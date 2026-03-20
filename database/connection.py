from typing import Optional
from psycopg_pool import ConnectionPool, AsyncConnectionPool
from database.initializer import DatabaseInitializer


class DatabasePool:
    _instance: Optional["DatabasePool"] = None
    _sync_pool: Optional[ConnectionPool] = None
    _async_pool: Optional[AsyncConnectionPool] = None

    @classmethod
    def get_instance(cls, **kwargs) -> "DatabasePool":
        if cls._instance is None:
            cls._instance = cls(**kwargs)
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        cls._instance = None

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
            from GlobalConfig import GlobalConfig

            config = GlobalConfig()
            host = host or config.db_host
            port = port or config.db_port
            database = database or config.db_name
            user = user or config.db_user
            password = password or config.db_password
            min_size = min_size or config.db_min_pool_size
            max_size = max_size or config.db_max_pool_size

        self._conninfo = self.build_conninfo(host, port, database, user, password)
        self._min_size = min_size
        self._max_size = max_size

    @staticmethod
    def build_conninfo(
        host: str, port: int, database: str, user: str, password: str
    ) -> str:
        password_escaped = password.replace("\\", "\\\\").replace("'", "\\'")
        return (
            f"dbname={database} "
            f"user={user} "
            f"password='{password_escaped}' "
            f"host={host} "
            f"port={port}"
        )

    def get_sync_pool(self) -> ConnectionPool:
        if self._sync_pool is None:
            self._sync_pool = ConnectionPool(
                conninfo=self._conninfo,
                min_size=self._min_size,
                max_size=self._max_size,
                open=True,
            )
            DatabaseInitializer().ensure_tables_exist(self._sync_pool)
        return self._sync_pool

    async def get_async_pool(self) -> AsyncConnectionPool:
        if self._async_pool is None:
            self._async_pool = AsyncConnectionPool(
                conninfo=self._conninfo,
                min_size=self._min_size,
                max_size=self._max_size,
            )
            await self._async_pool.open()
            await DatabaseInitializer().ensure_tables_exist_async(self._async_pool)
        return self._async_pool

    async def close(self) -> None:
        if self._sync_pool is not None:
            self._sync_pool.close()
            self._sync_pool = None
        if self._async_pool is not None:
            await self._async_pool.close()
            self._async_pool = None
