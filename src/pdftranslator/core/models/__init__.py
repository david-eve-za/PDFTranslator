"""Core models — re-exported from domain for backward compatibility.

DEPRECATED: Import from pdftranslator.domain.models instead.
"""
from pdftranslator.domain.models.work import Work, Volume, Chapter  # noqa: F401
from pdftranslator.domain.models.glossary import GlossaryEntry, TermContext, ContextExample  # noqa: F401

__all__ = ["Work", "Volume", "Chapter", "GlossaryEntry", "TermContext", "ContextExample"]
