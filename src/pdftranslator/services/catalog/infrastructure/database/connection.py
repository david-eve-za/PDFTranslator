"""
Database connection management for Catalog Service.

CUPID Principle: Predictable
- Explicit connection lifecycle
- Connection pooling
- Proper error handling
"""

from __future__ import annotations
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional
import aiosqlite
from pathlib import Path

from ...config.settings import CatalogSettings


class DatabaseConnection:
    """Manages async SQLite connections with WAL mode."""

    def __init__(self, settings: CatalogSettings):
        self._settings = settings
        self._db_path = Path(settings.database_path).expanduser().resolve()
        self._pool: Optional[aiosqlite.Connection] = None

    async def connect(self) -> None:
        """Initialize connection with WAL mode and foreign keys."""
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._pool = await aiosqlite.connect(
            self._db_path,
            timeout=30.0,
            isolation_level=None,  # Autocommit mode, we manage transactions
        )
        # Enable WAL mode for better concurrency
        await self._pool.execute("PRAGMA journal_mode=WAL")
        # Enable foreign key constraints
        await self._pool.execute("PRAGMA foreign_keys=ON")
        # Return rows as dict-like objects
        self._pool.row_factory = aiosqlite.Row
        await self._pool.commit()

    async def disconnect(self) -> None:
        """Close database connection."""
        if self._pool:
            await self._pool.close()
            self._pool = None

    @asynccontextmanager
    async def transaction(self) -> AsyncGenerator[aiosqlite.Connection, None]:
        """Provide transactional connection."""
        if not self._pool:
            await self.connect()

        async with self._pool.cursor() as cursor:
            try:
                await cursor.execute("BEGIN")
                yield self._pool
                await self._pool.commit()
            except Exception:
                await self._pool.rollback()
                raise

    @asynccontextmanager
    async def read_only(self) -> AsyncGenerator[aiosqlite.Connection, None]:
        """Provide read-only connection."""
        if not self._pool:
            await self.connect()
        yield self._pool

    @property
    def is_connected(self) -> bool:
        return self._pool is not None