import logging
from pathlib import Path
from psycopg_pool import ConnectionPool, AsyncConnectionPool

logger = logging.getLogger(__name__)


class DatabaseInitializer:
    SCHEMAS_DIR = Path(__file__).parent / "schemas"

    def ensure_tables_exist(self, pool: ConnectionPool) -> None:
        logger.debug("Checking if database tables exist")
        with pool.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(self._table_exists_query("works"))
                result = cursor.fetchone()
                if result is None:
                    logger.info("Tables not found, initializing database schema")
                    self._execute_schema_scripts(cursor)
                    conn.commit()
                    logger.info("Database schema initialized successfully")
                else:
                    logger.debug("Database tables already exist")

    async def ensure_tables_exist_async(self, pool: AsyncConnectionPool) -> None:
        logger.debug("Checking if database tables exist")
        async with pool.connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(self._table_exists_query("works"))
                result = await cursor.fetchone()
                if result is None:
                    logger.info("Tables not found, initializing database schema")
                    await self._execute_schema_scripts_async(cursor)
                    await conn.commit()
                    logger.info("Database schema initialized successfully")
                else:
                    logger.debug("Database tables already exist")

    def _table_exists_query(self, table_name: str) -> str:
        return (
            f"SELECT table_name FROM information_schema.tables "
            f"WHERE table_schema = 'public' AND table_name = '{table_name}'"
        )

    def _execute_schema_scripts(self, cursor) -> None:
        schema_files = sorted(self.SCHEMAS_DIR.glob("*.sql"), key=lambda p: p.name)
        for schema_file in schema_files:
            logger.debug(f"Executing schema script: {schema_file.name}")
            sql_content = schema_file.read_text()
            cursor.execute(sql_content)
            logger.debug(f"Schema script executed: {schema_file.name}")

    async def _execute_schema_scripts_async(self, cursor) -> None:
        schema_files = sorted(self.SCHEMAS_DIR.glob("*.sql"), key=lambda p: p.name)
        for schema_file in schema_files:
            logger.debug(f"Executing schema script: {schema_file.name}")
            sql_content = schema_file.read_text()
            await cursor.execute(sql_content)
            logger.debug(f"Schema script executed: {schema_file.name}")
