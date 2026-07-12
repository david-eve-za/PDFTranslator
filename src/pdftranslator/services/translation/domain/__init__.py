"""Domain package exports."""

from .models import TranslationJob, JobStatus, JobPriority, Segment, GlossaryReference
from .services import TranslationService, CreateJobCommand, CreateSegmentsCommand
from .repositories import (
    TranslationJobRepository,
    SegmentRepository,
    TranslationUnitOfWork,
    PaginationParams,
    PaginatedResult,
    DomainError,
    NotFoundError,
)

__all__ = [
    # Models
    "TranslationJob",
    "JobStatus",
    "JobPriority",
    "Segment",
    "GlossaryReference",
    # Services
    "TranslationService",
    "CreateJobCommand",
    "CreateSegmentsCommand",
    # Repositories
    "TranslationJobRepository",
    "SegmentRepository",
    "TranslationUnitOfWork",
    "PaginationParams",
    "PaginatedResult",
    "DomainError",
    "NotFoundError",
]