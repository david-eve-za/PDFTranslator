"""Database initialization for SQLite."""

import logging
import sqlite3
import aiosqlite
from pathlib import Path
from typing import Union

logger = logging.getLogger(__name__)


class DatabaseInitializer:
    SCHEMAS_DIR = Path(__file__).parent / "schemas"

    def ensure_tables_exist(self, conn: Union[sqlite3.Connection, aiosqlite.Connection]) -> None:
        """Check if tables exist and create schema if not."""
        logger.debug("Checking if database tables exist")
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='works'")
        result = cursor.fetchone()
        if result is None:
            logger.info("Tables not found, initializing database schema")
            self._execute_schema_scripts(cur=cursor)
            conn.commit()
            logger.info("Database schema initialized successfully")
        else:
            logger.debug("Database tables already exist")

    async def ensure_tables_exist_async(self, conn: aiosqlite.Connection) -> None:
        """Async version - check if tables exist and create schema if not."""
        logger.debug("Checking if database tables exist (async)")
        cursor = await conn.cursor()
        await cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='works'")
        result = await cursor.fetchone()
        if result is None:
            logger.info("Tables not found, initializing database schema (async)")
            await self._execute_schema_scripts_async(cursor)
            await conn.commit()
            logger.info("Database schema initialized successfully (async)")
        else:
            logger.debug("Database tables already exist")

    def _table_exists_query(self, table_name: str) -> str:
        """Query to check if a table exists in SQLite."""
        return f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'"

    def _execute_schema_scripts(self, cur) -> None:
        """Execute all schema SQL files in order (sync)."""
        schema_files = sorted(self.SCHEMAS_DIR.glob("*.sql"), key=lambda p: p.name)
        for schema_file in schema_files:
            logger.debug(f"Executing schema script: {schema_file.name}")
            sql_content = schema_file.read_text(encoding="utf-8")
            cur.executescript(sql_content)
            logger.debug(f"Schema script executed: {schema_file.name}")

    async def _execute_schema_scripts_async(self, cursor) -> None:
        """Execute all schema SQL files in order (async)."""
        schema_files = sorted(self.SCHEMAS_DIR.glob("*.sql"), key=lambda p: p.name)
        for schema_file in schema_files:
            logger.debug(f"Executing schema script: {schema_file.name}")
            sql_content = schema_file.read_text(encoding="utf-8")
            await cursor.executescript(sql_content)
            logger.debug(f"Schema script executed: {schema_file.name}")


def init_database_sync(db_path: Path | str) -> None:
    """Initialize database synchronously - utility function."""
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(str(db_path)) as conn:
        conn.row_factory = sqlite3.Row
        initializer = DatabaseInitializer()
        initializer.ensure_tables_exist(conn)


async def init_database_async(db_path: Path | str) -> None:
    """Initialize database asynchronously - utility function."""
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(str(db_path)) as conn:
        conn.row_factory = aiosqlite.Row
        initializer = DatabaseInitializer()
        await initializer.ensure_tables_exist_async(conn)