"""Business logic services."""

from pdftranslator.services.glossary_translator import GlossaryAwareTranslator
from pdftranslator.services.translator import TranslationResult, TranslatorService

__all__ = ["TranslatorService", "TranslationResult", "GlossaryAwareTranslator"]
