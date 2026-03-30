"""Translator service with dependency injection."""

import logging
import re
from dataclasses import dataclass, field
from typing import List

from config.llm import BCP47Language
from config.settings import Settings
from infrastructure.llm.factory import LLMFactory
from infrastructure.llm.protocol import LLMClient

logger = logging.getLogger(__name__)


@dataclass
class TranslationResult:
    """Result of a translation operation."""

    original_chunks: int
    translated_chunks: int
    text: str
    errors: List[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        """Check if translation was successful (no errors)."""
        return len(self.errors) == 0


class TranslatorService:
    """
    Service for translating text using LLM backends.

    Follows Single Responsibility Principle: only handles
    translation orchestration and chunk management.

    Usage:
        factory = LLMFactory(settings)
        translator = TranslatorService(factory)
        result = translator.translate(text, "en", "es")
    """

    _ERROR_CHUNK_MARKER = "[TRANSLATION_ERROR_CHUNK_{index}]"

    def __init__(
        self,
        llm_factory: LLMFactory,
        settings: Settings | None = None,
    ):
        """
        Initialize translator with LLM factory.

        Args:
            llm_factory: Factory for creating LLM clients.
            settings: Optional settings (uses Settings.get() if not provided).
        """
        self._llm_factory = llm_factory
        self._settings = settings or Settings.get()
        self._llm_client: LLMClient = llm_factory.create()
        self._progress = None

    def set_progress(self, progress) -> None:
        """Set progress tracker for chunk translation."""
        self._progress = progress

    def translate(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        language: BCP47Language = BCP47Language.ENGLISH,
    ) -> TranslationResult:
        """
        Translate text from source to target language.

        Args:
            text: Text to translate.
            source_lang: Source language code (e.g., "en").
            target_lang: Target language code (e.g., "es").
            language: Language for text splitting (default: English).

        Returns:
            TranslationResult with translated text and metadata.
        """
        # Split text into chunks
        chunks = self._llm_client.split_into_limit(text, language)

        logger.info(f"Text split into {len(chunks)} chunks for translation")

        if not chunks:
            logger.warning("No chunks to translate")
            return TranslationResult(
                original_chunks=0,
                translated_chunks=0,
                text="",
                errors=["No text to translate"],
            )

        # Load prompt template
        prompt_template = self._load_prompt_template()

        # Translate chunks
        translated_parts = []
        errors = []

        iterator = self._get_iterator(chunks)

        for i, chunk in iterator:
            try:
                result = self._translate_chunk(
                    chunk, i, prompt_template, source_lang, target_lang
                )
                translated_parts.append(result)
            except Exception as e:
                logger.error(f"Error translating chunk {i + 1}: {e}")
                errors.append(f"Chunk {i + 1}: {str(e)}")
                translated_parts.append(self._ERROR_CHUNK_MARKER.format(index=i + 1))

        # Combine translated parts
        full_text = "\n\n".join(translated_parts)
        full_text = re.sub(r"\n{3,}", "\n\n", full_text).strip()

        return TranslationResult(
            original_chunks=len(chunks),
            translated_chunks=len(translated_parts),
            text=full_text,
            errors=errors,
        )

    def _load_prompt_template(self) -> str:
        """Load translation prompt template."""
        prompt_path = self._settings.paths.translation_prompt_path
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()

    def _translate_chunk(
        self,
        chunk: str,
        index: int,
        template: str,
        source_lang: str,
        target_lang: str,
    ) -> str:
        """Translate a single chunk."""
        prompt = template.format(
            text_chunk=chunk,
            source_lang=source_lang,
            target_lang=target_lang,
        )

        logger.debug(
            f"Chunk {index + 1}: Prompt tokens = {self._llm_client.count_tokens(prompt)}"
        )

        return self._llm_client.call_model(prompt)

    def _get_iterator(self, chunks: List[str]):
        """Get iterator for chunk processing."""
        if self._progress:
            return self._progress(enumerate(chunks), desc="Translating Chunks...")
        return enumerate(chunks)
