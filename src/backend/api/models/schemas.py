"""Pydantic schemas for API models."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class FileUploadResponse(BaseModel):
    """Response schema for file upload."""

    id: str
    name: str
    size: int
    type: str
    uploaded_at: datetime
    work_id: int
    volume_id: int


class TaskStateSchema(BaseModel):
    """Task state schema."""

    status: str
    updated_at: datetime
    error: Optional[str] = None
    progress: Optional[int] = None


class TaskStatusResponse(BaseModel):
    """Task status response schema."""

    split_chapters: TaskStateSchema
    glossary: TaskStateSchema
    translated: TaskStateSchema
    audio_generated: TaskStateSchema


class TaskStartRequest(BaseModel):
    """Task start request schema."""

    task_type: str


class TaskStartResponse(BaseModel):
    """Task start response schema."""

    task_id: str
    status: str
    message: str


class ChapterResponse(BaseModel):
    """Chapter response schema."""

    id: int
    volume_id: int
    chapter_number: int
    title: str
    created_at: datetime
    updated_at: datetime


class ChapterUpdateRequest(BaseModel):
    """Chapter update request schema."""

    title: Optional[str] = None


class GlossaryEntryResponse(BaseModel):
    """Glossary entry response schema."""

    id: int
    work_id: int
    volume_id: Optional[int]
    source_term: str
    target_term: str
    context: Optional[str]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime


class GlossaryUpdateRequest(BaseModel):
    """Glossary update request schema."""

    target_term: Optional[str] = None
    context: Optional[str] = None
    notes: Optional[str] = None


class TranslationChunkResponse(BaseModel):
    """Translation chunk response schema."""

    id: int
    chapter_id: int
    original_text: str
    translated_text: str
    order: int


class TranslationChapterResponse(BaseModel):
    """Translation chapter response schema."""

    chapter_id: int
    chapter_title: str
    chunks: list[TranslationChunkResponse]


class TranslationDataResponse(BaseModel):
    """Translation data response schema."""

    file_id: str
    chapters: list[TranslationChapterResponse]


class TranslationUpdateRequest(BaseModel):
    """Translation update request schema."""

    translated_text: str


class AudioFileResponse(BaseModel):
    """Audio file response schema."""

    chapter_id: int
    chapter_title: str
    format: str
    duration: int
    url: str
    size: int


class AudioStatusResponse(BaseModel):
    """Audio status response schema."""

    status: str
    progress: int
    audio_files: Optional[list[AudioFileResponse]] = None
    error: Optional[str] = None
