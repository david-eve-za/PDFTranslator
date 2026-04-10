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
from typing import Dict, List, Optional

from pdftranslator.database.connection import DatabasePool
from pdftranslator.database.models import EntityCandidate, BuildResult, GlossaryEntry
from pdftranslator.database.repositories.glossary_repository import GlossaryRepository
from pdftranslator.database.services.entity_extractor import EntityExtractor
from pdftranslator.database.services.vector_store import VectorStoreService
from pdftranslator.infrastructure.llm.nvidia import NvidiaLLM

logger = logging.getLogger(__name__)


class GlossaryManager:
    def __init__(self, pool: Optional[DatabasePool] = None):
        self._pool = pool or DatabasePool.get_instance()
        self._extractor = EntityExtractor(pool)
        self._glossary_repo = GlossaryRepository(pool)
        self._vector_service = VectorStoreService()
        self._llm_client: Optional[NvidiaLLM] = None

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
        source_lang: str = "en",
        target_lang: str = "es",
        suggest_translations: bool = True,
    ) -> BuildResult:
        """
        Build glossary from text with full pipeline.

        Pipeline:
        1. Extract entities with NLTK
        2. Filter duplicates
        3. Validate with LLM (NEW)
        4. Generate embeddings
        5. Suggest translations with batching (IMPROVED)
        6. Save to database

        Args:
            text: Source text to analyze
            work_id: Work ID for glossary association
            source_lang: Source language code
            target_lang: Target language code
            suggest_translations: Whether to validate and suggest translations with LLM

        Returns:
            BuildResult with extraction statistics
        """
        # 1. Extract entities with NLTK
        candidates = self._extractor.extract(text, source_lang)

        # Track entities by type
        entities_by_type: Dict[str, int] = {}
        for c in candidates:
            entities_by_type[c.entity_type] = entities_by_type.get(c.entity_type, 0) + 1

        # 2. Filter duplicates against existing glossary
        new_entities = self._glossary_repo.filter_new_entities(candidates, work_id)

        if not new_entities:
            return BuildResult(
                extracted=len(candidates),
                new=0,
                skipped=len(candidates),
                entities_by_type=entities_by_type,
            )

        # 3. Validate with LLM (NEW)
        validated_entities = new_entities
        if suggest_translations:
            logger.info(f"Validating {len(new_entities)} entities with LLM...")
            validated_entities = self._validate_with_llm(new_entities, source_lang)

            # Update entities_by_type with validated types
            entities_by_type = {}
            for e in validated_entities:
                entities_by_type[e.entity_type] = (
                    entities_by_type.get(e.entity_type, 0) + 1
                )

            logger.info(
                f"Validated entities: {len(validated_entities)}/{len(new_entities)}"
            )

        # 4. Generate embeddings
        entity_embeddings = self._vector_service.embed_entities_for_glossary(
            validated_entities
        )

        # 5. Suggest translations with batching (IMPROVED)
        translations: Dict[str, str] = {}
        if suggest_translations and entity_embeddings:
            translations = self._suggest_translations(
                validated_entities, source_lang, target_lang
            )

        # 6. Save to database
        saved = self._save_entities(
            entity_embeddings,
            translations,
            work_id,
            source_lang,
            target_lang,
        )

        return BuildResult(
            extracted=len(candidates),
            new=len(saved),
            skipped=len(candidates) - len(validated_entities),
            entities_by_type=entities_by_type,
        )

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
