"""Domain models — source of truth for all entities."""
from pdftranslator.domain.models.work import Work, Volume, Chapter
from pdftranslator.domain.models.glossary import GlossaryEntry, TermContext, ContextExample
from pdftranslator.domain.models.entity import (
    EntityCandidate,
    BuildResult,
    GlossaryBuildProgress,
    EntityBlacklist,
    FantasyTerm,
)
from pdftranslator.domain.models.file import UploadedFile
from pdftranslator.domain.models.substitution import SubstitutionRule

__all__ = [
    "Work", "Volume", "Chapter",
    "GlossaryEntry", "TermContext", "ContextExample",
    "EntityCandidate", "BuildResult", "GlossaryBuildProgress",
    "EntityBlacklist", "FantasyTerm",
    "UploadedFile",
    "SubstitutionRule",
]
