"""API schemas package exports."""

from .work import WorkBase, WorkCreate, WorkUpdate, WorkResponse, WorkListResponse, VolumeSummary
from .volume import VolumeBase, VolumeCreate, VolumeUpdate, VolumeResponse, VolumeListResponse, ChapterSummary
from .chapter import ChapterBase, ChapterCreate, ChapterUpdate, ChapterResponse, ChapterListResponse

__all__ = [
    # Work
    "WorkBase",
    "WorkCreate",
    "WorkUpdate",
    "WorkResponse",
    "WorkListResponse",
    "VolumeSummary",
    # Volume
    "VolumeBase",
    "VolumeCreate",
    "VolumeUpdate",
    "VolumeResponse",
    "VolumeListResponse",
    "ChapterSummary",
    # Chapter
    "ChapterBase",
    "ChapterCreate",
    "ChapterUpdate",
    "ChapterResponse",
    "ChapterListResponse",
]