"""Text substitution service for applying regex rules."""

import logging
import re
import warnings

from pdftranslator.database.connection import DatabasePool
from pdftranslator.database.repositories.substitution_rule_repository import (
    SubstitutionRuleRepository,
)
from pdftranslator.database.repositories.volume_repository import VolumeRepository
from pdftranslator.domain.models.substitution import SubstitutionRule

logger = logging.getLogger(__name__)


class TextSubstitutionService:
    """Apply text substitution rules to content."""

    def __init__(
        self,
        rule_repo: SubstitutionRuleRepository | None = None,
        volume_repo: VolumeRepository | None = None,
    ):
        if rule_repo is None:
            warnings.warn(
                "Providing rule_repo=None is deprecated. Inject repositories explicitly.",
                DeprecationWarning,
                stacklevel=2,
            )
            rule_repo = SubstitutionRuleRepository(DatabasePool.get_instance())
        if volume_repo is None:
            warnings.warn(
                "Providing volume_repo=None is deprecated. Inject repositories explicitly.",
                DeprecationWarning,
                stacklevel=2,
            )
            volume_repo = VolumeRepository(DatabasePool.get_instance())
        self._rule_repo = rule_repo
        self._volume_repo = volume_repo

    def apply_rules(self, text: str, rules: list[SubstitutionRule]) -> str:
        result = text
        for rule in rules:
            if rule.is_active:
                try:
                    result = re.sub(rule.pattern, rule.replacement, result)
                    logger.debug(
                        f"Applied rule '{rule.name}': {rule.pattern} -> {rule.replacement}"
                    )
                except re.error as e:
                    logger.error(f"Invalid regex pattern in rule '{rule.name}': {e}")
        return result

    def apply_to_text(self, text: str, rule_ids: list[int] = None) -> str:
        if rule_ids:
            rules = [self._rule_repo.get_by_id(rid) for rid in rule_ids]
            rules = [r for r in rules if r is not None]
        else:
            rules = self._rule_repo.get_all(active_only=True)
        return self.apply_rules(text, rules)

    def apply_to_volume(self, volume_id: int, rule_ids: list[int] = None) -> dict:
        volume = self._volume_repo.get_by_id(volume_id)
        if not volume:
            return {"success": False, "error": "Volume not found"}

        if not volume.full_text:
            return {"success": False, "error": "Volume has no text content"}

        original_text = volume.full_text
        processed_text = self.apply_to_text(original_text, rule_ids)

        if processed_text == original_text:
            return {"success": True, "changes": 0, "message": "No changes made"}

        self._volume_repo.update_full_text(volume_id, processed_text)

        return {
            "success": True,
            "changes": 1,
            "original_length": len(original_text),
            "processed_length": len(processed_text),
        }

    def get_auto_apply_rules(self) -> list[SubstitutionRule]:
        return self._rule_repo.get_auto_apply_rules()
