"""
FastAPI Dependencies for Catalog Service.

CUPID Principle: Composable
- Dependencies injected, not hardcoded
- Easy to swap implementations for testing
"""

from __future__ import annotations
from functools import lru_cache
from fastapi import Depends

from ...config.settings import CatalogSettings
from ...infrastructure.database.connection import DatabaseConnection
from ...infrastructure.database.repositories import SQLiteUnitOfWork
from ...domain.services.catalog_service import CatalogService


@lru_cache()
def get_settings() -> CatalogSettings:
    """Get application settings (cached singleton)."""
    return CatalogSettings()


async def get_database_connection(settings: CatalogSettings = Depends(get_settings)) -> DatabaseConnection:
    """Get database connection."""
    db = DatabaseConnection(settings)
    await db.connect()
    return db


async def get_unit_of_work(db: DatabaseConnection = Depends(get_database_connection)) -> SQLiteUnitOfWork:
    """Get Unit of Work for transactional operations."""
    return SQLiteUnitOfWork(db)


async def get_catalog_service(uow: SQLiteUnitOfWork = Depends(get_unit_of_work)) -> CatalogService:
    """Get Catalog Service with Unit of Work."""
    return CatalogService(uow)