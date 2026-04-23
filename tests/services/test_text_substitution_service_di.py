"""Tests for TextSubstitutionService DI fix."""
from unittest.mock import MagicMock
from pdftranslator.services.text_substitution_service import TextSubstitutionService
from pdftranslator.database.repositories.substitution_rule_repository import SubstitutionRuleRepository
from pdftranslator.database.repositories.volume_repository import VolumeRepository


def test_text_substitution_service_accepts_injected_repos():
    mock_rule_repo = MagicMock(spec=SubstitutionRuleRepository)
    mock_volume_repo = MagicMock(spec=VolumeRepository)
    service = TextSubstitutionService(rule_repo=mock_rule_repo, volume_repo=mock_volume_repo)
    assert service._rule_repo is mock_rule_repo
    assert service._volume_repo is mock_volume_repo
