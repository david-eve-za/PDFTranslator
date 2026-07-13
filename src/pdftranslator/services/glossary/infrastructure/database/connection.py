"""
Database Connection for Glossary Service.

CUPID Principle: Idiomatic
- Uses aiosqlite for async SQLite
- Connection pooling for performance
- Proper lifecycle management
"""

from __future__ import annotations
import aiosqlite
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from ....config import GlossarySettings


class DatabaseConnection:
    """Async SQLite database connection manager."""

    def __init__(self, settings: GlossarySettings):
        self._settings = settings
        self._pool: Optional[aiosqlite.Connection] = None
        self._db_path = Path(settings.database_path).resolve()

    @property
    def path(self) -> Path:
        return self._db_path

    async def connect(self) -> None:
        """Initialize database connection and schema."""
        # Ensure parent directory exists
        self._db_path.parent.mkdir(parents=True, exist_ok=True)

        self._pool = await aiosqlite.connect(
            self._db_path,
            timeout=30.0,
            isolation_level=None,  # Autocommit mode
        )
        # Enable foreign keys
        await self._pool.execute("PRAGMA foreign_keys = ON")
        # Use WAL mode for better concurrency
        await self._pool.execute("PRAGMA journal_mode = WAL")
        # Return rows as dict-like objects
        self._pool.row_factory = aiosqlite.Row

        await self._run_migrations()

    async def _run_migrations(self) -> None:
        """Run database migrations."""
        from .migrations import MIGRATIONS

        # Create migrations table
        await self._pool.execute("""
            CREATE TABLE IF NOT EXISTS _migrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(255) NOT NULL UNIQUE,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Get applied migrations
        cursor = await self._pool.execute("SELECT name FROM _migrations")
        applied = {row[0] for row in await cursor.fetchall()}

        # Apply pending migrations
        for migration in MIGRATIONS:
            if migration.name not in applied:
                print(f"Applying migration: {migration.name}")
                for statement in migration.statements:
                    await self._pool.execute(statement)
                await self._pool.execute(
                    "INSERT INTO _migrations (name) VALUES (?)",
                    (migration.name,),
                )
                await self._pool.commit()

    @asynccontextmanager
    async def connection(self):
        """Get database connection from pool."""
        if self._pool is None:
            await self.connect()
        yield self._pool

    @asynccontextmanager
    async def transaction(self):
        """Get a transaction context (yield same connection)."""
        async with self.connection() as conn:
            try:
                yield conn
                await conn.commit()
            except Exception:
                await conn.rollback()
                raise

    async def close(self) -> None:
        """Close database connection."""
        if self._pool:
            await self._pool.close()
            self._pool = None

    async def __aenter__(self) -> DatabaseConnection:
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()


# For sync operations (legacy compatibility)
import sqlite3
from contextlib import contextmanager
from pathlib import Path


class SyncDatabaseConnection:
    """Synchronous SQLite connection for legacy code."""

    def __init__(self, db_path: str):
        self._db_path = Path(db_path).resolve()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, timeout=30.0)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.row_factory = sqlite3.Row
        return conn

    @contextmanager
    def connection(self):
        """Get a database connection."""
        conn = self._get_connection()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @contextmanager
    def transaction(self):
        """Transaction context (same as connection for SQLite)."""
        with self.connection() as conn:
            yield conn