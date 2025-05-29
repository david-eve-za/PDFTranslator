import logging
import os
from abc import ABC, abstractmethod

from google.api_core import exceptions as google_exceptions
from langchain_core.rate_limiters import InMemoryRateLimiter
from langchain_google_genai import ChatGoogleGenerativeAI

logger = logging.getLogger(__name__)

class LLMService(ABC):
    @abstractmethod
    def call_model(self, prompt: str) -> str:
        pass

class GeminiAI(LLMService):
    DEFAULT_MODEL_NAME = "gemini-2.0-flash"
    DEFAULT_TEMPERATURE = 0.2
    DEFAULT_TOP_P = 0.95
    DEFAULT_TOP_K = 40
    DEFAULT_RETRY_ATTEMPTS = 6
    DEFAULT_REQUESTS_PER_SECOND = .25
    DEFAULT_CHECK_EVERY_N_SECONDS = 0.1
    DEFAULT_MAX_BUCKET_SIZE = 10

    def __init__(self,
                 model_name: str = DEFAULT_MODEL_NAME,
                 temperature: float = DEFAULT_TEMPERATURE,
                 top_p: float = DEFAULT_TOP_P,
                 top_k: int = DEFAULT_TOP_K,
                 retry_attempts: int = DEFAULT_RETRY_ATTEMPTS,
                 requests_per_second: float = DEFAULT_REQUESTS_PER_SECOND,
                 check_every_n_seconds: float = DEFAULT_CHECK_EVERY_N_SECONDS,
                 max_bucket_size: int = DEFAULT_MAX_BUCKET_SIZE):
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            logger.error("GOOGLE_API_KEY environment variable not set.")
            raise ValueError("GOOGLE_API_KEY environment variable not set.")

        self.model_name = model_name

        rate_limiter = InMemoryRateLimiter(
            requests_per_second=requests_per_second,
            check_every_n_seconds=check_every_n_seconds,
            max_bucket_size=max_bucket_size
        )

        try:
            llm_client = ChatGoogleGenerativeAI(
                api_key=api_key,
                model=self.model_name,
                temperature=temperature,
                top_p=top_p,
                top_k=top_k,
                rate_limiter=rate_limiter,
                verbose=True
            )
            self.llm = llm_client.with_retry(
                stop_after_attempt=retry_attempts,
                retry_if_exception_type=(
                    google_exceptions.ResourceExhausted,
                    google_exceptions.InternalServerError,
                    google_exceptions.ServiceUnavailable,
                    google_exceptions.DeadlineExceeded,
                    google_exceptions.GoogleAPICallError
                )
            )
        except Exception as e:
            logger.exception(f"Failed to initialize ChatGoogleGenerativeAI for model {self.model_name}: {e}")
            raise

    def call_model(self, prompt: str) -> str:
        try:
            response = self.llm.invoke(prompt)
            logger.info(f"Usage metadata for model {self.model_name}: {response.usage_metadata}")
            if hasattr(response, 'content'):
                return response.content
            return str(response)
        except (google_exceptions.BadRequest,
                google_exceptions.PermissionDenied,
                google_exceptions.NotFound) as e:
            logger.error(f"Non-retryable API error with model {self.model_name}: {e.__class__.__name__} - {e}")
            raise
        except (google_exceptions.ResourceExhausted,
                google_exceptions.InternalServerError,
                google_exceptions.ServiceUnavailable,
                google_exceptions.DeadlineExceeded,
                google_exceptions.GoogleAPICallError) as e:
            logger.error(
                f"API error persisted after retries for model {self.model_name}: {e.__class__.__name__} - {e}"
            )
            raise google_exceptions.GoogleAPICallError(f"API call failed for model {self.model_name} after retries.") from e
        except Exception as e:
            logger.error(
                f"Unexpected error invoking model {self.model_name}: {e.__class__.__name__} - {e}"
            )
            raise Exception(f"An unexpected error occurred with model {self.model_name}.") from e
