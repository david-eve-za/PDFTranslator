"""Work models — re-exported from domain for backward compatibility.

DEPRECATED: Import from pdftranslator.domain.models.work instead.
"""
from pdftranslator.domain.models.work import Work, Volume, Chapter  # noqa: F401
from pdftranslator.domain.models.glossary import GlossaryEntry  # noqa: F401

__all__ = ["Work", "Volume", "Chapter", "GlossaryEntry"]
