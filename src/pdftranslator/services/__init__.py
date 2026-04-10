"""Business logic services."""

from pdftranslator.services.translator import TranslatorService, TranslationResult
from pdftranslator.services.glossary_translator import GlossaryAwareTranslator

__all__ = ["TranslatorService", "TranslationResult", "GlossaryAwareTranslator"]
