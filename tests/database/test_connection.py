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
