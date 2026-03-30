"""Factory for creating LLM clients."""

import logging
from typing import Type

from config.settings import Settings
from config.llm import LLMProvider
from infrastructure.llm.protocol import LLMClient
from infrastructure.llm.base import BaseLLM

logger = logging.getLogger(__name__)


class LLMFactory:
    """
    Factory for creating LLM clients based on configuration.

    Implements the Factory Pattern to decouple client creation
    from the calling code. Supports singleton instances per provider.

    Usage:
        factory = LLMFactory(settings)
        client = factory.create()  # Uses default provider from settings
        client = factory.create(LLMProvider.GEMINI)  # Specific provider
    """

    def __init__(self, settings: Settings):
        """
        Initialize the factory with settings.

        Args:
            settings: Application settings containing LLM configuration.
        """
        self._settings = settings
        self._instances: dict[LLMProvider, LLMClient] = {}

    def create(self, provider: LLMProvider | None = None) -> LLMClient:
        """
        Create or retrieve an LLM client instance.

        Uses singleton pattern per provider - creates once, reuses after.

        Args:
            provider: Specific provider to use. If None, uses the
                provider configured in settings.llm.agent.

        Returns:
            LLM client instance.

        Raises:
            ValueError: If the provider is not supported.
        """
        provider = provider or self._settings.llm.agent

        # Return existing instance if available (singleton per provider)
        if provider in self._instances:
            logger.debug(f"Reusing existing {provider.value} client instance")
            return self._instances[provider]

        # Create new instance
        logger.info(f"Creating new {provider.value} client instance")
        client = self._create_client(provider)
        self._instances[provider] = client
        return client

    def _create_client(self, provider: LLMProvider) -> LLMClient:
        """
        Create a new LLM client for the given provider.

        Args:
            provider: Provider to create client for.

        Returns:
            New LLM client instance.

        Raises:
            ValueError: If provider is not supported.
        """
        # Import here to avoid circular imports and allow lazy loading
        if provider == LLMProvider.GEMINI:
            from infrastructure.llm.gemini import GeminiLLM

            return GeminiLLM(self._settings)

        elif provider == LLMProvider.NVIDIA:
            from infrastructure.llm.nvidia import NvidiaLLM

            return NvidiaLLM(self._settings)

        elif provider == LLMProvider.OLLAMA:
            from infrastructure.llm.ollama import OllamaLLM

            return OllamaLLM(self._settings)

        raise ValueError(f"Unsupported LLM provider: {provider}")

    def clear_instances(self) -> None:
        """Clear all cached instances. Useful for testing."""
        self._instances.clear()
