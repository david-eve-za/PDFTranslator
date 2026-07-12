"""
Catalog Domain Service - Business logic for catalog operations.

CUPID Principle: Domain-Focused
- Encapsulates business rules
- Uses repository protocols (Composable)
- No infrastructure concerns
"""

from __future__ import annotations
from typing import Optional, List
from dataclasses import dataclass

from ..models.work import Work
from ..models.volume import Volume
from ..models.chapter import Chapter
from ..repositories.protocols import (
    WorkRepository,
    VolumeRepository,
    ChapterRepository,
    CatalogUnitOfWork,
    PaginationParams,
    PaginatedResult,
)
from ..repositories.exceptions import DomainError, NotFoundError


@dataclass
class CreateWorkCommand:
    """Command to create a new work."""
    title: str
    source_lang: str
    target_lang: str
    author: Optional[str] = None
    title_translated: Optional[str] = None


@dataclass
class UpdateWorkCommand:
    """Command to update work metadata."""
    title: Optional[str] = None
    author: Optional[str] = None
    title_translated: Optional[str] = None


class CatalogService:
    """
    Domain service for Catalog operations.

    Provides high-level business operations using repository abstractions.
    All operations are transactional via Unit of Work.
    """

    def __init__(self, uow: CatalogUnitOfWork):
        self._uow = uow

    # =================== WORK OPERATIONS ===================

    async def create_work(self, command: CreateWorkCommand) -> Work:
        """Create a new work with validation."""
        work = Work(
            title=command.title,
            source_lang=command.source_lang,
            target_lang=command.target_lang,
            author=command.author,
            title_translated=command.title_translated,
        )

        async with self._uow:
            created_work = await self._uow.works.create(work)
            await self._uow.commit()
            return created_work

    async def get_work(self, work_id: int) -> Work:
        """Get work by ID with full aggregate (volumes + chapters)."""
        work = await self._uow.works.get_by_id(work_id)
        if not work:
            raise NotFoundError(f"Work {work_id} not found")

        # Load volumes and chapters
        volumes = await self._uow.volumes.get_by_work_id(work_id)
        for volume in volumes:
            chapters = await self._uow.chapters.get_by_volume_id(volume.id)
            volume._chapters = chapters  # Internal access for aggregate
            work._volumes.append(volume)

        return work

    async def get_work_by_uuid(self, uuid: str) -> Work:
        """Get work by UUID."""
        work = await self._uow.works.get_by_uuid(uuid)
        if not work:
            raise NotFoundError(f"Work with UUID {uuid} not found")
        return work

    async def list_works(self, pagination: PaginationParams) -> PaginatedResult[Work]:
        """List works with pagination."""
        return await self._uow.works.get_all(pagination)

    async def update_work(self, work_id: int, command: UpdateWorkCommand) -> Work:
        """Update work metadata."""
        async with self._uow:
            work = await self._uow.works.get_by_id(work_id)
            if not work:
                raise NotFoundError(f"Work {work_id} not found")

            work.update_metadata(
                title=command.title,
                author=command.author,
                title_translated=command.title_translated,
            )

            updated = await self._uow.works.update(work)
            await self._uow.commit()
            return updated

    async def delete_work(self, work_id: int) -> bool:
        """Delete work and all its volumes/chapters (cascade)."""
        async with self._uow:
            work = await self._uow.works.get_by_id(work_id)
            if not work:
                raise NotFoundError(f"Work {work_id} not found")

            # Delete volumes (cascades to chapters via DB foreign key)
            volumes = await self._uow.volumes.get_by_work_id(work_id)
            for volume in volumes:
                await self._uow.volumes.delete(volume.id)

            deleted = await self._uow.works.delete(work_id)
            await self._uow.commit()
            return deleted

    async def search_works(self, query: str, pagination: PaginationParams) -> PaginatedResult[Work]:
        """Search works by title (supports fuzzy)."""
        works = await self._uow.works.find_by_title(query, fuzzy=True)
        # Simple pagination on in-memory results (for small datasets)
        start = pagination.offset
        end = start + pagination.page_size
        paginated = works[start:end]
        return PaginatedResult(
            items=paginated,
            total=len(works),
            page=pagination.page,
            page_size=pagination.page_size,
        )

    # =================== VOLUME OPERATIONS ===================

    async def get_volumes_for_work(self, work_id: int) -> List[Volume]:
        """Get all volumes for a work."""
        work = await self._uow.works.get_by_id(work_id)
        if not work:
            raise NotFoundError(f"Work {work_id} not found")
        return await self._uow.volumes.get_by_work_id(work_id)

    async def get_volume(self, volume_id: int) -> Volume:
        """Get volume by ID with chapters loaded."""
        volume = await self._uow.volumes.get_by_id(volume_id)
        if not volume:
            raise NotFoundError(f"Volume {volume_id} not found")

        chapters = await self._uow.chapters.get_by_volume_id(volume_id)
        volume._chapters = chapters
        return volume

    # =================== CHAPTER OPERATIONS ===================

    async def get_chapters_for_volume(self, volume_id: int) -> List[Chapter]:
        """Get all chapters for a volume."""
        volume = await self._uow.volumes.get_by_id(volume_id)
        if not volume:
            raise NotFoundError(f"Volume {volume_id} not found")
        return await self._uow.chapters.get_by_volume_id(volume_id)

    async def get_chapter(self, chapter_id: int) -> Chapter:
        """Get chapter by ID."""
        chapter = await self._uow.chapters.get_by_id(chapter_id)
        if not chapter:
            raise NotFoundError(f"Chapter {chapter_id} not found")
        return chapter