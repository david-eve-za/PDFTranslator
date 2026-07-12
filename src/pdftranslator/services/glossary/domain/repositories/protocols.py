"""
Repository Protocols for Glossary Service.

CUPID Principle: Composable
- Protocols define contracts, implementations vary
- Dependency injection via protocols enables testing
- Database-agnostic domain layer
"""

from __future__ import annotations
from typing import Protocol, List, Optional, AsyncIterator
from dataclasses import dataclass

from ...domain.models.glossary import Glossary, GlossaryEntry
from ...domain.models.build_pipeline import BuildPipeline, PipelineStage
from ...domain.models.entity import EntityCandidate, EntityType


@dataclass(frozen=True)
class PaginationParams:
    """Pagination parameters."""
    page: int = 1
    page_size: int = 20

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size


@dataclass(frozen=True)
class PaginatedResult:
    """Paginated query result."""
    items: List
    total: int
    page: int
    page_size: int

    @property
    def total_pages(self) -> int:
        return (self.total + self.page_size - 1) // self.page_size


class GlossaryRepository(Protocol):
    """Repository for Glossary aggregates."""

    async def get_by_id(self, glossary_id: int) -> Optional[Glossary]:
        """Get glossary by database ID."""
        ...

    async def get_by_uuid(self, uuid: str) -> Optional[Glossary]:
        """Get glossary by UUID."""
        ...

    async def get_by_work(self, work_id: int) -> Optional[Glossary]:
        """Get glossary for a work."""
        ...

    async def create(self, glossary: Glossary) -> Glossary:
        """Create new glossary."""
        ...

    async def update(self, glossary: Glossary) -> Glossary:
        """Update existing glossary."""
        ...

    async def delete(self, glossary_id: int) -> bool:
        """Delete glossary."""
        ...

    async def list(
        self,
        pagination: PaginationParams,
        work_id: Optional[int] = None,
        status: Optional[str] = None,
    ) -> PaginatedResult[Glossary]:
        """List glossaries with pagination and filters."""
        ...


class GlossaryEntryRepository(Protocol):
    """Repository for individual GlossaryEntry records."""

    async def get_by_id(self, entry_id: int) -> Optional[GlossaryEntry]:
        """Get entry by ID."""
        ...

    async def get_by_term(self, work_id: int, term: str) -> Optional[GlossaryEntry]:
        """Get entry by term."""
        ...

    async def get_by_uuid(self, uuid: str) -> Optional[GlossaryEntry]:
        """Get entry by UUID."""
        ...

    async def create(self, entry: GlossaryEntry) -> GlossaryEntry:
        """Create new entry."""
        ...

    async def update(self, entry: GlossaryEntry) -> GlossaryEntry:
        """Update existing entry."""
        ...

    async def delete(self, entry_id: int) -> bool:
        """Delete entry."""
        ...

    async def batch_create(self, entries: List[GlossaryEntry]) -> List[GlossaryEntry]:
        """Create multiple entries efficiently."""
        ...

    async def batch_update(self, entries: List[GlossaryEntry]) -> List[GlossaryEntry]:
        """Update multiple entries."""
        ...

    async def list_by_work(
        self,
        work_id: int,
        pagination: PaginationParams,
        entity_type: Optional[EntityType] = None,
        verified_only: bool = False,
    ) -> PaginatedResult[GlossaryEntry]:
        """List entries for a work."""
        ...

    async def search(
        self,
        work_id: int,
        query: str,
        pagination: PaginationParams,
    ) -> PaginatedResult[GlossaryEntry]:
        """Search entries by term (fuzzy)."""
        ...

    async def get_existing_terms(self, work_id: int) -> set[str]:
        """Get set of existing terms (lowercase) for deduplication."""
        ...


class BuildPipelineRepository(Protocol):
    """Repository for BuildPipeline aggregates."""

    async def get_by_id(self, pipeline_id: str) -> Optional[BuildPipeline]:
        """Get pipeline by ID."""
        ...

    async def get_by_work_volume(self, work_id: int, volume_id: int) -> Optional[BuildPipeline]:
        """Get pipeline for work/volume."""
        ...

    async def create(self, pipeline: BuildPipeline) -> BuildPipeline:
        """Create new pipeline."""
        ...

    async def update(self, pipeline: BuildPipeline) -> BuildPipeline:
        """Update existing pipeline."""
        ...

    async def delete(self, pipeline_id: str) -> bool:
        """Delete pipeline."""
        ...

    async def list(
        self,
        pagination: PaginationParams,
        work_id: Optional[int] = None,
        status: Optional[str] = None,
    ) -> PaginatedResult[BuildPipeline]:
        """List pipelines."""
        ...


class EntityExtractorRepository(Protocol):
    """Repository for entity extraction operations."""

    async def extract(
        self,
        text: str,
        source_lang: str,
        min_frequency: int = 2,
    ) -> List[EntityCandidate]:
        """Extract entities from text."""
        ...


# Unit of Work Protocol
class GlossaryUnitOfWork(Protocol):
    """Unit of Work for glossary operations."""

    glossaries: GlossaryRepository
    glossary_entries: GlossaryEntryRepository
    pipelines: BuildPipelineRepository
    entity_extractor: EntityExtractorRepository

    async def __aenter__(self) -> "GlossaryUnitOfWork":
        ...

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        ...

    async def commit(self) -> None:
        """Commit transaction."""
        ...

    async def rollback(self) -> None:
        """Rollback transaction."""
        ...