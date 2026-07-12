"""
API Schemas for Volume endpoints.
"""

from __future__ import annotations
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime


class ChapterSummary(BaseModel):
    """Chapter summary for volume responses."""
    id: int
    chapter_number: Optional[int] = None
    title: Optional[str] = None
    is_translated: bool = False
    word_count_original: int = 0
    word_count_translated: int = 0

    model_config = ConfigDict(from_attributes=True)


class VolumeBase(BaseModel):
    """Base volume fields."""
    volume_number: int = Field(..., gt=0, description="Volume number (1-based)")
    title: Optional[str] = Field(None, max_length=500)
    full_text: Optional[str] = None
    translated_text: Optional[str] = None


class VolumeCreate(VolumeBase):
    """Schema for creating a new volume."""
    pass


class VolumeUpdate(BaseModel):
    """Schema for updating a volume."""
    title: Optional[str] = Field(None, max_length=500)
    full_text: Optional[str] = None
    translated_text: Optional[str] = None


class VolumeResponse(VolumeBase):
    """Full volume response with chapters."""
    id: int
    uuid: str
    work_id: int
    chapters: List[ChapterSummary] = []
    chapter_count: int = 0
    translated_chapters: int = 0
    translation_progress: float = 0.0
    glossary_built_at: Optional[datetime] = None
    glossary_build_status: str = "pending"
    glossary_error_message: Optional[str] = None
    glossary_resume_phase: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VolumeListResponse(BaseModel):
    """Paginated volume list response."""
    items: List[VolumeResponse]
    total: int
    page: int
    page_size: int
    total_pages: int