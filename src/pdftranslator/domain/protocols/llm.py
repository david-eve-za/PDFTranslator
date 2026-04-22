"""LLM protocol definitions — segregated interfaces.

Resolves ISP-1: Consumers that only need text generation
should not be forced to depend on token counting or splitting.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from pdftranslator.core.config.llm import BCP47Language


@runtime_checkable
class TextGenerator(Protocol):
    """Minimal interface for text generation."""

    def call_model(self, prompt: str) -> str:
        """Generate text from a prompt."""
        ...


@runtime_checkable
class TokenCounter(Protocol):
    """Interface for token counting."""

    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        ...


@runtime_checkable
class TextSplitter(Protocol):
    """Interface for text splitting within token limits."""

    def split_into_limit(
        self, text: str, language: BCP47Language = BCP47Language.ENGLISH
    ) -> list[str]:
        """Split text into chunks within token limits."""
        ...


@runtime_checkable
class LLMClient(TextGenerator, TokenCounter, TextSplitter, Protocol):
    """Full LLM client — composed of segregated interfaces.

    For consumers that need all three capabilities.
    Prefer the specific interface when you don't need everything.
    """

    def get_current_model_name(self) -> str:
        """Get the name of the currently active model."""
        ...
