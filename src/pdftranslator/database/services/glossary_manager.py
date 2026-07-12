"""
Glossary management service with RAG capabilities.

Main pipeline:
1. Extract entities from text (EntityExtractor)
2. Filter duplicates against existing glossary
3. Generate embeddings (VectorStoreService)
4. Suggest translations with LLM
5. Store in database
"""

from __future__ import annotations

import json
import logging
import sys
from typing import Dict, List, Optional

from pdftranslator.database.connection import DatabasePool
from pdftranslator.database.models import (
    BuildResult,
    EntityCandidate,
    GlossaryBuildProgress,
    GlossaryEntry,
)
from pdftranslator.database.repositories.glossary_build_progress_repository import (
    GlossaryBuildProgressRepository,
)
from pdftranslator.database.repositories.glossary_repository import GlossaryRepository
from pdftranslator.database.services.entity_extractor import EntityExtractor
from pdftranslator.database.services.vector_store import VectorStoreService
from pdftranslator.infrastructure.llm.nvidia import NvidiaLLM

# Rich for progress bar
try:
    from rich.console import Console
    from rich.progress import (
        Progress,
        SpinnerColumn,
        TextColumn,
        BarColumn,
        TaskProgressColumn,
        TimeRemainingColumn,
        MofNCompleteColumn,
    )
    from rich.live import Live
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

logger = logging.getLogger(__name__)


