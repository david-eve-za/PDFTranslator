"""
DEPRECATED: Use models.work instead.
This module is kept for backward compatibility.

The following classes are now in models.work:
- Work
- Volume
- Chapter
- GlossaryEntry

Other classes remain here until migrated.
"""

# Backward compatibility imports
from src.core.models.work import Work, Volume, Chapter, GlossaryEntry

# Classes that remain in this module (not yet migrated)
from dataclasses import dataclass, field
from typing import Optional, List, Dict
import numpy as np


@dataclass
class ContextExample:
    id: Optional[int]
    context_id: int
    original_sentence: str
    translated_sentence: str
    chapter_id: Optional[int] = None


@dataclass
class TermContext:
    id: Optional[int]
    term_id: int
    context_hint: str
    translation: str
    example_usage: Optional[str] = None
    examples: List[ContextExample] = field(default_factory=list)


@dataclass
class EntityBlacklist:
    id: Optional[int]
    term: str
    reason: Optional[str] = None


@dataclass
class FantasyTerm:
    id: Optional[int]
    term: str
    entity_type: str
    do_not_translate: bool = False
    context_hint: Optional[str] = None


@dataclass
class EntityCandidate:
    text: str
    entity_type: str
    frequency: int = 1
    contexts: List[str] = field(default_factory=list)
    confidence: float = 0.0
    source_language: str = "en"

    def add_context(self, context: str):
        if context not in self.contexts:
            self.contexts.append(context[:300])

    def best_context(self) -> str:
        return self.contexts[0] if self.contexts else ""

    def to_embed_text(self) -> str:
        return f"{self.text} {self.entity_type} {self.best_context()}"


@dataclass
class BuildResult:
    extracted: int
    new: int
    skipped: int
    entities_by_type: Dict[str, int] = field(default_factory=dict)


__all__ = [
    # From models.work (backward compatibility)
    "Work",
    "Volume",
    "Chapter",
    "GlossaryEntry",
    # From this module
    "ContextExample",
    "TermContext",
    "EntityBlacklist",
    "FantasyTerm",
    "EntityCandidate",
    "BuildResult",
]
