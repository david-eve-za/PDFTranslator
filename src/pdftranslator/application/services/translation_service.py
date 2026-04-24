"""Application-layer TranslationService.

Resolves DIP-1: Accepts LLMClient (domain protocol) via constructor
instead of LLMFactory (infrastructure). Use this instead of
services.translator.TranslatorService which violates DIP.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

from pdftranslator.core.config.llm import BCP47Language
from pdftranslator.core.config.settings import Settings
from pdftranslator.domain.protocols.llm import LLMClient, TextGenerator, TextSplitter

logger = logging.getLogger(__name__)


@dataclass
class TranslationResult:
    """Result of a translation operation."""

    original_chunks: int
    translated_chunks: int
    text: str
    errors: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return len(self.errors) == 0


class TranslationService:
    """Service for translating text using LLM backends.

    Accepts an LLMClient via constructor injection (DIP compliant).
    """

    _ERROR_CHUNK_MARKER = "[TRANSLATION_ERROR_CHUNK_{index}]"

    def __init__(
        self,
        llm_client: TextGenerator | TextSplitter | LLMClient,
        settings: Settings | None = None,
    ):
        self._llm_client = llm_client
        self._settings = settings or Settings.get()
        self._progress = None

    @property
    def llm_client(self):
        return self._llm_client

    def set_progress(self, progress) -> None:
        self._progress = progress

    def translate(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        language: BCP47Language = BCP47Language.ENGLISH,
    ) -> TranslationResult:
        chunks = self._split_text(text, language)

        logger.info(f"Text split into {len(chunks)} chunks for translation")

        if not chunks:
            logger.warning("No chunks to translate")
            return TranslationResult(
                original_chunks=0,
                translated_chunks=0,
                text="",
                errors=["No text to translate"],
            )

        prompt_template = self._load_prompt_template()

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

        full_text = "\n\n".join(translated_parts)
        full_text = re.sub(r"\n{3,}", "\n\n", full_text).strip()

        return TranslationResult(
            original_chunks=len(chunks),
            translated_chunks=len(translated_parts),
            text=full_text,
            errors=errors,
        )

    def _split_text(self, text: str, language: BCP47Language) -> list[str]:
        if isinstance(self._llm_client, TextSplitter):
            return self._llm_client.split_into_limit(text, language)
        return [text]

    def _load_prompt_template(self) -> str:
        prompt_path = self._settings.paths.translation_prompt_path
        with open(prompt_path, encoding="utf-8") as f:
            return f.read()

    def _translate_chunk(
        self,
        chunk: str,
        index: int,
        template: str,
        source_lang: str,
        target_lang: str,
    ) -> str:
        prompt = template.format(
            text_chunk=chunk,
            source_lang=source_lang,
            target_lang=target_lang,
        )

        if hasattr(self._llm_client, "count_tokens"):
            logger.debug(
                f"Chunk {index + 1}: Prompt tokens = {self._llm_client.count_tokens(prompt)}"
            )

        return self._llm_client.call_model(prompt)

    def _get_iterator(self, chunks: list[str]):
        if self._progress:
            return self._progress(enumerate(chunks), desc="Translating Chunks...")
        return enumerate(chunks)
