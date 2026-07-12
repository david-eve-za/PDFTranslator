"""SQLite database connection pool with sync and async support."""

import sqlite3
import aiosqlite
from contextlib import contextmanager, asynccontextmanager
from pathlib import Path
from typing import Optional, AsyncGenerator
import logging

from pdftranslator.core.config.settings import Settings
from pdftranslator.database.initializer import DatabaseInitializer

logger = logging.getLogger(__name__)


class DatabasePool:
    """Manages SQLite database connections (sync and async)."""

    _instance: Optional["DatabasePool"] = None
    _tables_initialized: bool = False

    @classmethod
    def get_instance(cls, **kwargs) -> "DatabasePool":
        if cls._instance is None:
            cls._instance = cls(**kwargs)
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance (useful for testing)."""
        if cls._instance:
            # Close sync connection
            if cls._instance._sync_conn:
                cls._instance._sync_conn.close()
            cls._instance = None
        cls._tables_initialized = False

    def __init__(
        self,
        db_path: Optional[Path] = None,
        journal_mode: str = "WAL",
        synchronous: str = "NORMAL",
        cache_size: int = -32768,
        temp_store: str = "MEMORY",
        busy_timeout: int = 5000,
    ):
        if db_path is None:
            config = Settings.get()
            db = config.database
            db_path = db.path
            journal_mode = db.journal_mode
            synchronous = db.synchronous
            cache_size = db.cache_size
            temp_store = db.temp_store
            busy_timeout = db.busy_timeout

        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)

        # Connection configuration
        self._journal_mode = journal_mode
        self._synchronous = synchronous
        self._cache_size = cache_size
        self._temp_store = temp_store
        self._busy_timeout = busy_timeout

        # Sync connection (single connection for SQLite)
        self._sync_conn: Optional[sqlite3.Connection] = None

        # Async connection
        self._async_conn: Optional[aiosqlite.Connection] = None

    def _configure_connection(self, conn: sqlite3.Connection) -> None:
        """Apply SQLite PRAGMA settings for optimal performance."""
        conn.execute(f"PRAGMA journal_mode = {self._journal_mode}")
        conn.execute(f"PRAGMA synchronous = {self._synchronous}")
        conn.execute(f"PRAGMA cache_size = {self._cache_size}")
        conn.execute(f"PRAGMA temp_store = {self._temp_store}")
        conn.execute(f"PRAGMA busy_timeout = {self._busy_timeout}")
        conn.execute("PRAGMA foreign_keys = ON")
        # Return rows as dictionaries
        conn.row_factory = sqlite3.Row

    async def _configure_async_connection(self, conn: aiosqlite.Connection) -> None:
        """Apply SQLite PRAGMA settings for async connection."""
        await conn.execute(f"PRAGMA journal_mode = {self._journal_mode}")
        await conn.execute(f"PRAGMA synchronous = {self._synchronous}")
        await conn.execute(f"PRAGMA cache_size = {self._cache_size}")
        await conn.execute(f"PRAGMA temp_store = {self._temp_store}")
        await conn.execute(f"PRAGMA busy_timeout = {self._busy_timeout}")
        await conn.execute("PRAGMA foreign_keys = ON")
        conn.row_factory = aiosqlite.Row

    @contextmanager
    def connection(self) -> sqlite3.Connection:
        """Get a synchronous database connection (context manager)."""
        # Ensure tables are initialized when getting a connection
        if not DatabasePool._tables_initialized:
            # Create a temporary connection to initialize tables
            temp_conn = sqlite3.connect(str(self._db_path))
            self._configure_connection(temp_conn)
            DatabaseInitializer().ensure_tables_exist(temp_conn)
            temp_conn.commit()
            temp_conn.close()
            DatabasePool._tables_initialized = True

        if self._sync_conn is None:
            self._sync_conn = sqlite3.connect(
                str(self._db_path),
                check_same_thread=False,  # Allow multi-threaded access
            )
            self._configure_connection(self._sync_conn)
            logger.debug(f"Opened SQLite connection to {self._db_path}")

        try:
            yield self._sync_conn
            self._sync_conn.commit()
        except Exception:
            self._sync_conn.rollback()
            raise

    def get_sync_pool(self) -> "DatabasePool":
        """Return self for compatibility with existing code."""
        # Ensure tables are initialized
        if not DatabasePool._tables_initialized:
            temp_conn = sqlite3.connect(str(self._db_path))
            self._configure_connection(temp_conn)
            DatabaseInitializer().ensure_tables_exist(temp_conn)
            temp_conn.commit()
            temp_conn.close()
            DatabasePool._tables_initialized = True
        return self

    @asynccontextmanager
    async def async_connection(self) -> AsyncGenerator[aiosqlite.Connection, None]:
        """Get an asynchronous database connection (context manager)."""
        # Ensure tables are initialized when getting a connection
        if not DatabasePool._tables_initialized:
            # Create a temporary connection to initialize tables
            temp_conn = await aiosqlite.connect(str(self._db_path))
            await self._configure_async_connection(temp_conn)
            await DatabaseInitializer().ensure_tables_exist_async(temp_conn)
            await temp_conn.commit()
            await temp_conn.close()
            DatabasePool._tables_initialized = True

        if self._async_conn is None:
            self._async_conn = await aiosqlite.connect(str(self._db_path))
            await self._configure_async_connection(self._async_conn)
            logger.debug(f"Opened async SQLite connection to {self._db_path}")

        try:
            yield self._async_conn
            await self._async_conn.commit()
        except Exception:
            await self._async_conn.rollback()
            raise

    async def get_async_pool(self) -> "DatabasePool":
        """Return self for compatibility with existing code."""
        if not DatabasePool._tables_initialized:
            temp_conn = await aiosqlite.connect(str(self._db_path))
            await self._configure_async_connection(temp_conn)
            await DatabaseInitializer().ensure_tables_exist_async(temp_conn)
            await temp_conn.commit()
            await temp_conn.close()
            DatabasePool._tables_initialized = True
        return self

    async def close(self) -> None:
        """Close all connections."""
        if self._sync_conn is not None:
            self._sync_conn.close()
            self._sync_conn = None
        if self._async_conn is not None:
            await self._async_conn.close()
            self._async_conn = None
        logger.debug(f"Closed SQLite connections to {self._db_path}")

    @property
    def db_path(self) -> Path:
        """Return the database file path."""
        return self._db_path