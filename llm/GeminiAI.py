from __future__ import annotations

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

from GlobalConfig import GlobalConfig
from llm.base_llm import BaseLLM


# --- Custom Exceptions ---
class GeminiAIError(Exception):
    """Base exception for errors in the GeminiAI service."""

    pass


class GeminiAIInitializationError(GeminiAIError):
    """Raised when the GeminiAI service fails to initialize."""

    pass


class GeminiAPICallError(GeminiAIError):
    """Raised when a call to the Gemini API fails."""

    pass


def _get_api_key() -> str:
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY environment variable not set.")
    return api_key


class GeminiAI(BaseLLM):
    """BaseLLM implementation for Google's Gemini models."""

    def __init__(self):
        self.config = GlobalConfig()
        self.genai_client = genai.Client()
        self._logger = logging.getLogger(__name__)
        self._logger.info("Initializing GeminiAI...")

        if not self.config.gemini_model_names:
            raise GeminiAIInitializationError(
                "Gemini model names list cannot be empty in config."
            )

        self.model_names = self.config.gemini_model_names
        self._current_model_index = 0

        try:
            self._api_key = _get_api_key()
            self.tokenizer = self._initialize_tokenizer()
            self._llm_client = self._create_llm_client_for_current_model()
        except (FileNotFoundError, ValueError) as e:
            self._logger.error(f"Initialization failed: {e}", exc_info=True)
            raise GeminiAIInitializationError(f"Initialization failed: {e}") from e

        self._logger.info(
            f"GeminiAI service initialized successfully. Starting with model '{self.get_current_model_name()}'."
        )

    def get_current_model_name(self) -> str:
        return self.model_names[self._current_model_index]

    def call_model(self, prompt: str) -> str | None:
        initial_model_index = self._current_model_index
        first_exhaustion_error = None
        max_retries = 10

        for attempt in range(max_retries):
            current_model_name = self.get_current_model_name()
            self._logger.debug(
                f"Attempting to call model '{current_model_name}' (Attempt {attempt + 1}/{max_retries})."
            )
            try:
                response = self._llm_client.invoke(prompt)
                if response.content:
                    self._logger.info(
                        f"Call to '{current_model_name}' successful. Usage: {response.usage_metadata}"
                    )
                    return response.content
                else:
                    self._logger.warning(
                        f"Model '{current_model_name}' returned an empty response. Retrying in 60 second..."
                    )
                    time.sleep(60)

            except google_exceptions.ResourceExhausted as e:
                if first_exhaustion_error is None:
                    first_exhaustion_error = e
                self._logger.warning(
                    f"Model '{current_model_name}' is exhausted. Rotating. Error: {e}"
                )
                self._rotate_to_next_model()
                if self._current_model_index == initial_model_index:
                    self._logger.error("All models in the rotation are exhausted.")
                    raise GeminiAPICallError(
                        "All available models are exhausted."
                    ) from first_exhaustion_error
                self._llm_client = self._create_llm_client_for_current_model()
            except (
                google_exceptions.BadRequest,
                google_exceptions.PermissionDenied,
                google_exceptions.NotFound,
            ) as e:
                self._logger.error(
                    f"Non-retryable API error with '{current_model_name}': {e}",
                    exc_info=True,
                )
                raise GeminiAPICallError(f"Non-retryable API error: {e}") from e
            except Exception as e:
                self._logger.error(
                    f"An unexpected error occurred with '{current_model_name}': {e}",
                    exc_info=True,
                )
                raise GeminiAIError(f"An unexpected error occurred: {e}") from e

        self._logger.error(
            f"Failed to get a valid response from model '{self.get_current_model_name()}' after {max_retries} attempts."
        )
        raise GeminiAPICallError(
            "Failed to get a valid response after multiple retries."
        )

    def count_tokens(self, text: str) -> int:
        return len(self.tokenizer.encode(text, out_type=int))

    def split_into_limit(self, text: str) -> list[str]:
        text_spliter = NLTKTextSplitter(
            chunk_size=self._limit_tokens(),
            chunk_overlap=0,
            language="english",
            length_function=self.count_tokens,
        )
        return text_spliter.split_text(text)

    def _limit_tokens(self) -> int:
        return self.config.gemini_context_size

    def _rotate_to_next_model(self):
        self._current_model_index = (self._current_model_index + 1) % len(
            self.model_names
        )
        self._logger.info(f"Rotated to next model: '{self.get_current_model_name()}'.")

    def _create_llm_client_for_current_model(self) -> Runnable:
        model_name = self.get_current_model_name()
        rpm = self.config.gemini_model_rate_limits.get(
            model_name, self.config.gemini_default_fallback_rpm
        )
        requests_per_second = rpm / 60.0
        self._logger.info(
            f"Creating LLM client for '{model_name}' with rate limit of {rpm} RPM."
        )

        rate_limiter = InMemoryRateLimiter(
            requests_per_second=requests_per_second,
            max_bucket_size=self.config.gemini_max_bucket_size,
        )

        try:
            llm_client = ChatGoogleGenerativeAI(
                model=model_name,
                temperature=self.config.gemini_temperature,
                top_p=self.config.gemini_top_p,
                # top_k=self.config.gemini_top_k,
                rate_limiter=rate_limiter,
                verbose=True,
                request_timeout=self.config.gemini_request_timeout,
            )
            return llm_client.with_retry(
                stop_after_attempt=self.config.gemini_retry_attempts,
                retry_if_exception_type=(
                    google_exceptions.InternalServerError,
                    google_exceptions.ServiceUnavailable,
                    google_exceptions.DeadlineExceeded,
                ),
            )
        except Exception as e:
            self._logger.error(
                f"Failed to initialize client for '{model_name}': {e}", exc_info=True
            )
            raise GeminiAIInitializationError(
                f"Failed to initialize client for '{model_name}': {e}"
            ) from e

    def _initialize_tokenizer(self) -> spm.SentencePieceProcessor:
        tokenizer_path = Path(self.config.tokenizer_path)

        if not tokenizer_path.is_file():
            self._logger.error(f"Tokenizer model not found at path: {tokenizer_path}")
            raise FileNotFoundError(f"Tokenizer model not found at: {tokenizer_path}")

        self._logger.info(f"Loading tokenizer from: {tokenizer_path}")
        try:
            return spm.SentencePieceProcessor(model_file=str(tokenizer_path))
        except Exception as e:
            self._logger.error(
                f"Failed to load tokenizer model from '{tokenizer_path}': {e}",
                exc_info=True,
            )
            raise GeminiAIInitializationError(
                f"Failed to load tokenizer model: {e}"
            ) from e


if __name__ == "__main__":
    ai = genai.Client()
    for model in ai.models.list():
        # Revisar las acciones que soporta cada modelo
        if (
            hasattr(model, "supported_actions")
            and "generateContent" in model.supported_actions
        ):
            if "2.5" in model.name:
                print(
                    f"- {model.name}"
                )  # Nombre del recurso (ej: 'models/gemini-2.0-flash')
                print(
                    f"  Display Name: {model.display_name}"
                )  # Nombre para mostrar (ej: 'Gemini 2.0 Flash')
