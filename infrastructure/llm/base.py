"""Base LLM implementation with common functionality."""

from abc import ABC, abstractmethod
from typing import List

from config.settings import Settings
from config.llm import BCP47Language


class BaseLLM(ABC):
    """
    Abstract base class for LLM implementations.

    Provides common initialization and enforces the LLM interface.
    Subclasses must implement all abstract methods.
    """

    def __init__(self, settings: Settings):
        """
        Initialize the LLM with settings.

        Args:
            settings: Application settings containing LLM configuration.
        """
        self._settings = settings

    @abstractmethod
    def call_model(self, prompt: str) -> str:
        """Call the LLM model with a prompt."""
        pass

    @abstractmethod
    def get_current_model_name(self) -> str:
        """Get the name of the currently active model."""
        pass

    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """Count the number of tokens in a text."""
        pass

    @abstractmethod
    def split_into_limit(
        self, text: str, language: BCP47Language = BCP47Language.ENGLISH
    ) -> List[str]:
        """Split text into chunks that fit within token limits."""
        pass
