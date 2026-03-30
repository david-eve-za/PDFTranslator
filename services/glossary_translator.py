"""Glossary-aware translator service."""

import logging
from typing import List

from config.llm import BCP47Language
from database.models import GlossaryEntry
from services.translator import TranslatorService, TranslationResult
from cli.services.glossary_post_processor import GlossaryPostProcessor

logger = logging.getLogger(__name__)


class GlossaryAwareTranslator:
    """
    Translator with glossary consistency through post-processing.

    Instead of injecting glossary terms into the translation prompt,
    this translator applies glossary validation and correction after
    translation, ensuring 100% consistency of terms.

    Benefits:
        - Larger chunks (no glossary overhead in prompt)
        - Guaranteed consistency through post-processing
        - Fewer API calls for same text

    Usage:
        translator_service = TranslatorService(llm_factory)
        glossary_translator = GlossaryAwareTranslator(translator_service, entries)
        result = glossary_translator.translate(text, "en", "es", "es")
    """

    def __init__(
        self,
        translator: TranslatorService,
        glossary_entries: List[GlossaryEntry],
    ):
        """
        Initialize with translator and glossary entries.

        Args:
            translator: Base translator service.
            glossary_entries: List of glossary terms for post-processing.
        """
        self._translator = translator
        self._glossary_entries = glossary_entries

    def translate(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        target_lang_code: str,
        language: BCP47Language = BCP47Language.ENGLISH,
    ) -> TranslationResult:
        """
        Translate text with glossary post-processing.

        Args:
            text: Text to translate.
            source_lang: Source language code.
            target_lang: Target language code.
            target_lang_code: Target language code for glossary processing.
            language: Language for text splitting.

        Returns:
            TranslationResult with glossary-consistent translated text.
        """
        # Translate using base translator
        result = self._translator.translate(text, source_lang, target_lang, language)

        # Apply glossary post-processing
        if self._glossary_entries:
            logger.info(
                f"Applying glossary post-processing ({len(self._glossary_entries)} entries)"
            )
            processor = GlossaryPostProcessor(self._glossary_entries, target_lang_code)
            result.text = processor.process(result.text)
            logger.info("Glossary post-processing completed")

        return result

    def set_progress(self, progress) -> None:
        """Set progress tracker."""
        self._translator.set_progress(progress)
