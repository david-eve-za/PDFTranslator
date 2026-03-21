from dataclasses import dataclass, field
from typing import Optional, List, Dict
import numpy as np


@dataclass
class Work:
    id: Optional[int]
    title: str
    title_translated: Optional[str]
    source_lang: str = "en"
    target_lang: str = "es"
    author: Optional[str] = None


@dataclass
class Volume:
    id: Optional[int]
    work_id: int
    volume_number: int
    title: Optional[str]
    full_text: Optional[str] = None
    translated_text: Optional[str] = None
    embedding: Optional[np.ndarray] = None


@dataclass
class Chapter:
    id: Optional[int]
    volume_id: int
    chapter_number: Optional[int]
    title: Optional[str]
    original_text: Optional[str] = None
    translated_text: Optional[str] = None
    embedding: Optional[np.ndarray] = None


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
class GlossaryEntry:
    id: Optional[int]
    work_id: int
    term: str
    translation: Optional[str]
    is_proper_noun: bool = False
    notes: Optional[str] = None
    contexts: List[TermContext] = field(default_factory=list)
    embedding: Optional[np.ndarray] = None
    entity_type: str = "other"
    do_not_translate: bool = False
    is_verified: bool = False
    confidence: float = 0.0
    source_language: str = "en"
    target_language: str = "es"


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
