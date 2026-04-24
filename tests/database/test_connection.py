import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from database.connection import DatabasePool


def test_database_pool_initialization():
    pool = DatabasePool(
        host="localhost",
        port=5432,
        database="testdb",
        user="testuser",
        password="testpass",
        min_size=2,
        max_size=10,
    )
    assert "dbname=testdb" in pool._conninfo
    assert "user=testuser" in pool._conninfo
    assert "host=localhost" in pool._conninfo
    assert pool._min_size == 2
    assert pool._max_size == 10


def test_database_pool_build_conninfo():
    conninfo = DatabasePool.build_conninfo(
        host="localhost",
        port=5432,
        database="testdb",
        user="testuser",
        password="testpass",
    )
    assert "dbname=testdb" in conninfo
    assert "user=testuser" in conninfo
    assert "password='testpass'" in conninfo
    assert "host=localhost" in conninfo
    assert "port=5432" in conninfo


def test_database_pool_build_conninfo_no_password():
    conninfo = DatabasePool.build_conninfo(
        host="localhost", port=5432, database="testdb", user="testuser", password=""
    )
    assert "dbname=testdb" in conninfo
    assert "user=testuser" in conninfo
    assert "password=''" in conninfo
    assert "host=localhost" in conninfo


@patch("database.connection.ConnectionPool")
@patch("database.connection.DatabaseInitializer")
def test_get_sync_pool_creates_pool(mock_initializer_class, mock_pool_class):
    mock_pool = MagicMock()
    mock_pool_class.return_value = mock_pool
    pool_manager = DatabasePool(
        host="localhost",
        port=5432,
        database="testdb",
        user="testuser",
        password="testpass",
    )
    result = pool_manager.get_sync_pool()
    mock_pool_class.assert_called_once()
    assert result == mock_pool


@patch("database.connection.AsyncConnectionPool")
@patch("database.connection.DatabaseInitializer")
@pytest.mark.asyncio
async def test_get_async_pool_creates_pool(mock_initializer_class, mock_pool_class):
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


class TestDatabasePoolSingleton:
    def test_get_instance_returns_same_instance_on_multiple_calls(self):
        DatabasePool.reset_instance()
        instance1 = DatabasePool.get_instance(
            host="localhost",
            port=5432,
            database="testdb",
            user="testuser",
            password="testpass",
        )
        instance2 = DatabasePool.get_instance(
            host="localhost",
            port=5432,
            database="testdb",
            user="testuser",
            password="testpass",
        )
        assert instance1 is instance2
        DatabasePool.reset_instance()

    def test_get_instance_uses_global_config_when_no_params_provided(self):
        DatabasePool.reset_instance()
        instance = DatabasePool.get_instance()
        assert instance._min_size == 2
        assert instance._max_size == 10
        assert "dbname=book_translator" in instance._conninfo
        assert "user=translator_user" in instance._conninfo
        assert "host=localhost" in instance._conninfo
        assert "port=5432" in instance._conninfo
        DatabasePool.reset_instance()

    def test_get_instance_accepts_custom_config_parameters(self):
        DatabasePool.reset_instance()
        instance = DatabasePool.get_instance(
            host="customhost",
            port=5433,
            database="customdb",
            user="customuser",
            password="custompass",
            min_size=5,
            max_size=20,
        )
        assert "dbname=customdb" in instance._conninfo
        assert "user=customuser" in instance._conninfo
        assert "host=customhost" in instance._conninfo
        assert "port=5433" in instance._conninfo
        assert instance._min_size == 5
        assert instance._max_size == 20
        DatabasePool.reset_instance()

    def test_reset_instance_clears_the_singleton(self):
        instance1 = DatabasePool.get_instance(
            host="localhost",
            port=5432,
            database="testdb",
            user="testuser",
            password="testpass",
        )
        DatabasePool.reset_instance()
        instance2 = DatabasePool.get_instance(
            host="different",
            port=5432,
            database="testdb",
            user="testuser",
            password="testpass",
        )
        assert instance1 is not instance2
        DatabasePool.reset_instance()
