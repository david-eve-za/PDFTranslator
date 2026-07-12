"""NVIDIA NIM LLM implementation."""

import logging
from pathlib import Path

from langchain_core.rate_limiters import InMemoryRateLimiter
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_text_splitters import NLTKTextSplitter
from transformers import AutoTokenizer

from pdftranslator.core.config.settings import Settings
from pdftranslator.core.config.llm import BCP47Language
from pdftranslator.infrastructure.llm.base import BaseLLM
from pdftranslator.infrastructure.llm.token_chunk_calculator import TokenChunkCalculator

logger = logging.getLogger(__name__)

# Default timeout for LLM calls (1 hour in seconds)
DEFAULT_TIMEOUT = 3600


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

        # Create model with timeout in model_kwargs (deprecated parameter)
        timeout = config.request_timeout or DEFAULT_TIMEOUT
        self._model = ChatNVIDIA(
            model=config.model_name,
            temperature=config.temperature,
            top_p=config.top_p,
            max_tokens=config.max_output_tokens,
            rate_limiter=rate_limiter,
            model_kwargs={"request_timeout": timeout},
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

    def get_current_model_name(self) -> str:
        """Get the current model name."""
        return self._settings.llm.nvidia.model_name

    def count_tokens(self, text: str) -> int:
        """Count tokens using the tokenizer."""
        token_ids = self._tokenizer.encode(text, add_special_tokens=False)
        return len(token_ids)

    def split_into_limit(
        self,
        text: str,
        language: BCP47Language = BCP47Language.ENGLISH,
        source_lang: str = "en",
        target_lang: str = "es",
    ) -> list[str]:
        """
        Split text into chunks optimized for translation.

        Args:
            text: Text to split.
            language: BCP 47 language code for NLTK sentence splitting.
            source_lang: Source language code for expansion ratio.
            target_lang: Target language code for expansion ratio.

        Returns:
            List of text chunks.
        """
        # Load prompt template
        template = self._load_prompt_template()

        # Calculate optimal chunk size using TokenChunkCalculator
        calculator = TokenChunkCalculator(self, self._settings.llm.nvidia)
        prompt_tokens = calculator.measure_prompt_tokens(
            template, source_lang, target_lang
        )
        expansion_ratio = calculator.get_expansion_ratio(source_lang, target_lang)
        chunk_size = calculator.calculate_chunk_size(prompt_tokens, expansion_ratio)

        logger.info(
            f"Adaptive chunking: prompt={prompt_tokens} tokens, "
            f"expansion={expansion_ratio:.2f} ({source_lang}->{target_lang}), "
            f"chunk_size={chunk_size} tokens"
        )

        # Use NLTKTextSplitter with calculated chunk size
        text_splitter = NLTKTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=0,
            language=language.to_nltk_name(),
            length_function=self.count_tokens,
        )

        return text_splitter.split_text(text)

    def _load_prompt_template(self) -> str:
        """Load translation prompt template from configured path."""
        prompt_path = self._settings.paths.translation_prompt_path
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()

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
