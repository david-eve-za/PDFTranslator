import logging
import os
import random
import time

from google import genai
# Import specific exceptions for better handling
from google.api_core import exceptions as google_exceptions
from google.genai import \
    types  # types.GenerateContentResponse is not directly used, but types.GenerateContentConfig is.

from LLM.APIClient import APIClient
from PDFv2 import CommonPrompts  # Assuming PDFv2 contains CommonPrompts

# Configure logging
logger = logging.getLogger(__name__)


class GeminiAI(APIClient, CommonPrompts):
    # Retry parameters
    MAX_RETRIES = 3
    INITIAL_BACKOFF_SECONDS = 1.0  # Initial wait time in seconds
    BACKOFF_FACTOR = 2.0  # Multiplier for backoff delay
    JITTER_FACTOR = 0.5  # Percentage for random jitter (+/-)

    def __init__(self):
        # Rate limits for Gemini Flash (adjust if using Pro or other models)
        # Using 15 RPM as a conservative default for generateContent.
        # Tokens per minute is high (e.g., 1M for Flash), so RPM is often the bottleneck.
        APIClient.__init__(self=self, tokens_per_minute=1000000, calls_per_minute=15, daily_calls=1500)
        CommonPrompts.__init__(self=self)

        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY environment variable not set.")

        # Initialize the Gemini client.
        # We use methods from this client instance (e.g., self.llm.models.generate_content)
        # rather than top-level genai functions that might rely on global configuration.
        self.llm = genai.Client(api_key=api_key)

        # Use the specific model name recommended by Google
        self._gemini_model = "gemini-1.5-flash-latest"  # Updated to common "latest" alias

        # System prompt considerations:
        # The new Gemini API typically includes system instructions within the 'contents'
        # or via 'system_instruction' in GenerateContentConfig if supported.
        # This class assumes the prompt passed to call_model includes all necessary instructions.

        self.generation_config = genai.types.GenerateContentConfig(
            temperature=0.2,
            top_p=0.95,
            top_k=40,
            response_mime_type="text/plain",
            # max_output_tokens=8192, # Max for Flash 1.5, be mindful of total context window
            # system_instruction="Your system prompt here", # Use if model supports it
        )

    def count_tokens(self, text: str) -> int:
        """
        Counts tokens using the genai library for the configured model.

        Args:
            text: The text to count tokens for.

        Returns:
            The number of tokens, or 0 if an error occurs during counting.
        """
        if not text:  # Avoids API call for empty string, count is 0.
            return 0
        try:
            # Model name needs 'models/' prefix for client methods
            return self.llm.count_tokens(model=f"models/{self._gemini_model}", contents=text).total_tokens
        except Exception as e:
            logger.error(f"Error counting tokens for model {self._gemini_model}: {e}. Returning 0.")
            return 0

    def call_model(self, prompt: str) -> str:
        """
        Calls the Gemini model with the given prompt, including retry logic.

        Args:
            prompt: The prompt to send to the model.

        Returns:
            The model's response text.

        Raises:
            google_exceptions.BadRequest: If the request is invalid.
            google_exceptions.PermissionDenied: If there's an API key or permission issue.
            google_exceptions.NotFound: If the model name is invalid or resource not found.
            google_exceptions.GoogleAPICallError: For other API errors after retries are exhausted.
            Exception: For unexpected errors after retries are exhausted.
        """
        required_tokens = self.count_tokens(prompt)
        if required_tokens == 0 and prompt:  # Check if prompt is non-empty
            logger.warning(
                "Token count for a non-empty prompt returned 0 or failed. "
                "Proceeding, but rate limiting for tokens might be inaccurate."
            )

        self.wait_if_needed(required_tokens)
        logger.info(f"Sending prompt to {self._gemini_model} (estimated {required_tokens} tokens).")

        current_backoff = self.INITIAL_BACKOFF_SECONDS
        last_api_exception = None

        for attempt in range(self.MAX_RETRIES):
            try:
                response = self.llm.generate_content(
                    model=f"models/{self._gemini_model}",
                    contents=[prompt],  # Simple text prompt
                    generation_config=self.generation_config,
                    # safety_settings=... # Consider adding safety settings if needed
                )

                # Log token usage
                calculated_input_tokens = required_tokens  # From initial count
                calculated_output_tokens = self.count_tokens(response.text)
                calculated_total_tokens = calculated_input_tokens + calculated_output_tokens

                if hasattr(response, 'usage_metadata') and response.usage_metadata:
                    usage = response.usage_metadata
                    logger.info(
                        f"Response from {self._gemini_model}. "
                        f"API Usage - Prompt: {usage.prompt_token_count}, "
                        f"Candidates: {usage.candidates_token_count}, "
                        f"Total: {usage.total_token_count}. "
                        f"(Our calculation: In={calculated_input_tokens}, Out={calculated_output_tokens}, Total={calculated_total_tokens})"
                    )
                    # Here you might record usage.total_token_count with self.record_call if APIClient needs it
                else:
                    logger.info(
                        f"Response from {self._gemini_model}. Usage metadata not in response. "
                        f"Using our calculation: In={calculated_input_tokens}, Out={calculated_output_tokens}, Total={calculated_total_tokens}."
                    )
                    # Here you might record calculated_total_tokens with self.record_call

                if not response.text or not response.text.strip():
                    logger.warning(
                        f"Received empty or whitespace-only response from {self._gemini_model} on attempt {attempt + 1}. "
                        "Treating as valid (empty) response."
                    )
                    # If an empty response should be retried, raise an error here.
                    # e.g., raise ValueError("Model returned an empty response")

                return response.text  # Success

            # --- Non-Retryable Google API Errors ---
            except (google_exceptions.BadRequest,
                    google_exceptions.PermissionDenied,
                    google_exceptions.NotFound) as e:
                logger.error(f"Non-retryable API error with {self._gemini_model}: {e}")
                raise  # Re-raise immediately, no retry

            # --- Retryable Google API Errors (includes transient network issues via GoogleAPICallError) ---
            except (google_exceptions.ResourceExhausted,
                    google_exceptions.InternalServerError,
                    google_exceptions.ServiceUnavailable,
                    google_exceptions.GoogleAPICallError) as e:
                logger.warning(
                    f"Retryable API error ({e.__class__.__name__}) with {self._gemini_model} "
                    f"on attempt {attempt + 1}/{self.MAX_RETRIES}: {e}"
                )
                last_api_exception = e

            # --- Catch-all for other unexpected errors (also treated as potentially retryable) ---
            except Exception as e:
                logger.warning(
                    f"Unexpected error with {self._gemini_model} "
                    f"on attempt {attempt + 1}/{self.MAX_RETRIES}: {e}"
                )
                last_api_exception = e  # Store for potential re-raise

            # --- Retry Logic: If this point is reached, an error occurred that might be retried ---
            if attempt < self.MAX_RETRIES - 1:
                jitter = random.uniform(-self.JITTER_FACTOR, self.JITTER_FACTOR)
                wait_time = current_backoff * (1 + jitter)
                wait_time = max(0, wait_time)  # Ensure non-negative wait time

                logger.info(f"Waiting {wait_time:.2f} seconds before retry {attempt + 2}/{self.MAX_RETRIES}...")
                time.sleep(wait_time)
                current_backoff *= self.BACKOFF_FACTOR
            else:
                # This was the last attempt, and it failed.
                logger.error(
                    f"Max retries ({self.MAX_RETRIES}) reached for {self._gemini_model}. "
                    f"Last error: {last_api_exception}"
                )
                if last_api_exception:  # Should always be set if we are in this path after an error
                    raise last_api_exception from last_api_exception  # Re-raise the specific exception
                else:
                    # This fallback should ideally not be hit if last_api_exception is always set.
                    raise RuntimeError(
                        f"Max retries reached for {self._gemini_model}, but no specific exception was captured to re-raise.")

        # This part of the code should be unreachable if MAX_RETRIES >= 1,
        # as the loop will either return successfully or raise an exception.
        # Adding a safeguard here.
        logger.critical(
            f"call_model for {self._gemini_model} exited retry loop unexpectedly. This indicates a logic flaw.")
        if last_api_exception:
            raise last_api_exception  # type: ignore
        raise RuntimeError(
            f"Model call to {self._gemini_model} failed after all retries without a specific exception being re-raised from the loop.")
