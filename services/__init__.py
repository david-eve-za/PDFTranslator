"""Business logic services."""

from services.translator import TranslatorService, TranslationResult
from services.glossary_translator import GlossaryAwareTranslator

__all__ = ["TranslatorService", "TranslationResult", "GlossaryAwareTranslator"]
