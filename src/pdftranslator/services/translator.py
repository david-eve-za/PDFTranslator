"""Translator service — re-exported from application for backward compatibility.

DEPRECATED: Import from pdftranslator.application.services.translation_service instead.
"""
from pdftranslator.application.services.translation_service import (  # noqa: F401
    TranslationResult,
    TranslationService,
)

TranslatorService = TranslationService

__all__ = ["TranslationService", "TranslatorService", "TranslationResult"]
