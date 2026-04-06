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

from src.database.connection import DatabasePool
from src.database.models import EntityCandidate, BuildResult, GlossaryEntry
from src.database.repositories.glossary_repository import GlossaryRepository
from src.database.services.entity_extractor import EntityExtractor
from src.database.services.vector_store import VectorStoreService
from src.infrastructure.llm.nvidia import NvidiaLLM

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
            self._llm_client = NvidiaLLM()

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

        Args:
            text: Source text to analyze
            work_id: Work ID for glossary association
            source_lang: Source language code
            target_lang: Target language code
            suggest_translations: Whether to suggest translations with LLM

        Returns:
            BuildResult with extraction statistics
        """
        candidates = self._extractor.extract(text, source_lang)

        entities_by_type: Dict[str, int] = {}
        for c in candidates:
            entities_by_type[c.entity_type] = entities_by_type.get(c.entity_type, 0) + 1

        new_entities = self._glossary_repo.filter_new_entities(candidates, work_id)

        if not new_entities:
            return BuildResult(
                extracted=len(candidates),
                new=0,
                skipped=len(candidates),
                entities_by_type=entities_by_type,
            )

        entity_embeddings = self._vector_service.embed_entities_for_glossary(
            new_entities
        )

        translations: Dict[str, str] = {}
        if suggest_translations and entity_embeddings:
            translations = self._suggest_translations(
                new_entities, source_lang, target_lang
            )

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
            skipped=len(candidates) - len(new_entities),
            entities_by_type=entities_by_type,
        )

    def _suggest_translations(
        self,
        entities: List[EntityCandidate],
        source_lang: str,
        target_lang: str,
    ) -> Dict[str, str]:
        """
        Suggest translations using LLM.

        Args:
            entities: List of entities to translate
            source_lang: Source language
            target_lang: Target language

        Returns:
            Dict mapping entity text to suggested translation
        """
        self._ensure_llm()

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
            response = self._llm_client.call_model(prompt).replace("```json","").replace("```","")
            if response:
                return json.loads(response)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse LLM translation response: {e}")
        except Exception as e:
            logger.error(f"Error getting translations from LLM: {e}")

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
