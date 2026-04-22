"""Database models — re-exported from domain for backward compatibility.

DEPRECATED: Import from pdftranslator.domain.models instead.
"""
from pdftranslator.domain.models.work import Work, Volume, Chapter  # noqa: F401
from pdftranslator.domain.models.glossary import GlossaryEntry, TermContext, ContextExample  # noqa: F401
from pdftranslator.domain.models.entity import (  # noqa: F401
    EntityCandidate,
    BuildResult,
    GlossaryBuildProgress,
    EntityBlacklist,
    FantasyTerm,
)
from pdftranslator.domain.models.file import UploadedFile  # noqa: F401
from pdftranslator.domain.models.substitution import SubstitutionRule  # noqa: F401

__all__ = [
    "Work", "Volume", "Chapter",
    "GlossaryEntry", "TermContext", "ContextExample",
    "EntityCandidate", "BuildResult", "GlossaryBuildProgress",
    "EntityBlacklist", "FantasyTerm",
    "UploadedFile",
    "SubstitutionRule",
]
