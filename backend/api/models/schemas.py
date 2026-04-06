from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class FileUploadResponse(BaseModel):
    id: str
    name: str
    size: int
    type: str
    uploaded_at: datetime
    work_id: int
    volume_id: int


class TaskStateSchema(BaseModel):
    status: str
    updated_at: datetime
    error: Optional[str] = None
    progress: Optional[int] = None


class TaskStatusResponse(BaseModel):
    split_chapters: TaskStateSchema
    glossary: TaskStateSchema
    translated: TaskStateSchema
    audio_generated: TaskStateSchema


class TaskStartRequest(BaseModel):
    task_type: str


class TaskStartResponse(BaseModel):
    task_id: str
    status: str
    message: str


class ChapterResponse(BaseModel):
    id: int
    volume_id: int
    chapter_number: int
    title: str
    created_at: datetime
    updated_at: datetime


class ChapterUpdateRequest(BaseModel):
    title: Optional[str] = None


class GlossaryEntryResponse(BaseModel):
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
    target_term: Optional[str] = None
    context: Optional[str] = None
    notes: Optional[str] = None


class TranslationChunkResponse(BaseModel):
    id: int
    chapter_id: int
    original_text: str
    translated_text: str
    order: int


class TranslationChapterResponse(BaseModel):
    chapter_id: int
    chapter_title: str
    chunks: list[TranslationChunkResponse]


class TranslationDataResponse(BaseModel):
    file_id: str
    chapters: list[TranslationChapterResponse]


class TranslationUpdateRequest(BaseModel):
    translated_text: str


class AudioFileResponse(BaseModel):
    chapter_id: int
    chapter_title: str
    format: str
    duration: int
    url: str
    size: int


class AudioStatusResponse(BaseModel):
    status: str
    progress: int
    audio_files: Optional[list[AudioFileResponse]] = None
    error: Optional[str] = None
