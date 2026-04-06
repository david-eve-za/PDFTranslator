"""NVIDIA NIM LLM implementation."""

import logging
from pathlib import Path

from langchain_core.rate_limiters import InMemoryRateLimiter
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_text_splitters import NLTKTextSplitter
from transformers import AutoTokenizer

from config.settings import Settings
from config.llm import BCP47Language
from infrastructure.llm.base import BaseLLM

logger = logging.getLogger(__name__)


class NvidiaLLM(BaseLLM):
    """NVIDIA NIM cloud API connector using langchain-nvidia-ai-endpoints."""

    def __init__(self, settings: Settings):
        """
        Initialize NVIDIA LLM with settings.

        Args:
            settings: Application settings containing NVIDIA configuration.
        """
        super().__init__(settings)

        # Get NVIDIA-specific config
        config = settings.llm.nvidia

        # Initialize tokenizer
        self._tokenizer = self._load_tokenizer(config)

        # Create rate limiter
        rpm = config.rate_limit
        requests_per_second = rpm / 60.0
        logger.info(f"Creating NVIDIA LLM client with rate limit of {rpm} RPM")

        rate_limiter = InMemoryRateLimiter(
            requests_per_second=requests_per_second,
            max_bucket_size=rpm,
        )

        # Create model
        self._model = ChatNVIDIA(
            model=config.model_name,
            temperature=config.temperature,
            top_p=config.top_p,
            max_tokens=config.max_output_tokens,
            rate_limiter=rate_limiter,
            verbose=True,
        )

        logger.info(f"NvidiaLLM initialized with model: {config.model_name}")

    def call_model(self, prompt: str) -> str:
        """Call the NVIDIA model with a prompt."""
        response = self._model.invoke(prompt)
        logger.info(
            f"Call to '{self.get_current_model_name()}' successful. "
            f"Usage: {response.usage_metadata}"
        )
        return response.content

    def call_model_with_temperature(self, prompt: str, temperature: float) -> str:
        """
        Call the NVIDIA model with a custom temperature override.

        Args:
            prompt: The prompt to send to the model.
            temperature: Temperature value (0.0 to 2.0) for response randomness.

        Returns:
            The model's response as a string.
        """
        original_temp = self._model.temperature
        self._model.temperature = temperature
        try:
            response = self._model.invoke(prompt)
            logger.info(
                f"Call to '{self.get_current_model_name()}' with temp={temperature} successful. "
                f"Usage: {response.usage_metadata}"
            )
            return response.content
        finally:
            self._model.temperature = original_temp

    def get_current_model_name(self) -> str:
        """Get the current model name."""
        return self._settings.llm.nvidia.model_name

    def count_tokens(self, text: str) -> int:
        """Count tokens using the tokenizer."""
        token_ids = self._tokenizer.encode(text, add_special_tokens=False)
        return len(token_ids)

    def split_into_limit(
        self, text: str, language: BCP47Language = BCP47Language.ENGLISH
    ) -> list[str]:
        """
        Split text into chunks for translation.

        Args:
            text: Text to split.
            language: BCP 47 language code for splitting.

        Returns:
            List of text chunks.
        """
        # Use 3x output tokens as chunk size (input can be larger)
        chunk_size = self._settings.llm.nvidia.max_output_tokens

        text_splitter = NLTKTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=0,
            language=language.to_nltk_name(),
            length_function=self.count_tokens,
        )

        return text_splitter.split_text(text)

    def _load_tokenizer(self, config) -> AutoTokenizer:
        """
        Load or download tokenizer.

        Args:
            config: NVIDIA configuration containing tokenizer settings.

        Returns:
            Loaded AutoTokenizer instance.
        """
        tokenizer_dir = Path(config.local_tokenizer_dir)

        if tokenizer_dir.exists():
            logger.info(f"Tokenizer already cached in {tokenizer_dir}")
        else:
            logger.info(f"Downloading tokenizer for {config.local_tokenizer_name}...")
            tokenizer = AutoTokenizer.from_pretrained(
                config.local_tokenizer_name, use_fast=True
            )
            tokenizer_dir.mkdir(parents=True, exist_ok=True)
            tokenizer.save_pretrained(tokenizer_dir)
            logger.info(f"Tokenizer saved in {tokenizer_dir}")

        return AutoTokenizer.from_pretrained(tokenizer_dir, use_fast=True)
