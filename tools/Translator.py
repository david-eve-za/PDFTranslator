import logging
import re

from GlobalConfig import GlobalConfig
from llm.gemini_llm import GeminiLLM
from llm.nvidia_llm import NvidiaLLM
from llm.ollama_llm import OllamaLLM
from llm.base_llm import BaseLLM
from tools import OverlapCleaner
from tools.OverlapCleaner import clean_overlap

# Configure logging
logger = logging.getLogger(__name__)


class Translator:
    """
    Translates text using configurable LLM backends with chunking support.
    """

    _EMPTY_CHUNK_MARKER_FORMAT = "[EMPTY_TRANSLATION_CHUNK_{index}]"
    _ERROR_CHUNK_MARKER_FORMAT = "[TRANSLATION_ERROR_CHUNK_{index}]"

    def __init__(self, progress: gr.Progress = None):
        """
        Initializes the Translator, creating the appropriate LLM client
        based on the global configuration.
        """
        self.config = GlobalConfig()
        self.llm_client = self._create_llm_client()
        self._progress = progress

    def _create_llm_client(self) -> BaseLLM:
        """Factory function to create an LLM client."""
        if self.config.agent == "gemini":
            return GeminiLLM()
        elif self.config.agent == "ollama":
            return OllamaLLM()
        elif self.config.agent == "nvidia":
            return NvidiaLLM()
        else:
            raise ValueError(
                f"Unsupported agent specified in config: {self.config.agent}"
            )

    def _get_translation_prompt_template(
        self, source_lang: str, target_lang: str
    ) -> str:
        with open(self.config.translation_prompt_path, "r", encoding="utf-8") as f:
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

        iterator = (
            self._progress.tqdm(enumerate(chunks), desc="Translating Chunks...")
            if self._progress
            else enumerate(chunks)
        )

        for i, chunk in iterator:
            translated_chunk = self._translate_single_chunk(chunk, i, prompt_template)
            translated_chunks.append(translated_chunk)

        return translated_chunks

    def translate_text(self, full_text: str, source_lang: str, target_lang: str) -> str:
        original_chunks = self.llm_client.split_into_limit(full_text)

        logger.info(
            f"  - Original text split into {len(original_chunks)} chunks for translation."
        )

        if not original_chunks:
            logger.warning(
                "  - Warning: The original text resulted in 0 chunks. Check input."
            )
            return ""

        translated_text_parts = self._translate_chunks(
            original_chunks, source_lang, target_lang
        )

        logger.info("Translation of all chunks completed.")
        full_translated_text = "\n\n".join(translated_text_parts)
        full_translated_text = re.sub(r"\n{3,}", "\n\n", full_translated_text).strip()

        return full_translated_text
