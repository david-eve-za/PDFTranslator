"""
Domain package exports.
"""

from .models.work import Work
from .models.volume import Volume
from .models.chapter import Chapter
from .repositories.protocols import (
    WorkRepository,
    VolumeRepository,
    ChapterRepository,
    CatalogUnitOfWork,
    PaginationParams,
    PaginatedResult,
)
from .repositories.exceptions import (
    DomainError,
    NotFoundError,
    ConcurrencyError,
    ValidationError,
)
from .services.catalog_service import (
    CatalogService,
    CreateWorkCommand,
    UpdateWorkCommand,
)

__all__ = [
    # Models
    "Work",
    "Volume",
    "Chapter",
    # Repository Protocols
    "WorkRepository",
    "VolumeRepository",
    "ChapterRepository",
    "CatalogUnitOfWork",
    "PaginationParams",
    "PaginatedResult",
    # Exceptions
    "DomainError",
    "NotFoundError",
    "ConcurrencyError",
    "ValidationError",
    # Services
    "CatalogService",
    "CreateWorkCommand",
    "UpdateWorkCommand",
]