"""Tests for LLM protocol segregation (ISP-1)."""
from pdftranslator.domain.protocols.llm import (
    TextGenerator,
    TokenCounter,
    TextSplitter,
    LLMClient,
)


def test_text_generator_protocol():
    class MockGenerator:
        def call_model(self, prompt: str) -> str:
            return "response"
    gen = MockGenerator()
    assert isinstance(gen, TextGenerator)


def test_llm_client_composed_protocols():
    class MockLLM:
        def call_model(self, prompt: str) -> str:
            return "response"

        def count_tokens(self, text: str) -> int:
            return len(text.split())

        def split_into_limit(self, text: str, language=None) -> list[str]:
            return [text]

        def get_current_model_name(self) -> str:
            return "mock"
    client = MockLLM()
    assert isinstance(client, LLMClient)
    assert isinstance(client, TextGenerator)
    assert isinstance(client, TokenCounter)
    assert isinstance(client, TextSplitter)
