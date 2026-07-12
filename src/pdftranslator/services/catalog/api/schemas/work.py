"""
API Schemas for Work endpoints.

CUPID Principle: Composable
- Clean separation between domain models and API contracts
- Versionable, documentable via OpenAPI
"""

from __future__ import annotations
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime


class VolumeSummary(BaseModel):
    """Volume summary for work list/detail responses."""
    id: int
    volume_number: int
    title: Optional[str] = None
    total_chapters: int = 0
    translated_chapters: int = 0

    model_config = ConfigDict(from_attributes=True)


class WorkBase(BaseModel):
    """Base work fields."""
    title: str = Field(..., min_length=1, max_length=500, description="Work title")
    author: Optional[str] = Field(None, max_length=200, description="Author name")
    title_translated: Optional[str] = Field(None, max_length=500, description="Translated title")
    source_lang: str = Field(..., min_length=2, max_length=2, pattern="^[a-z]{2}$", description="ISO 639-1 source language")
    target_lang: str = Field(..., min_length=2, max_length=2, pattern="^[a-z]{2}$", description="ISO 639-1 target language")


class WorkCreate(WorkBase):
    """Schema for creating a new work."""
    pass


class WorkUpdate(BaseModel):
    """Schema for updating a work (all fields optional)."""
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    author: Optional[str] = Field(None, max_length=200)
    title_translated: Optional[str] = Field(None, max_length=500)


class WorkResponse(WorkBase):
    """Full work response with volumes."""
    id: int
    uuid: str
    volumes: List[VolumeSummary] = []
    total_volumes: int = 0
    total_chapters: int = 0
    translated_chapters: int = 0
    translation_progress: float = 0.0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WorkListResponse(BaseModel):
    """Paginated work list response."""
    items: List[WorkResponse]
    total: int
    page: int
    page_size: int
    total_pages: int