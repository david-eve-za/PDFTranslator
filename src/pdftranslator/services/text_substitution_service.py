"""Text substitution service for applying regex rules."""

import re
import logging
from typing import List

from pdftranslator.database.models import SubstitutionRule
from pdftranslator.database.repositories.substitution_rule_repository import (
    SubstitutionRuleRepository,
)
from pdftranslator.database.repositories.volume_repository import VolumeRepository
from pdftranslator.database.connection import DatabasePool

logger = logging.getLogger(__name__)


class TextSubstitutionService:
    """Apply text substitution rules to content."""

    def __init__(self):
        self._rule_repo = SubstitutionRuleRepository(DatabasePool.get_instance())
        self._volume_repo = VolumeRepository(DatabasePool.get_instance())

    def apply_rules(self, text: str, rules: List[SubstitutionRule]) -> str:
        """
        Apply all active rules to text.

        Args:
            text: Text to process
            rules: List of substitution rules

        Returns:
            Text with substitutions applied
        """
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

    def apply_to_text(self, text: str, rule_ids: List[int] = None) -> str:
        """
        Apply specific rules or all active rules to text.

        Args:
            text: Text to process
            rule_ids: Optional list of specific rule IDs to apply

        Returns:
            Text with substitutions applied
        """
        if rule_ids:
            rules = [self._rule_repo.get_by_id(rid) for rid in rule_ids]
            rules = [r for r in rules if r is not None]
        else:
            rules = self._rule_repo.get_all(active_only=True)
        return self.apply_rules(text, rules)

    def apply_to_volume(self, volume_id: int, rule_ids: List[int] = None) -> dict:
        """
        Apply rules to a volume's full_text.

        Args:
            volume_id: Volume ID
            rule_ids: Optional list of specific rule IDs

        Returns:
            Dict with success status and stats
        """
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

    def get_auto_apply_rules(self) -> List[SubstitutionRule]:
        """Get rules that should be applied automatically on extraction."""
        return self._rule_repo.get_auto_apply_rules()
