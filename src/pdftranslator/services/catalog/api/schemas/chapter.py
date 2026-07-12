"""
API Schemas for Chapter endpoints.
"""

from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime


class ChapterBase(BaseModel):
    """Base chapter fields."""
    chapter_number: Optional[int] = Field(None, gt=0)
    title: Optional[str] = Field(None, max_length=500)
    start_position: Optional[int] = Field(None, ge=0)
    end_position: Optional[int] = Field(None, ge=0)
    original_text: Optional[str] = None
    translated_text: Optional[str] = None


class ChapterCreate(ChapterBase):
    """Schema for creating a new chapter."""
    pass


class ChapterUpdate(BaseModel):
    """Schema for updating a chapter."""
    chapter_number: Optional[int] = Field(None, gt=0)
    title: Optional[str] = Field(None, max_length=500)
    start_position: Optional[int] = Field(None, ge=0)
    end_position: Optional[int] = Field(None, ge=0)
    original_text: Optional[str] = None
    translated_text: Optional[str] = None


class ChapterResponse(ChapterBase):
    """Full chapter response."""
    id: int
    uuid: str
    volume_id: int
    is_translated: bool = False
    word_count_original: int = 0
    word_count_translated: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChapterListResponse(BaseModel):
    """Paginated chapter list response."""
    items: List[ChapterResponse]
    total: int
    page: int
    page_size: int
    total_pages: int