"""Domain models for works, volumes, and chapters.

Maps directly from SQL schema:
- works -> Work
- volumes -> Volume
- chapters -> Chapter
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class Work:
    id: int | None = None
    title: str = ""
    title_translated: str | None = None
    source_lang: str | None = None
    target_lang: str | None = None
    author: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass
class Volume:
    id: int | None = None
    work_id: int | None = None
    volume_number: int = 0
    title: str | None = None
    full_text: str | None = None
    translated_text: str | None = None
    embedding: list[float] | None = None
    glossary_built_at: datetime | None = None
    created_at: datetime | None = None
    glossary_build_status: str = "pending"
    glossary_error_message: str | None = None
    glossary_resume_phase: str | None = None


@dataclass
class Chapter:
    id: int | None = None
    volume_id: int | None = None
    chapter_number: int | None = None
    title: str | None = None
    start_position: int | None = None
    end_position: int | None = None
    original_text: str | None = None
    translated_text: str | None = None
    embedding: list[float] | None = None
    created_at: datetime | None = None
