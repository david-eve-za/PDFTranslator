"""Domain models for glossary entries, contexts, and examples.

Maps directly from SQL schema:
- glossary_terms -> GlossaryEntry
- term_contexts -> TermContext
- context_examples -> ContextExample

Resolves DUP-2 and DUP-3: unified glossary models in domain layer.
Includes all SQL columns (MOD-1 fix).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class GlossaryEntry:
    id: int | None = None
    work_id: int | None = None
    term: str = ""
    translation: str | None = None
    notes: str | None = None
    is_proper_noun: bool = False
    entity_type: str = "other"
    do_not_translate: bool = False
    is_verified: bool = False
    confidence: float = 0.0
    context: str | None = None
    frequency: int = 0
    source_lang: str = "en"
    target_lang: str = "es"
    embedding: list[float] | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass
class TermContext:
    id: int | None = None
    term_id: int | None = None
    context_hint: str = ""
    translation: str = ""
    example_usage: str | None = None
    examples: list[ContextExample] = field(default_factory=list)
    created_at: datetime | None = None


@dataclass
class ContextExample:
    id: int | None = None
    context_id: int | None = None
    original_sentence: str = ""
    translated_sentence: str = ""
    chapter_id: int | None = None
    created_at: datetime | None = None
