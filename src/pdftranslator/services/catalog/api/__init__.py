"""API package exports."""

from .schemas import (
    WorkBase, WorkCreate, WorkUpdate, WorkResponse, WorkListResponse, VolumeSummary,
    VolumeBase, VolumeCreate, VolumeUpdate, VolumeResponse, VolumeListResponse, ChapterSummary,
    ChapterBase, ChapterCreate, ChapterUpdate, ChapterResponse, ChapterListResponse,
)
from .dependencies import get_catalog_service, get_settings, get_database_connection, get_unit_of_work
from .routes import works_router, volumes_router, chapters_router

__all__ = [
    # Schemas
    "WorkBase", "WorkCreate", "WorkUpdate", "WorkResponse", "WorkListResponse", "VolumeSummary",
    "VolumeBase", "VolumeCreate", "VolumeUpdate", "VolumeResponse", "VolumeListResponse", "ChapterSummary",
    "ChapterBase", "ChapterCreate", "ChapterUpdate", "ChapterResponse", "ChapterListResponse",
    # Dependencies
    "get_catalog_service", "get_settings", "get_database_connection", "get_unit_of_work",
    # Routes
    "works_router", "volumes_router", "chapters_router",
]