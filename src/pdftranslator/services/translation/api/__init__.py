"""API package exports."""

from .schemas import JobBase, JobCreate, JobUpdate, JobResponse, JobListResponse, GlossaryRefSchema, SegmentSummary
from .dependencies import get_translation_service, get_settings, get_database_connection, get_unit_of_work
from .routes import jobs

__all__ = [
    # Schemas
    "JobBase", "JobCreate", "JobUpdate", "JobResponse", "JobListResponse", "GlossaryRefSchema", "SegmentSummary",
    # Dependencies
    "get_translation_service", "get_settings", "get_database_connection", "get_unit_of_work",
    # Routes
    "jobs_router",
]