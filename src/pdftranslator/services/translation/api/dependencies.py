"""
FastAPI Dependencies for Translation Service.

CUPID Principle: Composable
- Dependencies injected, not hardcoded
- Easy to swap implementations for testing
"""

from __future__ import annotations
from functools import lru_cache
from fastapi import Depends

from ..config.settings import TranslationSettings
from ..infrastructure.database.connection import DatabaseConnection
from ..infrastructure.database.repositories import SQLiteUnitOfWork
from ..domain.services.translation_service import TranslationService


@lru_cache()
def get_settings() -> TranslationSettings:
    """Get application settings (cached singleton)."""
    return TranslationSettings()


async def get_database_connection(settings: TranslationSettings = Depends(get_settings)) -> DatabaseConnection:
    """Get database connection."""
    db = DatabaseConnection(settings)
    await db.connect()
    return db


async def get_unit_of_work(db: DatabaseConnection = Depends(get_database_connection)) -> SQLiteUnitOfWork:
    """Get Unit of Work for transactional operations."""
    return SQLiteUnitOfWork(db)


async def get_translation_service(uow: SQLiteUnitOfWork = Depends(get_unit_of_work)) -> TranslationService:
    """Get Translation Service with Unit of Work."""
    return TranslationService(uow)