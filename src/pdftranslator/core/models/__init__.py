"""Core models — re-exported from domain for backward compatibility.

DEPRECATED: Import from pdftranslator.domain.models instead.
"""
from pdftranslator.domain.models.glossary import (  # noqa: F401
    ContextExample,
    GlossaryEntry,
    TermContext,
)
from pdftranslator.domain.models.work import Chapter, Volume, Work  # noqa: F401

__all__ = ["Work", "Volume", "Chapter", "GlossaryEntry", "TermContext", "ContextExample"]
