"""Tests for application-layer TranslationService (DIP fix)."""
from unittest.mock import MagicMock

from pdftranslator.application.services.translation_service import TranslationService
from pdftranslator.domain.protocols.llm import LLMClient, TextGenerator


def test_translation_service_accepts_llm_client():
    mock_client = MagicMock(spec=LLMClient)
    mock_client.call_model.return_value = "translated text"
    mock_client.split_into_limit.return_value = ["chunk1"]
    mock_client.count_tokens.return_value = 10
    mock_client.get_current_model_name.return_value = "mock"
    service = TranslationService(llm_client=mock_client)
    assert service.llm_client is mock_client


def test_translation_service_works_with_text_generator_only():
    mock_gen = MagicMock(spec=TextGenerator)
    mock_gen.call_model.return_value = "translated text"
    service = TranslationService(llm_client=mock_gen)
    assert service.llm_client is mock_gen
