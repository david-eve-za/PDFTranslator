"""
Pydantic schemas for TranslationJob API.
"""

from __future__ import annotations
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime

from ...domain.models.job import JobStatus, JobPriority


class GlossaryRefSchema(BaseModel):
    glossary_id: int
    name: str
    source_lang: str
    target_lang: str
    priority: int = 0
    entry_count: int = 0


class SegmentSummary(BaseModel):
    id: int
    segment_number: Optional[int] = None
    is_translated: bool = False
    word_count_source: int = 0
    word_count_target: int = 0

    model_config = ConfigDict(from_attributes=True)


class JobBase(BaseModel):
    source_lang: str = Field(..., min_length=2, max_length=2, pattern="^[a-z]{2}$")
    target_lang: str = Field(..., min_length=2, max_length=2, pattern="^[a-z]{2}$")
    work_id: int = Field(..., gt=0)
    volume_id: Optional[int] = Field(None, gt=0)
    priority: JobPriority = JobPriority.NORMAL
    llm_provider: Optional[str] = None
    model_name: Optional[str] = None


class JobCreate(JobBase):
    source_text: Optional[str] = None


class JobUpdate(BaseModel):
    priority: Optional[JobPriority] = None
    llm_provider: Optional[str] = None
    model_name: Optional[str] = None


class JobResponse(JobBase):
    id: int
    uuid: str
    status: JobStatus
    source_text: Optional[str] = None
    target_text: Optional[str] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    glossary_refs: List[GlossaryRefSchema] = []
    segment_count: int = 0
    translated_segment_count: int = 0
    progress: float = 0.0
    word_count_source: int = 0
    word_count_target: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class JobListResponse(BaseModel):
    items: List[JobResponse]
    total: int
    page: int
    page_size: int
    total_pages: int