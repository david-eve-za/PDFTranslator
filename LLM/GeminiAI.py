import logging
import os
import random
import time

from google import genai
# Import specific exceptions for better handling
from google.api_core import exceptions as google_exceptions
from google.genai import types

from LLM.APIClient import APIClient
from PDFv2 import CommonPrompts  # Assuming PDFv2 contains CommonPrompts

# Configure logging
logger = logging.getLogger(__name__)


class GeminiAI(APIClient, CommonPrompts):
    # Define retry parameters as class constants or configuration options
    MAX_RETRIES = 3
    INITIAL_BACKOFF_SECONDS = 1.0 # Initial wait time in seconds
    BACKOFF_FACTOR = 2.0 # Multiplier for backoff delay
    JITTER_FACTOR = 0.5 # Percentage for random jitter (+/-)

    def __init__(self):
        # Rate limits for Gemini Flash (adjust if using Pro or other models)
        # Flash: 60 RPM for non-tuning, 1500 RPM for tuning (using lower general limit)
        # Pro: 2 RPM (text)
        # Let's assume a general limit for Flash, adjust based on actual usage/model
        # The APIClient defaults might be okay, but check Gemini docs for specifics.
        # Using 15 RPM as a conservative default for generateContent based on some docs.
        # Tokens per minute is high (e.g., 1M for Flash), so RPM is often the bottleneck.
        APIClient.__init__(self=self, tokens_per_minute=1000000, calls_per_minute=15, daily_calls=1500)
        CommonPrompts.__init__(self=self)

        # Ensure API key is loaded
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY environment variable not set.")
        self.llm =genai.Client(api_key=api_key) # Configure the library globally

        # Use the client instance method for making calls if preferred,
        # but the top-level genai functions are often simpler.
        # self._client = genai.Client(api_key=api_key) # Keep if needed for other client methods

        # Use the specific model name recommended by Google
        self._gemini_model = "gemini-2.0-flash" # Or "gemini-1.5-pro-latest"

        # System prompt handling seems incorrect here. System prompts are usually
        # passed differently in the new API (often within the 'contents' list
        # with a specific role, or via 'system_instruction' if supported by the model/method).
        # Let's remove the direct system_prompt logic here and assume the prompt
        # passed to call_model includes any necessary instructions.
        # If a true system prompt is needed, adjust the call_model structure.
        # system_prompt = self._text_generation_prompt if model_type == "text" else self._audio_prompt
        # self._system_prompt_size = self.count_tokens(system_prompt) # This might be inaccurate depending on how system prompts are counted

        self.generation_config = genai.types.GenerateContentConfig(
            temperature=0.2, # Slightly increased for potentially better flow
            top_p=0.95,
            top_k=40,
            response_mime_type="text/plain",
            # max_output_tokens=8192, # Max for Flash 1.5, be mindful of total context window (1M tokens)
            # system_instruction=system_prompt, # Use this if model supports it and it's desired
        )

    # get_system_prompt_size might not be relevant anymore depending on prompt structure
    # def get_system_prompt_size(self):
    #     return self._system_prompt_size

    def count_tokens(self, text):
        """Counts tokens using the genai library."""
        # Add basic error handling for token counting
        try:
            # Ensure the model name used here matches the one for generation
            # Using the top-level function is often easier
            return self.llm.models.count_tokens(model=f"models/{self._gemini_model}", contents=text).total_tokens
        except Exception as e:
            logger.error(f"Error counting tokens: {e}. Returning 0.")
            # Decide how to handle this: raise error, return 0, return estimated length?
            # Returning 0 might cause issues later if used for chunking/limits.
            # Raising might be safer. For now, print and return 0.
            return 0

    def call_model(self, prompt):
        """
        Calls the Gemini model with retry logic for transient errors.

        Args:
            prompt (str): The prompt to send to the model.

        Returns:
            str: The model's response text, or None if retries fail.
        """
        required_tokens = self.count_tokens(prompt)
        # Add check for token count error (if count_tokens returns 0 on error)
        if required_tokens == 0 and len(prompt) > 0:
             logger.warning("Token count failed or returned 0 for non-empty prompt. Proceeding with caution.")
             # Optionally, estimate tokens based on characters if needed for wait_if_needed
             # required_tokens = len(prompt) // 3 # Rough estimate

        # Check rate limits before the first attempt
        self.wait_if_needed(required_tokens)
        logger.info(f"Sending prompt to {self._gemini_model} model ({required_tokens} tokens estimate)")

        current_backoff = self.INITIAL_BACKOFF_SECONDS
        for attempt in range(self.MAX_RETRIES):
            try:
                # Use the top-level generate_content function
                response = self.llm.models.generate_content(
                    model=f"models/{self._gemini_model}", # Model name needs 'models/' prefix here
                    contents=[prompt], # Simple text prompt
                    config=self.generation_config,
                    # safety_settings=... # Consider adding safety settings if needed
                )

                # Log token usage from metadata if available
                # Note: Usage metadata might not always be present or accurate for streamed/chunked responses
                # For simple generate_content, it should be available.
                input_tokens = self.count_tokens(prompt) # Recalculate or use previous value
                output_tokens = self.count_tokens(response.text)
                total_tokens = input_tokens + output_tokens
                if hasattr(response, 'usage_metadata'):
                     usage = response.usage_metadata
                     logger.info(f"Received response from {self._gemini_model}. "
                           f"Usage - Prompt: {usage.prompt_token_count}, "
                           f"Candidates: {usage.candidates_token_count}, "
                           f"Total: {usage.total_token_count}. "
                           f"(Calculated: In={input_tokens}, Out={output_tokens}, Total={total_tokens})")
                else:
                     logger.info(f"Received response from {self._gemini_model}. "
                           f"(Calculated: In={input_tokens}, Out={output_tokens}, Total={total_tokens}). "
                           f"Usage metadata not available in response.")

                # Basic validation of the response content
                if not response.text or not response.text.strip():
                    logger.warning("Received empty response from the model.")
                    # Decide if this should be retried or treated as failure.
                    # For now, return the empty response, caller can handle it.

                return response.text # Success

            # --- Specific, Retryable Google API Errors ---
            except google_exceptions.ResourceExhausted as e:
                print(f"Error: Rate limit exceeded (ResourceExhausted). Attempt {attempt + 1}/{self.MAX_RETRIES}. {e}")
                logger.error(f"Error: Rate limit exceeded (ResourceExhausted). Attempt {attempt + 1}/{self.MAX_RETRIES}. {e}")
                if attempt == self.MAX_RETRIES - 1:
                    logger.error("Max retries reached for ResourceExhausted.")
                    raise # Re-raise the last exception

            except google_exceptions.InternalServerError as e:
                logger.error(f"Error: Internal Server Error (500). Attempt {attempt + 1}/{self.MAX_RETRIES}. {e}")
                if attempt == self.MAX_RETRIES - 1:
                    logger.error("Max retries reached for InternalServerError.")
                    raise

            except google_exceptions.ServiceUnavailable as e:
                logger.error(f"Error: Service Unavailable (503). Attempt {attempt + 1}/{self.MAX_RETRIES}. {e}")
                if attempt == self.MAX_RETRIES - 1:
                    logger.error("Max retries reached for ServiceUnavailable.")
                    raise

            # --- Potentially Retryable General API Error (e.g., network issues) ---
            # Be cautious retrying generic errors, but sometimes needed for transient network flakes
            except google_exceptions.GoogleAPICallError as e:
                 # Check if it's a potentially transient error (e.g., based on status code if available)
                 logger.error(f"Error: Google API Call Error. Attempt {attempt + 1}/{self.MAX_RETRIES}. {e}")
                 if attempt == self.MAX_RETRIES - 1:
                     logger.error("Max retries reached for GoogleAPICallError.")
                     raise

            # --- Non-Retryable Google API Errors ---
            except google_exceptions.BadRequest as e:
                logger.error(f"Error: Invalid Request (BadRequest). Not retrying. {e}")
                raise # Bad request won't be fixed by retrying

            except google_exceptions.PermissionDenied as e:
                logger.error(f"Error: Permission Denied. Check API key and permissions. Not retrying. {e}")
                raise # Permission issue won't be fixed by retrying

            except google_exceptions.NotFound as e:
                logger.error(f"Error: Not Found (e.g., invalid model name?). Not retrying. {e}")
                raise # Not found won't be fixed by retrying

            # --- Catch-all for other unexpected errors ---
            except Exception as e:
                logger.error(f"Error: An unexpected error occurred. Attempt {attempt + 1}/{self.MAX_RETRIES}. {e}")
                # Decide whether to retry unexpected errors. It's often safer not to,
                # unless you know certain types might be transient.
                if attempt == self.MAX_RETRIES - 1:
                    print("Max retries reached for unexpected error.")
                    raise # Re-raise the last exception

            # --- Wait before retrying ---
            # Calculate delay with exponential backoff and jitter
            wait_time = current_backoff * (1 + random.uniform(-self.JITTER_FACTOR, self.JITTER_FACTOR))
            logger.info(f"Waiting {wait_time:.2f} seconds before retry...")
            time.sleep(wait_time)
            current_backoff *= self.BACKOFF_FACTOR # Increase backoff for next potential retry

        # This part should ideally not be reached if exceptions are re-raised on final failure
        logger.error("Model call failed after all retries.")
        return None # Return None if all retries fail and exceptions weren't re-raised (though re-raising is preferred)

# --- No changes needed below this line for the retry logic ---