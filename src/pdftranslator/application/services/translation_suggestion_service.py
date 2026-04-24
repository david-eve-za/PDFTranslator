"""TranslationSuggestionService — suggests translations via LLM.

Extracted from GlossaryManager to fix DIP-1 and OCP-5 violations.
Accepts TextGenerator (domain protocol) instead of hard-coded NvidiaLLM.
Uses max_output_tokens parameter instead of nvidia-specific config.
"""
from __future__ import annotations

import json
import logging

from pdftranslator.domain.models.entity import EntityCandidate
from pdftranslator.domain.protocols.llm import TextGenerator

logger = logging.getLogger(__name__)


class TranslationSuggestionService:
    """Suggests translations for glossary entities using LLM."""

    def __init__(
        self,
        llm_client: TextGenerator,
        max_output_tokens: int = 4096,
    ):
        self._llm_client = llm_client
        self._max_output_tokens = max_output_tokens

    def suggest_translations(
        self,
        entities: list[EntityCandidate],
        source_lang: str,
        target_lang: str,
    ) -> dict[str, str]:
        """Suggest translations for entities via LLM.

        If entities already have translations from validation, use them.
        Otherwise, batch-translate via LLM.
        """
        if not entities:
            return {}

        if all(e.translation for e in entities):
            logger.info("Using translations from LLM validation")
            return {e.text: e.translation for e in entities if e.translation}

        batch_size = self._calculate_batch_size(len(entities))
        batches = self._split_into_batches(entities, batch_size)

        all_translations = {}
        for i, batch in enumerate(batches):
            logger.info(
                f"Translating batch {i + 1}/{len(batches)} ({len(batch)} entities)"
            )
            batch_translations = self._translate_batch(batch, source_lang, target_lang)
            all_translations.update(batch_translations)

        return all_translations

    def _calculate_batch_size(self, total_entities: int) -> int:
        available_tokens = self._max_output_tokens - 500
        avg_tokens_per_entity = 40
        batch_size = available_tokens // avg_tokens_per_entity
        return min(batch_size, 100)

    def _translate_batch(
        self,
        entities: list[EntityCandidate],
        source_lang: str,
        target_lang: str,
    ) -> dict[str, str]:
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

    def _split_into_batches(
        self,
        entities: list[EntityCandidate],
        batch_size: int,
    ) -> list[list[EntityCandidate]]:
        batches = []
        for i in range(0, len(entities), batch_size):
            batches.append(entities[i : i + batch_size])
        return batches
