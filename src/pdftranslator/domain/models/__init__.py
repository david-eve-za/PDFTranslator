"""Domain models — source of truth for all entities."""
from pdftranslator.domain.models.entity import (
    BuildResult,
    EntityBlacklist,
    EntityCandidate,
    FantasyTerm,
    GlossaryBuildProgress,
)
from pdftranslator.domain.models.file import UploadedFile
from pdftranslator.domain.models.glossary import (
    ContextExample,
    GlossaryEntry,
    TermContext,
)
from pdftranslator.domain.models.substitution import SubstitutionRule
from pdftranslator.domain.models.work import Chapter, Volume, Work

__all__ = [
    "Work", "Volume", "Chapter",
    "GlossaryEntry", "TermContext", "ContextExample",
    "EntityCandidate", "BuildResult", "GlossaryBuildProgress",
    "EntityBlacklist", "FantasyTerm",
    "UploadedFile",
    "SubstitutionRule",
]
