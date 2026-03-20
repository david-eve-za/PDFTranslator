from typing import Optional
from psycopg_pool import ConnectionPool, AsyncConnectionPool


class DatabasePool:
    _sync_pool: Optional[ConnectionPool] = None
    _async_pool: Optional[AsyncConnectionPool] = None

    def __init__(
        self,
        host: str,
        port: int,
        database: str,
        user: str,
        password: str,
        min_size: int = 2,
        max_size: int = 10,
    ):
        self._conninfo = (
            f"dbname={database} "
            f"user={user} "
            f"password='{password}' "
            f"host={host} "
            f"port={port}"
        )
        self._min_size = min_size
        self._max_size = max_size

    @staticmethod
    def build_conninfo(
        host: str, port: int, database: str, user: str, password: str
    ) -> str:
        return (
            f"dbname={database} "
            f"user={user} "
            f"password='{password}' "
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
        return self._sync_pool

    async def get_async_pool(self) -> AsyncConnectionPool:
        if self._async_pool is None:
            self._async_pool = AsyncConnectionPool(
                conninfo=self._conninfo,
                min_size=self._min_size,
                max_size=self._max_size,
            )
            await self._async_pool.open()
        return self._async_pool

    async def close(self) -> None:
        if self._sync_pool is not None:
            self._sync_pool.close()
            self._sync_pool = None
        if self._async_pool is not None:
            await self._async_pool.close()
            self._async_pool = None
