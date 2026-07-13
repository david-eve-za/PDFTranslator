"""
FastAPI Dependencies for Glossary Service.

CUPID Principle: Composable
- Dependencies injected, not hardcoded
- Easy to swap implementations for testing
"""

from __future__ import annotations
from functools import lru_cache
from fastapi import Depends

from ..config import GlossarySettings
from ...infrastructure.database.connection import DatabaseConnection
from ...infrastructure.database.repositories import SQLiteGlossaryUnitOfWork
from ...domain.services.glossary_service import GlossaryService
from ...domain.repositories.protocols import EntityExtractorRepository
from ...infrastructure.database.repositories import SQLiteEntityExtractorRepository


@lru_cache()
def get_settings() -> GlossarySettings:
    """Get application settings (cached singleton)."""
    return GlossarySettings()


async def get_database_connection(
    settings: GlossarySettings = Depends(get_settings),
) -> DatabaseConnection:
    """Get database connection."""
    db = DatabaseConnection(settings)
    await db.connect()
    return db


async def get_unit_of_work(
    db: DatabaseConnection = Depends(get_database_connection),
) -> SQLiteGlossaryUnitOfWork:
    """Get Unit of Work for transactional operations."""
    return SQLiteGlossaryUnitOfWork(db)


async def get_entity_extractor(
    db: DatabaseConnection = Depends(get_database_connection),
) -> EntityExtractorRepository:
    """Get entity extractor repository."""
    return SQLiteEntityExtractorRepository(db)


async def get_glossary_service(
    uow: SQLiteGlossaryUnitOfWork = Depends(get_unit_of_work),
    entity_extractor: EntityExtractorRepository = Depends(get_entity_extractor),
) -> GlossaryService:
    """Get Glossary Service with all dependencies."""
    return GlossaryService(uow)


# Override for testing - add to conftest.py or test setup
def override_get_glossary_service(service: GlossaryService):
    """Override glossary service for testing."""
    import sys
    if "tests" in sys.modules:
        sys.modules["src.pdftranslator.services.glossary.api.dependencies"].get_glossary_service = lambda: service