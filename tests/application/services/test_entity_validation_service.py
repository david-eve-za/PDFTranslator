"""Tests for EntityValidationService (extracted from GlossaryManager)."""
from unittest.mock import MagicMock
from pdftranslator.domain.protocols.llm import TextGenerator
from pdftranslator.application.services.entity_validation_service import EntityValidationService
from pdftranslator.domain.models.entity import EntityCandidate


def test_entity_validation_service_accepts_text_generator():
    mock_gen = MagicMock(spec=TextGenerator)
    mock_gen.call_model.return_value = '{"entities": [{"text": "Dragon", "valid": true, "type": "creature", "suggest": "Dragon"}]}'
    service = EntityValidationService(llm_client=mock_gen, max_output_tokens=4096)
    assert service is not None


def test_entity_validation_service_validates_entities():
    mock_gen = MagicMock(spec=TextGenerator)
    mock_gen.call_model.return_value = '{"entities": [{"text": "Dragon", "valid": true, "type": "creature", "suggest": "Dragon"}]}'
    service = EntityValidationService(llm_client=mock_gen, max_output_tokens=4096)
    entities = [EntityCandidate(text="Dragon", entity_type="other", contexts=["The dragon flew."])]
    result = service.validate(entities, "en")
    assert len(result) >= 1
    assert result[0].validated is True
