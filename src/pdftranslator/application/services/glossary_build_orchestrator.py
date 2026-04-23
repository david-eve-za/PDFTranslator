"""GlossaryBuildOrchestrator — coordinates the glossary build pipeline.

Replaces GlossaryManager.build_from_text() with a DIP-compliant version
that accepts all dependencies via constructor injection.

Pipeline:
1. Extract entities from text
2. Filter duplicates against existing glossary
3. Save progress
4. Validate with LLM (via EntityValidationService)
5. Generate embeddings (via EmbeddingProvider)
6. Suggest translations (via TranslationSuggestionService)
7. Save to database
8. Cleanup progress
"""
from __future__ import annotations

import logging

from pdftranslator.domain.protocols.llm import TextGenerator
from pdftranslator.domain.protocols.embedding import EmbeddingProvider
from pdftranslator.domain.protocols.repositories import GlossaryProgressTracker
from pdftranslator.domain.models.entity import BuildResult, EntityCandidate
from pdftranslator.application.services.entity_validation_service import EntityValidationService
from pdftranslator.application.services.translation_suggestion_service import TranslationSuggestionService

logger = logging.getLogger(__name__)


class GlossaryBuildOrchestrator:
    """Orchestrates the full glossary build pipeline."""

    def __init__(
        self,
        llm_client: TextGenerator,
        embedder: EmbeddingProvider,
        progress_tracker: GlossaryProgressTracker,
        glossary_repo,
        entity_extractor,
        max_output_tokens: int = 4096,
    ):
        self._validation_service = EntityValidationService(
            llm_client=llm_client,
            max_output_tokens=max_output_tokens,
        )
        self._translation_service = TranslationSuggestionService(
            llm_client=llm_client,
            max_output_tokens=max_output_tokens,
        )
        self._embedder = embedder
        self._progress_tracker = progress_tracker
        self._glossary_repo = glossary_repo
        self._entity_extractor = entity_extractor

    def build_from_text(
        self,
        text: str,
        work_id: int,
        volume_id: int,
        source_lang: str = "en",
        target_lang: str = "es",
        suggest_translations: bool = True,
        resume: bool = False,
    ) -> BuildResult:
        """Build glossary from text with full pipeline."""
        entities_by_type: dict[str, int] = {}

        if resume:
            phase, batch_num = self._progress_tracker.get_resume_point(work_id, volume_id)
            if phase == "saved":
                logger.info("Glossary build already complete")
                return BuildResult(extracted=0, new=0, skipped=0)
            return self._resume_from_phase(
                work_id, volume_id, phase, batch_num,
                source_lang, target_lang, suggest_translations,
            )

        entities = self._entity_extractor.extract(text)
        logger.info(f"Extracted {len(entities)} entities")

        if not entities:
            return BuildResult(extracted=0, new=0, skipped=0)

        for e in entities:
            entities_by_type[e.entity_type] = entities_by_type.get(e.entity_type, 0) + 1

        existing = self._glossary_repo.get_by_work(work_id)
        existing_terms = {e.term for e in existing}
        new_entities = [e for e in entities if e.text not in existing_terms]
        skipped = len(entities) - len(new_entities)
        logger.info(f"Filtered: {skipped} existing, {len(new_entities)} new entities")

        self._progress_tracker.save_extracted(work_id, volume_id, new_entities)

        if suggest_translations:
            new_entities = self._validation_service.validate(new_entities, source_lang)
            if new_entities:
                translations = self._translation_service.suggest_translations(
                    new_entities, source_lang, target_lang
                )
            else:
                translations = {}
        else:
            translations = {}

        if not new_entities:
            return BuildResult(
                extracted=len(entities),
                new=0,
                skipped=skipped,
                entities_by_type=entities_by_type,
            )

        entity_embeddings = self._generate_embeddings(new_entities)
        self._save_entities(entity_embeddings, translations, work_id, source_lang, target_lang)
        self._progress_tracker.cleanup_completed(volume_id)

        return BuildResult(
            extracted=len(entities),
            new=len(new_entities),
            skipped=skipped,
            entities_by_type=entities_by_type,
        )

    def _generate_embeddings(
        self,
        entities: list[EntityCandidate],
    ) -> list[tuple]:
        if not entities:
            return []
        texts = [e.to_embed_text() for e in entities]
        embeddings = self._embedder.embed_documents(texts)
        return list(zip(entities, embeddings))

    def _save_entities(
        self,
        entity_embeddings: list[tuple],
        translations: dict[str, str],
        work_id: int,
        source_lang: str,
        target_lang: str,
    ) -> list:
        entries_to_save = []
        for entity, embedding in entity_embeddings:
            translation = translations.get(entity.text)
            if translation:
                entity.translation = translation
            entries_to_save.append((entity, embedding))

        return self._glossary_repo.batch_create_with_embeddings(
            entries_to_save, work_id, source_lang, target_lang,
        )

    def _resume_from_phase(
        self,
        work_id: int,
        volume_id: int,
        phase: str,
        batch_num: int | None,
        source_lang: str,
        target_lang: str,
        suggest_translations: bool,
    ) -> BuildResult:
        logger.info(f"Resuming from phase: {phase}, batch: {batch_num}")
        entities_by_type: dict[str, int] = {}

        if phase == "validated":
            pending = self._progress_tracker.get_pending_for_phase(
                work_id, volume_id, "extracted"
            )
            if pending:
                self._progress_tracker.batch_update_phase(
                    [p.id for p in pending], "validated"
                )

        if phase in ("validated", "translated"):
            pending = self._progress_tracker.get_pending_for_phase(
                work_id, volume_id, "validated"
            )
            if pending:
                if suggest_translations:
                    entities = [EntityCandidate(text=p.entity_text) for p in pending]
                    translations = self._translation_service.suggest_translations(
                        entities, source_lang, target_lang
                    )
                    self._progress_tracker.batch_update_phase(
                        [p.id for p in pending], "translated"
                    )
                else:
                    translations = {}

                entity_embeddings = self._generate_embeddings(entities)
                self._save_entities(
                    entity_embeddings, translations, work_id, source_lang, target_lang
                )
                self._progress_tracker.cleanup_completed(volume_id)

                return BuildResult(
                    extracted=len(pending),
                    new=len(pending),
                    skipped=0,
                    entities_by_type=entities_by_type,
                )

        self._progress_tracker.cleanup_completed(volume_id)
        return BuildResult(extracted=0, new=0, skipped=0, entities_by_type=entities_by_type)
