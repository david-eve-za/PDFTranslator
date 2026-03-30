"""Google Gemini LLM implementation."""

import logging
import os
import time
from pathlib import Path

import sentencepiece as spm
from google import genai
from google.api_core import exceptions as google_exceptions
from langchain_core.rate_limiters import InMemoryRateLimiter
from langchain_core.runnables import Runnable
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_text_splitters import NLTKTextSplitter

from config.settings import Settings
from config.llm import BCP47Language
from infrastructure.llm.base import BaseLLM

logger = logging.getLogger(__name__)


class GeminiLLM(BaseLLM):
    """Google Gemini LLM connector with model rotation support."""

    def __init__(self, settings: Settings):
        """
        Initialize Gemini LLM with settings.

        Args:
            settings: Application settings containing Gemini configuration.
        """
        super().__init__(settings)

        config = settings.llm.gemini
        self.genai_client = genai.Client()

        if not config.model_names:
            raise ValueError("Gemini model names list cannot be empty")

        self.model_names = config.model_names
        self._current_model_index = 0

        # Get API key
        self._api_key = self._get_api_key()

        # Initialize tokenizer
        self._tokenizer = self._initialize_tokenizer()

        # Create LLM client
        self._llm_client = self._create_llm_client_for_current_model()

        logger.info(
            f"GeminiLLM initialized. Starting with model '{self.get_current_model_name()}'"
        )

    def call_model(self, prompt: str) -> str:
        """Call Gemini model with retry and rotation logic."""
        initial_model_index = self._current_model_index
        first_exhaustion_error = None
        max_retries = 10

        for attempt in range(max_retries):
            current_model_name = self.get_current_model_name()
            logger.debug(
                f"Attempting to call model '{current_model_name}' "
                f"(Attempt {attempt + 1}/{max_retries})"
            )

            try:
                response = self._llm_client.invoke(prompt)
                if response.content:
                    logger.info(
                        f"Call to '{current_model_name}' successful. "
                        f"Usage: {response.usage_metadata}"
                    )
                    return response.content
                else:
                    logger.warning(
                        f"Model '{current_model_name}' returned empty response. "
                        f"Retrying in 60 seconds..."
                    )
                    time.sleep(60)

            except google_exceptions.ResourceExhausted as e:
                if first_exhaustion_error is None:
                    first_exhaustion_error = e
                logger.warning(
                    f"Model '{current_model_name}' exhausted. Rotating. Error: {e}"
                )
                self._rotate_to_next_model()

                if self._current_model_index == initial_model_index:
                    logger.error("All models in rotation are exhausted.")
                    raise RuntimeError(
                        "All available models are exhausted"
                    ) from first_exhaustion_error

                self._llm_client = self._create_llm_client_for_current_model()

            except (
                google_exceptions.BadRequest,
                google_exceptions.PermissionDenied,
                google_exceptions.NotFound,
            ) as e:
                logger.error(f"Non-retryable API error: {e}", exc_info=True)
                raise RuntimeError(f"Non-retryable API error: {e}") from e

            except Exception as e:
                logger.error(f"Unexpected error: {e}", exc_info=True)
                raise RuntimeError(f"Unexpected error: {e}") from e

        raise RuntimeError("Failed to get valid response after multiple retries")

    def get_current_model_name(self) -> str:
        """Get the current model name."""
        return self.model_names[self._current_model_index]

    def count_tokens(self, text: str) -> int:
        """Count tokens using SentencePiece tokenizer."""
        return len(self._tokenizer.encode(text, out_type=int))

    def split_into_limit(
        self, text: str, language: BCP47Language = BCP47Language.ENGLISH
    ) -> list[str]:
        """Split text into chunks for translation."""
        text_splitter = NLTKTextSplitter(
            chunk_size=self._settings.llm.gemini.context_size,
            chunk_overlap=0,
            language=language.value,
            length_function=self.count_tokens,
        )
        return text_splitter.split_text(text)

    def _get_api_key(self) -> str:
        """Get Google API key from environment."""
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY environment variable not set")
        return api_key

    def _rotate_to_next_model(self) -> None:
        """Rotate to the next model in the list."""
        self._current_model_index = (self._current_model_index + 1) % len(
            self.model_names
        )
        logger.info(f"Rotated to model: '{self.get_current_model_name()}'")

    def _create_llm_client_for_current_model(self) -> Runnable:
        """Create LLM client for the current model."""
        model_name = self.get_current_model_name()
        config = self._settings.llm.gemini

        rpm = config.rate_limit
        requests_per_second = rpm / 60.0
        logger.info(f"Creating LLM client for '{model_name}' with rate limit {rpm} RPM")

        rate_limiter = InMemoryRateLimiter(
            requests_per_second=requests_per_second,
            max_bucket_size=config.max_bucket_size,
        )

        llm_client = ChatGoogleGenerativeAI(
            model=model_name,
            temperature=config.temperature,
            top_p=config.top_p,
            rate_limiter=rate_limiter,
            verbose=True,
            request_timeout=config.request_timeout,
        )

        return llm_client.with_retry(
            stop_after_attempt=config.retry_attempts,
            retry_if_exception_type=(
                google_exceptions.InternalServerError,
                google_exceptions.ServiceUnavailable,
                google_exceptions.DeadlineExceeded,
            ),
        )

    def _initialize_tokenizer(self) -> spm.SentencePieceProcessor:
        """Initialize SentencePiece tokenizer."""
        tokenizer_path = Path(self._settings.paths.tokenizer_path)

        if not tokenizer_path.is_file():
            logger.error(f"Tokenizer not found at: {tokenizer_path}")
            raise FileNotFoundError(f"Tokenizer not found at: {tokenizer_path}")

        logger.info(f"Loading tokenizer from: {tokenizer_path}")
        return spm.SentencePieceProcessor(model_file=str(tokenizer_path))
