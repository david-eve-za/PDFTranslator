"""Tests for TranslationSuggestionService (extracted from GlossaryManager)."""
from unittest.mock import MagicMock

from pdftranslator.application.services.translation_suggestion_service import (
    TranslationSuggestionService,
)
from pdftranslator.domain.models.entity import EntityCandidate
from pdftranslator.domain.protocols.llm import TextGenerator


def test_translation_suggestion_service_accepts_text_generator():
    mock_gen = MagicMock(spec=TextGenerator)
    service = TranslationSuggestionService(llm_client=mock_gen, max_output_tokens=4096)
    assert service is not None


def test_translation_suggestion_service_suggests():
    mock_gen = MagicMock(spec=TextGenerator)
    mock_gen.call_model.return_value = '{"Dragon": "Dragon", "Sword": "Espada"}'
    service = TranslationSuggestionService(llm_client=mock_gen, max_output_tokens=4096)
    entities = [EntityCandidate(text="Dragon"), EntityCandidate(text="Sword")]
    result = service.suggest_translations(entities, "en", "es")
    assert "Dragon" in result
    assert "Sword" in result
