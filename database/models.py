from dataclasses import dataclass, field
from typing import Optional, List
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
    chapter_number: int
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
