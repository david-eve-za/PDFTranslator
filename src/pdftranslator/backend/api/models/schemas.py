"""Pydantic schemas for API models."""

from datetime import datetime

from pydantic import BaseModel, Field


class FileUploadResponse(BaseModel):
    """Response schema for file upload."""

    id: int
    filename: str
    original_name: str
    file_size: int
    file_type: str
    work_id: int | None = None
    work_title: str | None = None
    volume_id: int | None = None
    volume_number: int | None = None
    status: str
    created_at: datetime


class FileListResponse(BaseModel):
    """Paginated list of files."""

    items: list[FileUploadResponse]
    total: int
    page: int
    page_size: int

    @property
    def pages(self) -> int:
        return (
            (self.total + self.page_size - 1) // self.page_size
            if self.page_size > 0
            else 0
        )


class FileUploadQuery(BaseModel):
    """Query parameters for file upload."""

    source_lang: str = Field(default="en", description="Source language code")
    target_lang: str = Field(default="es", description="Target language code")


class TaskStateSchema(BaseModel):
    """Task state schema."""

    status: str
    updated_at: datetime
    error: str | None = None
    progress: int | None = None


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
    chapter_number: int | None = None
    title: str | None = None
    original_text: str | None = None
    translated_text: str | None = None
    is_translated: bool = False
    created_at: str
    updated_at: str


class ChapterUpdateRequest(BaseModel):
    """Chapter update request schema."""

    title: str | None = None


class GlossaryEntryResponse(BaseModel):
    """Glossary entry response schema."""

    id: int
    work_id: int
    term: str
    translation: str | None
    notes: str | None
    is_proper_noun: bool
    created_at: datetime


class GlossaryUpdateRequest(BaseModel):
    """Glossary update request schema."""

    translation: str | None = None
    notes: str | None = None


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
    audio_files: list[AudioFileResponse] | None = None
    error: str | None = None


class WorkResponse(BaseModel):
    """Work response schema."""

    id: int
    title: str
    title_translated: str | None = None
    author: str
    source_lang: str = "en"
    target_lang: str = "es"
    volumes: list[dict] = []
    created_at: str
    updated_at: str


class WorkListResponse(BaseModel):
    """Paginated list of works."""

    items: list[WorkResponse]
    total: int
    page: int
    page_size: int

    @property
    def pages(self) -> int:
        return (
            (self.total + self.page_size - 1) // self.page_size
            if self.page_size > 0
            else 0
        )


class WorkCreate(BaseModel):
    """Work create request schema."""

    title: str
    author: str
    title_translated: str | None = None
    source_lang: str = "en"
    target_lang: str = "es"


class WorkUpdate(BaseModel):
    """Work update request schema."""

    title: str | None = None
    title_translated: str | None = None
    author: str | None = None
    source_lang: str | None = None
    target_lang: str | None = None


class VolumeResponse(BaseModel):
    """Volume response schema."""

    id: int
    work_id: int
    volume_number: int
    title: str | None = None
    chapters: list[dict] = []
    created_at: str


class VolumeListResponse(BaseModel):
    """Paginated list of volumes."""

    items: list[VolumeResponse]
    total: int


class VolumeCreate(BaseModel):
    """Volume create request schema."""

    work_id: int
    volume_number: int
    title: str | None = None


class ChapterListResponse(BaseModel):
    """Paginated list of chapters."""

    items: list[ChapterResponse]
    total: int


class ChapterUpdate(BaseModel):
    """Chapter update request schema."""

    title: str | None = None
    translated_text: str | None = None


class GlossaryCreate(BaseModel):
    """Glossary create request schema."""

    work_id: int
    term: str
    translation: str | None = None
    notes: str | None = None
    is_proper_noun: bool = False


class GlossaryUpdateRequestNew(BaseModel):
    """Glossary update request schema (new)."""

    translation: str | None = None
    notes: str | None = None
    is_proper_noun: bool | None = None
