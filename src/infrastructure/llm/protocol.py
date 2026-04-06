"""LLM Client Protocol definition."""

from typing import Protocol, runtime_checkable

from src.core.config.llm import BCP47Language


@runtime_checkable
class LLMClient(Protocol):
    """
    Protocol defining the LLM client interface.

    Any class implementing these methods can be used as an LLM client,
    enabling duck typing and easy mocking for tests.
    """

    def call_model(self, prompt: str) -> str:
        """
        Call the LLM model with a prompt.

        Args:
            prompt: The prompt to send to the model.

        Returns:
            The model's response as a string.

        Raises:
            LLMError: If the call fails.
        """
        ...

    def get_current_model_name(self) -> str:
        """
        Get the name of the currently active model.

        Returns:
            Model name string.
        """
        ...

    def count_tokens(self, text: str) -> int:
        """
        Count the number of tokens in a text.

        Args:
            text: The text to count tokens for.

        Returns:
            Number of tokens.
        """
        ...

    def split_into_limit(
        self, text: str, language: BCP47Language = BCP47Language.ENGLISH
    ) -> list[str]:
        """
        Split text into chunks that fit within token limits.

        Args:
            text: The text to split.
            language: Language for tokenization (default: English).

        Returns:
            List of text chunks.
        """
        ...
