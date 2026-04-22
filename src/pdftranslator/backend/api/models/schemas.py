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
    """Query parameters for file upload (deprecated - languages configured in Work)."""

    source_lang: str | None = Field(
        default=None, description="Source language code (ignored)"
    )
    target_lang: str | None = Field(
        default=None, description="Target language code (ignored)"
    )


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
    translation: str | None = None
    entity_type: str = "other"
    context: str | None = None
    is_proper_noun: bool = False
    frequency: int = 0
    source_lang: str = "en"
    target_lang: str = "es"
    created_at: datetime
    updated_at: datetime | None = None


class GlossaryUpdateRequest(BaseModel):
    """Glossary update request schema."""

    term: str | None = None
    translation: str | None = None
    context: str | None = None
    is_proper_noun: bool | None = None
    do_not_translate: bool | None = None
    is_verified: bool | None = None


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
    total_volumes: int = 0
    total_chapters: int = 0
    translated_chapters: int = 0
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
    full_text: str | None = None
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
    entity_type: str = "other"
    context: str | None = None
    is_proper_noun: bool = False
    source_lang: str = "en"
    target_lang: str = "es"


class GlossaryUpdateRequestNew(BaseModel):
    """Glossary update request schema (new)."""

    term: str | None = None
    translation: str | None = None
    context: str | None = None
    is_proper_noun: bool | None = None


class SplitPreviewRequest(BaseModel):
    """Request schema for split preview."""

    text: str


class SplitPreviewResponse(BaseModel):
    """Response schema for split preview."""

    blocks: list[dict]
    has_errors: bool = False
    error_message: str | None = None


class SplitProcessRequest(BaseModel):
    """Request schema for split processing."""

    volume_id: int
    text: str


class SplitProcessResponse(BaseModel):
    """Response schema for split processing."""

    success: bool
    chapters_created: int = 0
    blocks: list[dict] = []
    error_message: str | None = None


class SubstitutionRuleResponse(BaseModel):
    """Substitution rule response schema."""

    id: int
    name: str
    pattern: str
    replacement: str
    description: str | None = None
    is_active: bool = True
    apply_on_extract: bool = True
    created_at: str
    updated_at: str | None = None


class SubstitutionRuleCreate(BaseModel):
    """Substitution rule create request schema."""

    name: str
    pattern: str
    replacement: str
    description: str | None = None
    is_active: bool = True
    apply_on_extract: bool = True


class SubstitutionRuleUpdate(BaseModel):
    """Substitution rule update request schema."""

    name: str | None = None
    pattern: str | None = None
    replacement: str | None = None
    description: str | None = None
    is_active: bool | None = None
    apply_on_extract: bool | None = None


class SettingsResponse(BaseModel):
    """Settings response schema (secrets masked)."""

    llm: dict
    database: dict
    document: dict
    nlp: dict
    paths: dict


class SettingsUpdateRequest(BaseModel):
    """Settings update request schema."""

    llm: dict | None = None
    database: dict | None = None
    document: dict | None = None
    nlp: dict | None = None
    paths: dict | None = None


class ApplyRulesRequest(BaseModel):
    """Request to apply rules to a volume."""

    rule_ids: list[int] | None = None


class GlossaryBuildRequest(BaseModel):
    """Request schema for building glossary."""

    work_id: int
    source_lang: str = "en"
    target_lang: str = "es"


class GlossaryBuildVolumeResult(BaseModel):
    """Result for a single volume in glossary build."""

    volume_id: int
    volume_number: int
    extracted: int = 0
    new: int = 0
    skipped: int = 0
    entities_by_type: dict = {}
    was_resumed: bool = False
    resume_phase: str | None = None
    progress_stats: dict[str, int] | None = None


class GlossaryBuildResponse(BaseModel):
    """Response schema for glossary build."""

    total_extracted: int = 0
    total_new: int = 0
    total_skipped: int = 0
    volumes_processed: int = 0
    volumes_skipped: int = 0
    entities_by_type: dict = {}
    volume_results: list[GlossaryBuildVolumeResult] = []
