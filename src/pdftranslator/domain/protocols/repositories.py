"""Repository protocols — segregated interfaces.

Resolves ISP-2 and LSP-1: Not all repositories need full CRUD.
GlossaryBuildProgressRepository only needs batch operations.
"""
from __future__ import annotations

from typing import Protocol, TypeVar, runtime_checkable

T = TypeVar("T")


@runtime_checkable
class ReadRepository(Protocol[T]):
    """Read-only repository interface."""

    def get_by_id(self, id: int) -> T | None:
        ...

    def get_all(self) -> list[T]:
        ...


@runtime_checkable
class WriteRepository(Protocol[T]):
    """Write-only repository interface."""

    def create(self, entity: T) -> T:
        ...

    def update(self, entity: T) -> T:
        ...

    def delete(self, id: int) -> bool:
        ...


@runtime_checkable
class GlossaryProgressTracker(Protocol):
    """Interface for glossary build progress tracking.

    Resolves LSP-1: GlossaryBuildProgressRepository
    should not be forced to implement full CRUD.
    """

    def save_extracted(
        self, work_id: int, volume_id: int, entities: list
    ) -> list:
        ...

    def get_pending_for_phase(
        self, work_id: int, volume_id: int, phase: str
    ) -> list:
        ...

    def batch_update_phase(
        self,
        ids: list[int],
        phase: str,
        batch_num: int | None = None,
    ) -> None:
        ...

    def get_resume_point(
        self, work_id: int, volume_id: int
    ) -> tuple[str, int | None]:
        ...

    def cleanup_completed(self, volume_id: int) -> None:
        ...