class GlossaryManager:
    def __init__(self, pool: Optional[DatabasePool] = None):
        self._pool = pool or DatabasePool.get_instance()
        self._extractor = EntityExtractor(pool)
        self._glossary_repo = GlossaryRepository(pool)
        self._progress_repo = GlossaryBuildProgressRepository(pool)
        self._vector_service = VectorStoreService()
        self._llm_client: Optional[NvidiaLLM] = None

    def _log_progress(self, stage: str, current: int, total: int, message: str = "") -> None:
        """Log progress for server environments where Rich may not display."""
        if total > 0:
            pct = (current / total) * 100
            bar_len = 30
            filled = int(bar_len * current / total)
            bar = "█" * filled + "░" * (bar_len - filled)
            logger.info(f"[{bar}] {stage}: {current}/{total} ({pct:.1f}%) {message}")
        else:
            logger.info(f"[{stage}] {message}")

    def _log_stage_start(self, stage: str, total: int) -> None:
        """Log the start of a pipeline stage."""
        logger.info(f"{'='*60}")
        logger.info(f"STAGE: {stage.upper()} ({total} items)")
        logger.info(f"{'='*60}")

    def _log_stage_complete(self, stage: str, total: int) -> None:
        """Log the completion of a pipeline stage."""
        logger.info(f"COMPLETED: {stage.upper()} - processed {total} items")
        logger.info(f"{'-'*60}")

    def _ensure_llm(self):
        if self._llm_client is None:
            from pdftranslator.core.config.settings import Settings

            settings = Settings.get()
            self._llm_client = NvidiaLLM(settings)

    def _validate_with_llm(
        self,
        entities: List[EntityCandidate],
        source_lang: str,
    ) -> List[EntityCandidate]:
        """
        Validate entities with LLM, filtering false positives and improving classification.

        Args:
            entities: Entities from NLTK extraction
            source_lang: Source language for context

        Returns:
            Validated entities with improved types and initial translations
        """
        if not entities:
            return []

        self._ensure_llm()
        logger.info(f"Validating {len(entities)} entities with LLM...")

        # Calculate batch size for validation
        batch_size = self._calculate_validation_batch_size()
        batches = self._split_into_batches(entities, batch_size)

        validated_entities = []
        for i, batch in enumerate(batches):
            logger.info(
                f"Validating batch {i + 1}/{len(batches)} ({len(batch)} entities)"
            )
            batch_validated = self._validate_batch(batch, source_lang)
            validated_entities.extend(batch_validated)

        logger.info(f"Validated {len(validated_entities)}/{len(entities)} entities")
        return validated_entities

    def _validate_with_llm_tracked(
        self,
        entities: List[EntityCandidate],
        source_lang: str,
        work_id: int,
        volume_id: int,
    ) -> tuple[List[EntityCandidate], int]:
        """
        Validate entities with LLM, tracking progress per batch.

        Returns (validated_entities, last_batch_number).
        """
        if not entities:
            return [], 0

        self._ensure_llm()
        batch_size = self._calculate_validation_batch_size()
        batches = self._split_into_batches(entities, batch_size)

        validated_entities = []
        for i, batch in enumerate(batches):
            logger.info(
                f"Validating batch {i + 1}/{len(batches)} ({len(batch)} entities)"
            )
            batch_validated = self._validate_batch(batch, source_lang)
            validated_entities.extend(batch_validated)

            # Update progress after each batch
            batch_entity_texts = [e.text for e in batch_validated]
            pending = self._progress_repo.get_pending_for_phase(
                work_id, volume_id, "extracted"
            )
            matching_ids = [
                p.id for p in pending if p.entity_text in batch_entity_texts
            ]
            if matching_ids:
                self._progress_repo.batch_update_phase(matching_ids, "validated", i + 1)

        return validated_entities, len(batches)

    def _validate_with_llm_tracked_with_progress(
        self,
        entities: List[EntityCandidate],
        source_lang: str,
        work_id: int,
        volume_id: int,
        progress: Progress,
        task_id: int,
    ) -> tuple[List[EntityCandidate], int]:
        """
        Validate entities with LLM, tracking progress per batch with Rich progress bar.

        Returns (validated_entities, last_batch_number).
        """
        if not entities:
            return [], 0

        self._ensure_llm()
        batch_size = self._calculate_validation_batch_size()
        batches = self._split_into_batches(entities, batch_size)

        validated_entities = []
        for i, batch in enumerate(batches):
            logger.info(
                f"Validating batch {i + 1}/{len(batches)} ({len(batch)} entities)"
            )
            batch_validated = self._validate_batch(batch, source_lang)
            validated_entities.extend(batch_validated)

            # Update progress after each batch
            if progress and task_id is not None:
                progress.update(
                    task_id,
                    description=f"[blue]Validating batch {i + 1}/{len(batches)}...",
                    advance=len(batch_validated),
                )

            # Update progress after each batch
            batch_entity_texts = [e.text for e in batch_validated]
            pending = self._progress_repo.get_pending_for_phase(
                work_id, volume_id, "extracted"
            )
            matching_ids = [
                p.id for p in pending if p.entity_text in batch_entity_texts
            ]
            if matching_ids:
                self._progress_repo.batch_update_phase(matching_ids, "validated", i + 1)

        return validated_entities, len(batches)

    def _suggest_translations_tracked_with_progress(
        self,
        entities: List[EntityCandidate],
        source_lang: str,
        target_lang: str,
        work_id: int,
        volume_id: int,
        progress: Progress,
        task_id: int,
    ) -> tuple[Dict[str, str], int]:
        """
        Suggest translations with progress tracking and Rich progress bar.

        Returns (translations, last_batch_number).
        """
        if not entities:
            return {}, 0

        self._ensure_llm()

        # If entities already have translations from validation, use them
        if all(e.translation for e in entities):
            logger.info("Using translations from LLM validation")
            if progress and task_id is not None:
                progress.update(
                    task_id, completed=len(entities), advance=len(entities)
                )
            return {e.text: e.translation for e in entities}, 0

        batch_size = self._calculate_translation_batch_size(len(entities))
        batches = self._split_into_batches(entities, batch_size)

        all_translations = {}
        for i, batch in enumerate(batches):
            logger.info(
                f"Translating batch {i + 1}/{len(batches)} ({len(batch)} entities)"
            )
            batch_translations = self._translate_batch(batch, source_lang, target_lang)
            all_translations.update(batch_translations)

            # Update Rich progress bar
            if progress and task_id is not None:
                progress.update(
                    task_id,
                    description=f"[cyan]Translating batch {i + 1}/{len(batches)}...",
                    advance=len(batch_translations),
                )

            # Update progress after each batch
            batch_entity_texts = list(batch_translations.keys())
            pending = self._progress_repo.get_pending_for_phase(
                work_id, volume_id, "validated"
            )
            matching_ids = [
                p.id for p in pending if p.entity_text in batch_entity_texts
            ]
            if matching_ids:
                self._progress_repo.batch_update_phase(
                    matching_ids, "translated", i + 1
                )

        return all_translations, len(batches)

    def _calculate_validation_batch_size(self) -> int:
        """
        Calculate optimal batch size for validation.

        Returns:
            Number of entities per batch
        """
        # Reserve tokens for prompt overhead (~500)
        available_tokens = self._llm_client._settings.llm.nvidia.max_output_tokens - 500

        # Estimate: ~60 tokens per entity with context in JSON response
        # {"text": "Entity", "valid": true, "type": "character", "suggest": "Entity"}
        avg_tokens_per_entity = 60

        batch_size = available_tokens // avg_tokens_per_entity
        return min(batch_size, 80)  # Cap at 80 entities per batch

    def _validate_batch(
        self,
        entities: List[EntityCandidate],
        source_lang: str,
    ) -> List[EntityCandidate]:
        """
        Validate a single batch of entities.

        Args:
            entities: Batch of entities to validate
            source_lang: Source language

        Returns:
            Validated entities from this batch
        """
        # Build prompt with entities and their best contexts
        entity_lines = []
        for e in entities:
            ctx = e.best_context()[:100]  # Truncate context for prompt
            entity_lines.append(f'- "{e.text}" (context: "{ctx}...")')

        prompt = f"""You are a fantasy literature expert. Validate and classify entities for translation.

Input entities with their best context:
{chr(10).join(entity_lines)}

Tasks:
1. Validate: Is this a proper noun requiring special translation treatment?
2. Classify: character/place/skill/item/faction/title/race
3. Suggest initial translation (keep original for names, translate for terms)

Rules:
- Proper names (characters, places): keep original OR phonetic adaptation
- Skills, items, titles: translate meaningfully
- Common words incorrectly detected: mark as invalid
- Pay attention to context for accurate classification

Respond ONLY as JSON (no explanation):
{{"entities": [{{"text": "EntityName", "valid": true, "type": "character", "suggest": "EntityName"}}]}}"""

        try:
            response = self._llm_client.call_model(prompt)
            response = response.replace("```json", "").replace("```", "").strip()

            # Parse JSON response
            data = json.loads(response)
            validated = []

            # Create mapping from response
            response_map = {e["text"]: e for e in data.get("entities", [])}

            for entity in entities:
                if entity.text in response_map:
                    resp = response_map[entity.text]
                    if resp.get("valid", False):
                        # Update entity with validated info
                        entity.validated = True
                        entity.entity_type = resp.get("type", entity.entity_type)
                        entity.translation = resp.get("suggest")
                        validated.append(entity)
                else:
                    # If not in response, keep original (conservative approach)
                    logger.debug(f"Entity '{entity.text}' not in LLM response, keeping")

            return validated

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse LLM validation response: {e}")
            # Return original entities on error
            return entities
        except Exception as e:
            logger.error(f"Error validating batch: {e}")
            return entities

    def build_from_text(
        self,
        text: str,
        work_id: int,
        volume_id: int,
        source_lang: str = "en",
        target_lang: str = "es",
        suggest_translations: bool = True,
        resume: bool = False,
        progress: Optional["Progress"] = None,
        task_ids: Optional[Dict[str, int]] = None,
    ) -> BuildResult:
        """
        Build glossary from text with full pipeline.

        Pipeline:
        1. Extract entities with NLTK
        2. Filter duplicates
        3. Save progress (NEW)
        4. Validate with LLM
        5. Generate embeddings
        6. Suggest translations with batching
        7. Save to database
        8. Cleanup progress (NEW)

        NEW: Supports resume from last checkpoint when resume=True.

        Args:
            text: Source text to analyze
            work_id: Work ID for glossary association
            volume_id: Volume ID for progress tracking
            source_lang: Source language code
            target_lang: Target language code
            suggest_translations: Whether to validate and suggest translations with LLM
            resume: Whether to resume from previous progress

        Returns:
            BuildResult with extraction statistics
        """
        # Track entities by type
        entities_by_type: Dict[str, int] = {}

        # Check for resume
        if resume:
            phase, batch_num = self._progress_repo.get_resume_point(work_id, volume_id)
            if phase != "extracted":
                logger.info(f"Resuming from phase '{phase}' (batch {batch_num})")
                return self._resume_from_phase(
                    work_id,
                    volume_id,
                    phase,
                    batch_num,
                    source_lang,
                    target_lang,
                    suggest_translations,
                )

        # Track progress records for cleanup
        progress_records: List[GlossaryBuildProgress] = []

        # Check if we should use Rich progress (only when stdout is a TTY)
        use_rich_progress = RICH_AVAILABLE and sys.stdout.isatty()
        use_logging_progress = RICH_AVAILABLE and not sys.stdout.isatty()

        # Determine if we should create our own Progress context or use the provided one
        create_own_progress = use_rich_progress and progress is None

        # Run full pipeline - either with provided progress or create our own
        # Extract first (before progress display)
        candidates = self._extractor.extract(text, source_lang)

        entities_by_type: Dict[str, int] = {}
        for c in candidates:
            entities_by_type[c.entity_type] = (
                entities_by_type.get(c.entity_type, 0) + 1
            )

        new_entities = self._glossary_repo.filter_new_entities(candidates, work_id)

        if not new_entities:
            self._progress_repo.cleanup_completed(volume_id)
            return BuildResult(
                extracted=len(candidates),
                new=0,
                skipped=len(candidates),
                entities_by_type=entities_by_type,
            )

        progress_records = self._progress_repo.save_extracted(
            work_id, volume_id, new_entities
        )
        logger.info(f"Saved {len(progress_records)} entities to progress table")

        # Helper function to run the pipeline with a progress instance
        def run_pipeline(progress_instance, tasks):
            # 4. Validate with LLM
            validated_entities = new_entities
            validation_batches = 0
            if suggest_translations:
                logger.info(f"Validating {len(new_entities)} entities with LLM...")
                validated_entities, validation_batches = (
                    self._validate_with_llm_tracked_with_progress(
                        new_entities,
                        source_lang,
                        work_id,
                        volume_id,
                        progress_instance,
                        tasks["validate"],
                    )
                )

            progress_instance.update(tasks["validate"], completed=len(validated_entities), visible=False)
            progress_instance.update(tasks["embed"], visible=True)

            # Update entities_by_type
            entities_by_type_local = {}
            for e in validated_entities:
                entities_by_type_local[e.entity_type] = (
                    entities_by_type_local.get(e.entity_type, 0) + 1
                )

            logger.info(f"Validated entities: {len(validated_entities)}/{len(new_entities)}")

            # 5. Generate embeddings
            entity_embeddings = self._vector_service.embed_entities_for_glossary(
                validated_entities
            )

            progress_instance.update(tasks["embed"], completed=1, visible=False)
            if suggest_translations and entity_embeddings:
                progress_instance.update(
                    tasks["translate"], total=len(validated_entities), visible=True
                )

            # 6. Suggest translations
            translations: Dict[str, str] = {}
            translation_batches = 0
            if suggest_translations and entity_embeddings:
                logger.info(f"Translating {len(validated_entities)} entities...")
                translations, translation_batches = self._suggest_translations_tracked_with_progress(
                    validated_entities,
                    source_lang,
                    target_lang,
                    work_id,
                    volume_id,
                    progress_instance,
                    tasks["translate"],
                )

            progress_instance.update(tasks["translate"], completed=len(validated_entities), visible=False)
            progress_instance.update(tasks["save"], visible=True)

            # 7. Save to database
            saved = self._save_entities(
                entity_embeddings,
                translations,
                work_id,
                source_lang,
                target_lang,
            )

            # 8. Cleanup
            if progress_records:
                progress_ids = [p.id for p in progress_records if p.id]
                if progress_ids:
                    self._progress_repo.batch_update_phase(progress_ids, "saved")

            self._progress_repo.cleanup_completed(volume_id)

            progress_instance.update(tasks["save"], completed=1, visible=False)

            return BuildResult(
                extracted=len(candidates),
                new=len(saved),
                skipped=len(candidates) - len(validated_entities),
                entities_by_type=entities_by_type_local,
            )

        if create_own_progress:
            # Create our own Console and Progress context
            console = Console(
                force_terminal=True,
                file=sys.stdout,
                width=120,
                legacy_windows=False,
            )
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                TimeRemainingColumn(),
                MofNCompleteColumn(),
                console=console,
                transient=False,
                expand=True,
            ) as progress_instance:
                tasks = {}
                tasks["validate"] = progress_instance.add_task(
                    "[blue]Validating entities...", total=len(new_entities)
                )
                tasks["embed"] = progress_instance.add_task(
                    "[magenta]Generating embeddings...", total=1, visible=False
                )
                tasks["translate"] = progress_instance.add_task(
                    "[cyan]Translating entities...", total=1, visible=False
                )
                tasks["save"] = progress_instance.add_task(
                    "[green]Saving to database...", total=1, visible=False
                )
                return run_pipeline(progress_instance, tasks)
        elif progress is not None and task_ids is not None:
            # Use the provided progress and task_ids (caller manages the Progress context)
            return run_pipeline(progress, task_ids)
        elif progress is not None and task_ids is None:
            # Progress provided but no task_ids - create subtasks in the provided progress
            tasks = {}
            tasks["validate"] = progress.add_task(
                "[blue]Validating entities...", total=len(new_entities)
            )
            tasks["embed"] = progress.add_task(
                "[magenta]Generating embeddings...", total=1, visible=False
            )
            tasks["translate"] = progress.add_task(
                "[cyan]Translating entities...", total=1, visible=False
            )
            tasks["save"] = progress.add_task(
                "[green]Saving to database...", total=1, visible=False
            )
            return run_pipeline(progress, tasks)
        elif use_logging_progress:
            # Logging-based progress fallback (existing logic)
            self._log_stage_start("extracting entities", 1)

            try:
                # 1. Extract entities with NLTK (already done above, but need to re-extract for logging flow)
                self._log_progress("extracting entities", 1, 1)
                self._log_stage_start("filtering duplicates", 1)
                self._log_progress("filtering duplicates", 1, 1)
                self._log_stage_start("validating entities", len(new_entities))

                # 3. Save progress (already done above)
                logger.info(f"Saved {len(progress_records)} entities to progress table")

                # 4. Validate with LLM
                validated_entities = new_entities
                validation_batches = 0
                if suggest_translations:
                    logger.info(f"Validating {len(new_entities)} entities with LLM...")
                    self._log_stage_start("validating with LLM", len(new_entities))
                    validated_entities, validation_batches = (
                        self._validate_with_llm_tracked(
                            new_entities, source_lang, work_id, volume_id
                        )
                    )
                    self._log_progress("validating with LLM", len(validated_entities), len(new_entities))
                    self._log_stage_start("generating embeddings", 1)

                # Update entities_by_type
                entities_by_type = {}
                for e in validated_entities:
                    entities_by_type[e.entity_type] = (
                        entities_by_type.get(e.entity_type, 0) + 1
                    )

                logger.info(f"Validated entities: {len(validated_entities)}/{len(new_entities)}")

                # 5. Generate embeddings
                entity_embeddings = self._vector_service.embed_entities_for_glossary(
                    validated_entities
                )

                if suggest_translations and entity_embeddings:
                    self._log_progress("generating embeddings", 1, 1)
                    self._log_stage_start("translating entities", len(validated_entities))

                # 6. Suggest translations
                translations: Dict[str, str] = {}
                translation_batches = 0
                if suggest_translations and entity_embeddings:
                    logger.info(f"Translating {len(validated_entities)} entities...")
                    self._log_stage_start("translating with LLM", len(validated_entities))
                    translations, translation_batches = self._suggest_translations_tracked(
                        validated_entities,
                        source_lang,
                        target_lang,
                        work_id,
                        volume_id,
                    )
                    self._log_progress("translating entities", len(validated_entities), len(validated_entities))
                    self._log_stage_start("saving to database", 1)

                # 7. Save to database
                saved = self._save_entities(
                    entity_embeddings,
                    translations,
                    work_id,
                    source_lang,
                    target_lang,
                )

                # 8. Cleanup
                if progress_records:
                    progress_ids = [p.id for p in progress_records if p.id]
                    if progress_ids:
                        self._progress_repo.batch_update_phase(progress_ids, "saved")

                self._progress_repo.cleanup_completed(volume_id)

                self._log_progress("saving to database", 1, 1)
                self._log_stage_complete("glossary build", len(saved))

                return BuildResult(
                    extracted=len(candidates),
                    new=len(saved),
                    skipped=len(candidates) - len(validated_entities),
                    entities_by_type=entities_by_type,
                )

            except Exception as e:
                logger.error(f"Error building glossary: {e}")
                self._log_stage_complete("glossary build (error)", 0)
                raise

        else:
            # No progress tracking - original behavior
            try:
                # Already extracted and filtered above

                # 4. Validate with LLM
                validated_entities = new_entities
                validation_batches = 0
                if suggest_translations:
                    logger.info(f"Validating {len(new_entities)} entities with LLM...")
                    validated_entities, validation_batches = (
                        self._validate_with_llm_tracked(
                            new_entities, source_lang, work_id, volume_id
                        )
                    )

                # Update entities_by_type
                entities_by_type = {}
                for e in validated_entities:
                    entities_by_type[e.entity_type] = (
                        entities_by_type.get(e.entity_type, 0) + 1
                    )

                logger.info(f"Validated entities: {len(validated_entities)}/{len(new_entities)}")

                # 5. Generate embeddings
                entity_embeddings = self._vector_service.embed_entities_for_glossary(
                    validated_entities
                )

                # 6. Suggest translations
                translations: Dict[str, str] = {}
                translation_batches = 0
                if suggest_translations and entity_embeddings:
                    logger.info(f"Translating {len(validated_entities)} entities...")
                    translations, translation_batches = self._suggest_translations_tracked(
                        validated_entities,
                        source_lang,
                        target_lang,
                        work_id,
                        volume_id,
                    )

                # 7. Save to database
                saved = self._save_entities(
                    entity_embeddings,
                    translations,
                    work_id,
                    source_lang,
                    target_lang,
                )

                # 8. Cleanup
                if progress_records:
                    progress_ids = [p.id for p in progress_records if p.id]
                    if progress_ids:
                        self._progress_repo.batch_update_phase(progress_ids, "saved")

                self._progress_repo.cleanup_completed(volume_id)

                return BuildResult(
                    extracted=len(candidates),
                    new=len(saved),
                    skipped=len(candidates) - len(validated_entities),
                    entities_by_type=entities_by_type,
                )

            except Exception as e:
                logger.error(f"Error building glossary: {e}")
                raise

    def _suggest_translations(
        self,
        entities: List[EntityCandidate],
        source_lang: str,
        target_lang: str,
    ) -> Dict[str, str]:
        """
        Suggest translations using LLM with auto-batching.

        Args:
            entities: List of entities to translate
            source_lang: Source language
            target_lang: Target language

        Returns:
            Dict mapping entity text to suggested translation
        """
        if not entities:
            return {}

        self._ensure_llm()

        # If entities already have translations from validation, use them
        if all(e.translation for e in entities):
            logger.info("Using translations from LLM validation")
            return {e.text: e.translation for e in entities}

        # Otherwise, calculate batches and translate
        batch_size = self._calculate_translation_batch_size(len(entities))
        batches = self._split_into_batches(entities, batch_size)

        all_translations = {}
        for i, batch in enumerate(batches):
            logger.info(
                f"Translating batch {i + 1}/{len(batches)} ({len(batch)} entities)"
            )
            batch_translations = self._translate_batch(batch, source_lang, target_lang)
            all_translations.update(batch_translations)

        return all_translations

    def _suggest_translations_tracked(
        self,
        entities: List[EntityCandidate],
        source_lang: str,
        target_lang: str,
        work_id: int,
        volume_id: int,
    ) -> tuple[Dict[str, str], int]:
        """
        Suggest translations with progress tracking.

        Returns (translations, last_batch_number).
        """
        if not entities:
            return {}, 0

        self._ensure_llm()

        # If entities already have translations from validation, use them
        if all(e.translation for e in entities):
            logger.info("Using translations from LLM validation")
            return {e.text: e.translation for e in entities}, 0

        batch_size = self._calculate_translation_batch_size(len(entities))
        batches = self._split_into_batches(entities, batch_size)

        all_translations = {}
        for i, batch in enumerate(batches):
            logger.info(
                f"Translating batch {i + 1}/{len(batches)} ({len(batch)} entities)"
            )
            batch_translations = self._translate_batch(batch, source_lang, target_lang)
            all_translations.update(batch_translations)

            # Update progress after each batch
            batch_entity_texts = list(batch_translations.keys())
            pending = self._progress_repo.get_pending_for_phase(
                work_id, volume_id, "validated"
            )
            matching_ids = [
                p.id for p in pending if p.entity_text in batch_entity_texts
            ]
            if matching_ids:
                self._progress_repo.batch_update_phase(
                    matching_ids, "translated", i + 1
                )

        return all_translations, len(batches)

    def _calculate_translation_batch_size(self, total_entities: int) -> int:
        """
        Calculate optimal batch size for translation.

        Args:
            total_entities: Total number of entities

        Returns:
            Number of entities per batch
        """
        # Reserve tokens for prompt overhead
        available_tokens = self._llm_client._settings.llm.nvidia.max_output_tokens - 500

        # Estimate: ~40 tokens per entity in JSON response
        # {"term": "translation"} ≈ 25 chars ≈ 6-7 tokens
        # Plus entity name variations and formatting
        avg_tokens_per_entity = 40

        batch_size = available_tokens // avg_tokens_per_entity
        return min(batch_size, 100)  # Cap at 100 entities

    def _split_into_batches(
        self,
        entities: List[EntityCandidate],
        batch_size: int,
    ) -> List[List[EntityCandidate]]:
        """
        Split entities into batches.

        Args:
            entities: List of entities
            batch_size: Maximum entities per batch

        Returns:
            List of batches
        """
        batches = []
        for i in range(0, len(entities), batch_size):
            batches.append(entities[i : i + batch_size])
        return batches

    def _translate_batch(
        self,
        entities: List[EntityCandidate],
        source_lang: str,
        target_lang: str,
    ) -> Dict[str, str]:
        """
        Translate a single batch of entities.

        Args:
            entities: Batch of entities to translate
            source_lang: Source language
            target_lang: Target language

        Returns:
            Dict mapping entity text to translation
        """
        terms = [e.text for e in entities]

        prompt = f"""You are a translation assistant for fantasy literature.
Translate the following terms from {source_lang} to {target_lang}.

Rules:
- For proper names of characters and places: keep original OR adapt phonetically if appropriate
- For skills, items, titles: translate meaningfully
- For races/species that are proper nouns in this context: keep original
- Respond ONLY with a JSON object, no explanation

Terms: {json.dumps(terms)}

Response format: {{"original_term": "translation"}}"""

        try:
            response = self._llm_client.call_model(prompt)
            response = response.replace("```json", "").replace("```", "").strip()
            return json.loads(response)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse LLM translation response: {e}")
            return {}
        except Exception as e:
            logger.error(f"Error translating batch: {e}")
            return {}

    def _save_entities(
        self,
        entity_embeddings: List[tuple],
        translations: Dict[str, str],
        work_id: int,
        source_lang: str,
        target_lang: str,
    ) -> List[GlossaryEntry]:
        """
        Save entities to database.

        Args:
            entity_embeddings: List of (EntityCandidate, embedding) tuples
            translations: Dict of suggested translations
            work_id: Work ID
            source_lang: Source language
            target_lang: Target language

        Returns:
            List of saved GlossaryEntry objects
        """
        entries_to_save = []
        for entity, embedding in entity_embeddings:
            translation = translations.get(entity.text)
            setattr(entity, "translation", translation)
            entries_to_save.append((entity, embedding))

        return self._glossary_repo.batch_create_with_embeddings(
            entries_to_save,
            work_id,
            source_lang,
            target_lang,
        )

    def get_glossary_for_work(self, work_id: int) -> List[GlossaryEntry]:
        """Get all glossary entries for a work."""
        return self._glossary_repo.get_by_work(work_id)

    def _resume_from_phase(
        self,
        work_id: int,
        volume_id: int,
        phase: str,
        batch_num: Optional[int],
        source_lang: str,
        target_lang: str,
        suggest_translations: bool,
    ) -> BuildResult:
        """Resume pipeline from a specific phase."""
        entities_by_type: Dict[str, int] = {}

        if phase == "validated":
            # Resume from validation
            pending = self._progress_repo.get_pending_for_phase(
                work_id, volume_id, "extracted"
            )
            entities = [
                EntityCandidate(
                    text=p.entity_text,
                    entity_type=p.entity_type or "other",
                    frequency=p.frequency,
                    contexts=p.contexts,
                )
                for p in pending
            ]

            if not entities:
                return BuildResult(extracted=0, new=0, skipped=0, entities_by_type={})

            validated_entities, _ = self._validate_with_llm_tracked(
                entities, source_lang, work_id, volume_id
            )

            # Continue with embeddings and translation
            entity_embeddings = self._vector_service.embed_entities_for_glossary(
                validated_entities
            )

            translations = {}
            if suggest_translations and entity_embeddings:
                translations, _ = self._suggest_translations_tracked(
                    validated_entities,
                    source_lang,
                    target_lang,
                    work_id,
                    volume_id,
                )

            saved = self._save_entities(
                entity_embeddings,
                translations,
                work_id,
                source_lang,
                target_lang,
            )

            # Update progress and cleanup
            progress_ids = [p.id for p in pending if p.id]
            if progress_ids:
                self._progress_repo.batch_update_phase(progress_ids, "saved")
                self._progress_repo.cleanup_completed(volume_id)

            for e in validated_entities:
                entities_by_type[e.entity_type] = (
                    entities_by_type.get(e.entity_type, 0) + 1
                )

            return BuildResult(
                extracted=len(entities),
                new=len(saved),
                skipped=len(entities) - len(validated_entities),
                entities_by_type=entities_by_type,
            )

        elif phase == "translated":
            # Resume from translation
            pending = self._progress_repo.get_pending_for_phase(
                work_id, volume_id, "validated"
            )
            entities = [
                EntityCandidate(
                    text=p.entity_text,
                    entity_type=p.entity_type or "other",
                    frequency=p.frequency,
                    contexts=p.contexts,
                    translation=p.translation,
                )
                for p in pending
            ]

            if not entities:
                return BuildResult(extracted=0, new=0, skipped=0, entities_by_type={})

            # Need to regenerate embeddings
            entity_embeddings = self._vector_service.embed_entities_for_glossary(
                entities
            )

            translations = {}
            if suggest_translations and entity_embeddings:
                translations, _ = self._suggest_translations_tracked(
                    entities,
                    source_lang,
                    target_lang,
                    work_id,
                    volume_id,
                )

            saved = self._save_entities(
                entity_embeddings,
                translations,
                work_id,
                source_lang,
                target_lang,
            )

            progress_ids = [p.id for p in pending if p.id]
            if progress_ids:
                self._progress_repo.batch_update_phase(progress_ids, "saved")
                self._progress_repo.cleanup_completed(volume_id)

            for e in entities:
                entities_by_type[e.entity_type] = (
                    entities_by_type.get(e.entity_type, 0) + 1
                )

            return BuildResult(
                extracted=len(entities),
                new=len(saved),
                skipped=0,
                entities_by_type=entities_by_type,
            )

        # Default: start fresh
        return BuildResult(extracted=0, new=0, skipped=0, entities_by_type={})

    # ============================================================
    # Progress Logging Helpers (for server environments)
    # ============================================================

    def _log_stage_start(self, stage: str, total: int) -> None:
        """Log the start of a pipeline stage."""
        logger.info(f"{'='*60}")
        logger.info(f"STAGE: {stage.upper()} ({total} items)")
        logger.info(f"{'='*60}")

    def _log_stage_complete(self, stage: str, total: int) -> None:
        """Log the completion of a pipeline stage."""
        logger.info(f"COMPLETED: {stage.upper()} - processed {total} items")
        logger.info(f"{'-'*60}")

    def _log_progress(self, stage: str, current: int, total: int, message: str = "") -> None:
        """Log progress for server environments where Rich may not display."""
        if total > 0:
            pct = (current / total) * 100
            bar_len = 30
            filled = int(bar_len * current / total)
            bar = "█" * filled + "░" * (bar_len - filled)
            logger.info(f"[{bar}] {stage}: {current}/{total} ({pct:.1f}%) {message}")
        else:
            logger.info(f"[{stage}] {message}")
