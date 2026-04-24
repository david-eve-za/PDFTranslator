import logging
import re

from pdftranslator.core.config.settings import Settings
from pdftranslator.infrastructure.llm.gemini import GeminiLLM
from pdftranslator.infrastructure.llm.nvidia import NvidiaLLM
from pdftranslator.infrastructure.llm.ollama import OllamaLLM
from pdftranslator.infrastructure.llm.base import BaseLLM

# Configure logging
logger = logging.getLogger(__name__)


class Translator:
    """
    Translates text using configurable LLM backends with chunking support.
    """

    _EMPTY_CHUNK_MARKER_FORMAT = "[EMPTY_TRANSLATION_CHUNK_{index}]"
    _ERROR_CHUNK_MARKER_FORMAT = "[TRANSLATION_ERROR_CHUNK_{index}]"

    def __init__(self, progress=None):
        """
        Initializes the Translator, creating the appropriate LLM client
        based on the global configuration.
        """
        self._settings = Settings.get()
        self.llm_client = self._create_llm_client()
        self._progress = progress

    def _create_llm_client(self) -> BaseLLM:
        """Factory function to create an LLM client."""
        agent = self._settings.agent.value  # LLMProvider enum
        if agent == "gemini":
            return GeminiLLM(self._settings)
        elif agent == "ollama":
            return OllamaLLM(self._settings)
        elif agent == "nvidia":
            return NvidiaLLM(self._settings)
        else:
            raise ValueError(f"Unsupported agent specified in config: {agent}")

    def _get_translation_prompt_template(
        self, source_lang: str, target_lang: str
    ) -> str:
        with open(
            self._settings.paths.translation_prompt_path, "r", encoding="utf-8"
        ) as f:
            prompt_template = f.read()
        return prompt_template.format(source_lang=source_lang, target_lang=target_lang)

    def _translate_single_chunk(
        self, chunk: str, chunk_index: int, base_prompt_template: str
    ) -> str:
        prompt = base_prompt_template.format(text_chunk=chunk)
        try:
            translated_chunk = self.llm_client.call_model(prompt)
            return translated_chunk if translated_chunk is not None else ""
        except Exception as e:
            logger.error(f"Error during LLM call for chunk {chunk_index + 1}: {e}")
            return self._ERROR_CHUNK_MARKER_FORMAT.format(index=chunk_index + 1)

    def _translate_chunks(
        self, chunks: list[str], source_lang: str, target_lang: str
    ) -> list[str]:
        translated_chunks = []
        prompt_template = self._get_translation_prompt_template(
            source_lang, target_lang
        )

        if self._progress:
            iterator = self._progress(enumerate(chunks), desc="Translating Chunks...")
        else:
            iterator = enumerate(chunks)

        for i, chunk in iterator:
            translated_chunk = self._translate_single_chunk(chunk, i, prompt_template)
            translated_chunks.append(translated_chunk)

        return translated_chunks

    def translate_text(self, full_text: str, source_lang: str, target_lang: str) -> str:
        original_chunks = self.llm_client.split_into_limit(full_text)

        logger.info(
            f" - Original text split into {len(original_chunks)} chunks for translation."
        )

        if not original_chunks:
            logger.warning(
                " - Warning: The original text resulted in 0 chunks. Check input."
            )
            return ""

        translated_text_parts = self._translate_chunks(
            original_chunks, source_lang, target_lang
        )

        logger.info("Translation of all chunks completed.")
        full_translated_text = "\n\n".join(translated_text_parts)
        full_translated_text = re.sub(r"\n{3,}", "\n\n", full_translated_text).strip()

        return full_translated_text
