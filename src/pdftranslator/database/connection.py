from typing import Optional
from urllib.parse import quote
from psycopg_pool import ConnectionPool, AsyncConnectionPool
from pdftranslator.database.initializer import DatabaseInitializer


class DatabasePool:
    _instance: Optional["DatabasePool"] = None
    _sync_pool: Optional[ConnectionPool] = None
    _async_pool: Optional[AsyncConnectionPool] = None
    _tables_initialized: bool = False

    @classmethod
    def get_instance(cls, **kwargs) -> "DatabasePool":
        if cls._instance is None:
            cls._instance = cls(**kwargs)
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        cls._instance = None
        cls._tables_initialized = False

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        database: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        min_size: Optional[int] = None,
        max_size: Optional[int] = None,
    ):
        if (
            host is None
            or port is None
            or database is None
            or user is None
            or password is None
        ):
            from pdftranslator.core.config.settings import Settings

            config = Settings.get()
            db = config.database
            host = host or db.host
            port = port or db.port
            database = database or db.name
            user = user or db.user
            password = password or db.password
            min_size = min_size or db.min_connections
            max_size = max_size or db.max_connections

        self._conninfo = self.build_conninfo(host, port, database, user, password)
        self._min_size = min_size
        self._max_size = max_size

    @staticmethod
    def build_conninfo(
        host: str, port: int, database: str, user: str, password: str
    ) -> str:
        # Use PostgreSQL URI format which handles special characters better
        from urllib.parse import quote_plus

        password_escaped = quote_plus(password)
        return f"postgresql://{user}:{password_escaped}@{host}:{port}/{database}"

    def get_sync_pool(self) -> ConnectionPool:
        if self._sync_pool is None:
            self._sync_pool = ConnectionPool(
                conninfo=self._conninfo,
                min_size=self._min_size,
                max_size=self._max_size,
                open=False,
            )
            self._sync_pool.open(wait=True)
            if not DatabasePool._tables_initialized:
                DatabaseInitializer().ensure_tables_exist(self._sync_pool)
                DatabasePool._tables_initialized = True
        return self._sync_pool

    async def get_async_pool(self) -> AsyncConnectionPool:
        if self._async_pool is None:
            self._async_pool = AsyncConnectionPool(
                conninfo=self._conninfo,
                min_size=self._min_size,
                max_size=self._max_size,
            )
            await self._async_pool.open()
            if not DatabasePool._tables_initialized:
                await DatabaseInitializer().ensure_tables_exist_async(self._async_pool)
                DatabasePool._tables_initialized = True
        return self._async_pool

    async def close(self) -> None:
        if self._sync_pool is not None:
            self._sync_pool.close()
            self._sync_pool = None
        if self._async_pool is not None:
            await self._async_pool.close()
            self._async_pool = None
