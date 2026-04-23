"""EntityValidationService — validates entities via LLM.

Extracted from GlossaryManager to fix DIP-1 and SRP violations.
Accepts TextGenerator (domain protocol) instead of hard-coded NvidiaLLM.
"""
from __future__ import annotations

import json
import logging
from typing import Optional

from pdftranslator.domain.protocols.llm import TextGenerator
from pdftranslator.domain.models.entity import EntityCandidate

logger = logging.getLogger(__name__)


class EntityValidationService:
    """Validates and classifies extracted entities using LLM."""

    def __init__(
        self,
        llm_client: TextGenerator,
        max_output_tokens: int = 4096,
    ):
        self._llm_client = llm_client
        self._max_output_tokens = max_output_tokens

    def validate(
        self,
        entities: list[EntityCandidate],
        source_lang: str,
    ) -> list[EntityCandidate]:
        """Validate entities with LLM, filtering false positives."""
        if not entities:
            return []

        logger.info(f"Validating {len(entities)} entities with LLM...")
        batch_size = self._calculate_batch_size()
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

    def _calculate_batch_size(self) -> int:
        available_tokens = self._max_output_tokens - 500
        avg_tokens_per_entity = 60
        batch_size = available_tokens // avg_tokens_per_entity
        return min(batch_size, 80)

    def _validate_batch(
        self,
        entities: list[EntityCandidate],
        source_lang: str,
    ) -> list[EntityCandidate]:
        entity_lines = []
        for e in entities:
            ctx = e.best_context()[:100]
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

            data = json.loads(response)
            validated = []
            response_map = {e["text"]: e for e in data.get("entities", [])}

            for entity in entities:
                if entity.text in response_map:
                    resp = response_map[entity.text]
                    if resp.get("valid", False):
                        entity.validated = True
                        entity.entity_type = resp.get("type", entity.entity_type)
                        entity.translation = resp.get("suggest")
                        validated.append(entity)
                else:
                    logger.debug(f"Entity '{entity.text}' not in LLM response, keeping")

            return validated

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse LLM validation response: {e}")
            return entities
        except Exception as e:
            logger.error(f"Error validating batch: {e}")
            return entities

    def _split_into_batches(
        self,
        entities: list[EntityCandidate],
        batch_size: int,
    ) -> list[list[EntityCandidate]]:
        batches = []
        for i in range(0, len(entities), batch_size):
            batches.append(entities[i : i + batch_size])
        return batches
