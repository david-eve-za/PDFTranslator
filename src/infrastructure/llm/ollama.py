"""Ollama local LLM implementation."""

import logging
from pathlib import Path

from langchain_ollama import ChatOllama
from langchain_text_splitters import NLTKTextSplitter
from transformers import AutoTokenizer

from src.core.config.settings import Settings
from src.core.config.llm import BCP47Language
from src.infrastructure.llm.base import BaseLLM

logger = logging.getLogger(__name__)

# Default timeout for LLM calls (30 minutes in seconds)
DEFAULT_TIMEOUT = 1800


class OllamaLLM(BaseLLM):
    """Ollama local LLM connector using langchain-ollama."""

    def __init__(self, settings: Settings):
        """
        Initialize Ollama LLM with settings.

        Args:
            settings: Application settings containing Ollama configuration.
        """
        super().__init__(settings)

        config = settings.llm.ollama
        self._tokenizer = self._load_tokenizer(config)

        self._model = ChatOllama(
            model=config.model_name,
            validate_model_on_init=config.validate_model,
            temperature=config.temperature,
            top_p=config.top_p,
            request_timeout=DEFAULT_TIMEOUT,
            verbose=True,
            reasoning=False,
        )

        logger.info(f"OllamaLLM initialized with model: {config.model_name}")

    def call_model(self, prompt: str) -> str:
        """Call the Ollama model with a prompt."""
        response = self._model.invoke(prompt)
        logger.info(
            f"Call to '{self.get_current_model_name()}' successful. "
            f"Usage: {response.usage_metadata}"
        )
        return response.content

    def get_current_model_name(self) -> str:
        """Get the current model name."""
        return self._settings.llm.ollama.model_name

    def count_tokens(self, text: str) -> int:
        """Count tokens using the tokenizer."""
        token_ids = self._tokenizer.encode(text, add_special_tokens=False)
        return len(token_ids)

    def split_into_limit(
        self, text: str, language: BCP47Language = BCP47Language.ENGLISH
    ) -> list[str]:
        """Split text into chunks for translation."""
        text_splitter = NLTKTextSplitter(
            chunk_size=self._settings.llm.ollama.context_size,
            chunk_overlap=0,
            language=language.to_nltk_name(),
            length_function=self.count_tokens,
        )
        return text_splitter.split_text(text)

    def _load_tokenizer(self, config) -> AutoTokenizer:
        """
        Load or download tokenizer.

        Args:
            config: Ollama configuration containing tokenizer settings.

        Returns:
            Loaded AutoTokenizer instance.
        """
        tokenizer_dir = Path(config.local_tokenizer_dir)

        if tokenizer_dir.exists():
            logger.info(f"Tokenizer already cached in {tokenizer_dir}")
        else:
            logger.info(f"Downloading tokenizer for {config.model_id}...")
            tokenizer = AutoTokenizer.from_pretrained(
                config.local_tokenizer_name, use_fast=True
            )
            tokenizer_dir.mkdir(parents=True, exist_ok=True)
            tokenizer.save_pretrained(tokenizer_dir)
            logger.info(f"Tokenizer saved in {tokenizer_dir}")

        return AutoTokenizer.from_pretrained(tokenizer_dir, use_fast=True)
