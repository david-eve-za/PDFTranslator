"""
Repository Protocols (Interfaces) for Catalog Domain.

CUPID Principle: Composable
- Dependencies inverted via protocols
- Implementations can be swapped (SQLite, PostgreSQL, In-Memory for tests)
- No concrete dependencies in domain layer
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Optional, List, Protocol
from dataclasses import dataclass

from ..models.work import Work
from ..models.volume import Volume
from ..models.chapter import Chapter


@dataclass(frozen=True)
class PaginationParams:
    """Pagination parameters for list queries."""
    page: int = 1
    page_size: int = 20

    def __post_init__(self) -> None:
        if self.page < 1:
            raise ValueError("Page must be >= 1")
        if self.page_size < 1 or self.page_size > 100:
            raise ValueError("Page size must be between 1 and 100")

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size


@dataclass(frozen=True)
class PaginatedResult:
    """Generic paginated result."""
    items: List
    total: int
    page: int
    page_size: int

    @property
    def total_pages(self) -> int:
        if self.page_size == 0:
            return 0
        return (self.total + self.page_size - 1) // self.page_size


class WorkRepository(Protocol):
    """Protocol for Work persistence operations."""

    async def get_by_id(self, work_id: int) -> Optional[Work]:
        """Get work by ID."""
        ...

    async def get_by_uuid(self, uuid: str) -> Optional[Work]:
        """Get work by UUID."""
        ...

    async def get_all(self, pagination: PaginationParams) -> PaginatedResult[Work]:
        """Get all works with pagination."""
        ...

    async def create(self, work: Work) -> Work:
        """Create new work, returns work with assigned ID."""
        ...

    async def update(self, work: Work) -> Work:
        """Update existing work."""
        ...

    async def delete(self, work_id: int) -> bool:
        """Delete work by ID."""
        ...

    async def find_by_title(self, title: str, fuzzy: bool = False) -> List[Work]:
        """Find works by title."""
        ...


class VolumeRepository(Protocol):
    """Protocol for Volume persistence operations."""

    async def get_by_id(self, volume_id: int) -> Optional[Volume]:
        ...

    async def get_by_work_id(self, work_id: int) -> List[Volume]:
        ...

    async def get_by_work_and_number(self, work_id: int, volume_number: int) -> Optional[Volume]:
        ...

    async def create(self, volume: Volume) -> Volume:
        ...

    async def update(self, volume: Volume) -> Volume:
        ...

    async def delete(self, volume_id: int) -> bool:
        ...


class ChapterRepository(Protocol):
    """Protocol for Chapter persistence operations."""

    async def get_by_id(self, chapter_id: int) -> Optional[Chapter]:
        ...

    async def get_by_volume_id(self, volume_id: int) -> List[Chapter]:
        ...

    async def get_by_volume_and_number(self, volume_id: int, chapter_number: int) -> Optional[Chapter]:
        ...

    async def create(self, chapter: Chapter) -> Chapter:
        ...

    async def update(self, chapter: Chapter) -> Chapter:
        ...

    async def delete(self, chapter_id: int) -> bool:
        ...


class CatalogUnitOfWork(Protocol):
    """
    Unit of Work pattern for transactional consistency.

    CUPID Principle: Predictable
    - Explicit transaction boundaries
    - Atomic operations across repositories
    """

    @property
    def works(self) -> WorkRepository:
        ...

    @property
    def volumes(self) -> VolumeRepository:
        ...

    @property
    def chapters(self) -> ChapterRepository:
        ...

    async def commit(self) -> None:
        """Commit the transaction."""
        ...

    async def rollback(self) -> None:
        """Rollback the transaction."""
        ...

    async def __aenter__(self) -> CatalogUnitOfWork:
        ...

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        ...