import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from database.connection import DatabasePool


def test_database_pool_initialization():
    pool = DatabasePool("postgresql://localhost/test", min_size=2, max_size=10)
    assert pool._dsn == "postgresql://localhost/test"
    assert pool._min_size == 2
    assert pool._max_size == 10


def test_database_pool_build_dsn():
    pool = DatabasePool.build_dsn(
        host="localhost",
        port=5432,
        database="testdb",
        user="testuser",
        password="testpass",
    )
    assert pool == "postgresql://testuser:testpass@localhost:5432/testdb"


def test_database_pool_build_dsn_no_password():
    pool = DatabasePool.build_dsn(
        host="localhost", port=5432, database="testdb", user="testuser", password=""
    )
    assert pool == "postgresql://testuser@localhost:5432/testdb"


@patch("database.connection.ConnectionPool")
def test_get_sync_pool_creates_pool(mock_pool_class):
    mock_pool = MagicMock()
    mock_pool_class.return_value = mock_pool
    pool_manager = DatabasePool("postgresql://localhost/test")
    result = pool_manager.get_sync_pool()
    mock_pool_class.assert_called_once()
    assert result == mock_pool


@patch("database.connection.AsyncConnectionPool")
@pytest.mark.asyncio
async def test_get_async_pool_creates_pool(mock_pool_class):
    mock_pool = MagicMock()
    mock_pool.open = AsyncMock()
    mock_pool_class.return_value = mock_pool
    pool_manager = DatabasePool("postgresql://localhost/test")
    result = await pool_manager.get_async_pool()
    mock_pool_class.assert_called_once()
    assert result == mock_pool


class TestDatabaseInitializerIntegration:
    def test_get_sync_pool_calls_initializer(self):
        with (
            patch("database.connection.ConnectionPool") as mock_pool_class,
            patch("database.connection.DatabaseInitializer") as mock_initializer_class,
        ):
            mock_pool = MagicMock()
            mock_pool_class.return_value = mock_pool
            mock_initializer = mock_initializer_class.return_value
            pool_manager = DatabasePool(
                host="localhost",
                port=5432,
                database="testdb",
                user="testuser",
                password="testpass",
            )
            result = pool_manager.get_sync_pool()
            mock_initializer.ensure_tables_exist.assert_called_once_with(mock_pool)
            assert result == mock_pool

    def test_get_sync_pool_does_not_call_initializer_again_if_pool_exists(self):
        with (
            patch("database.connection.ConnectionPool") as mock_pool_class,
            patch("database.connection.DatabaseInitializer") as mock_initializer_class,
        ):
            mock_pool = MagicMock()
            mock_pool_class.return_value = mock_pool
            mock_initializer = mock_initializer_class.return_value
            pool_manager = DatabasePool(
                host="localhost",
                port=5432,
                database="testdb",
                user="testuser",
                password="testpass",
            )
            pool_manager.get_sync_pool()
            mock_initializer.ensure_tables_exist.reset_mock()
            pool_manager.get_sync_pool()
            mock_initializer.ensure_tables_exist.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_async_pool_calls_initializer(self):
        with (
            patch("database.connection.AsyncConnectionPool") as mock_pool_class,
            patch("database.connection.DatabaseInitializer") as mock_initializer_class,
        ):
            mock_pool = MagicMock()
            mock_pool.open = AsyncMock()
            mock_pool_class.return_value = mock_pool
            mock_initializer = mock_initializer_class.return_value
            mock_initializer.ensure_tables_exist_async = AsyncMock()
            pool_manager = DatabasePool(
                host="localhost",
                port=5432,
                database="testdb",
                user="testuser",
                password="testpass",
            )
            result = await pool_manager.get_async_pool()
            mock_initializer.ensure_tables_exist_async.assert_awaited_once_with(
                mock_pool
            )
            assert result == mock_pool

    @pytest.mark.asyncio
    async def test_get_async_pool_does_not_call_initializer_again_if_pool_exists(self):
        with (
            patch("database.connection.AsyncConnectionPool") as mock_pool_class,
            patch("database.connection.DatabaseInitializer") as mock_initializer_class,
        ):
            mock_pool = MagicMock()
            mock_pool.open = AsyncMock()
            mock_pool_class.return_value = mock_pool
            mock_initializer = mock_initializer_class.return_value
            mock_initializer.ensure_tables_exist_async = AsyncMock()
            pool_manager = DatabasePool(
                host="localhost",
                port=5432,
                database="testdb",
                user="testuser",
                password="testpass",
            )
            await pool_manager.get_async_pool()
            mock_initializer.ensure_tables_exist_async.reset_mock()
            await pool_manager.get_async_pool()
            mock_initializer.ensure_tables_exist_async.assert_not_awaited()
