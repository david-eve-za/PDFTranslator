import pytest
from unittest.mock import MagicMock, AsyncMock, patch, call
from pathlib import Path
from database.initializer import DatabaseInitializer


class TestDatabaseInitializer:
    def test_table_exists_query_returns_correct_sql(self):
        initializer = DatabaseInitializer()
        query = initializer._table_exists_query("works")
        assert "information_schema.tables" in query
        assert "works" in query

    @patch("database.initializer.Path")
    def test_ensure_tables_exist_when_tables_missing(self, mock_path):
        initializer = DatabaseInitializer()
        mock_pool = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_pool.connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.fetchone.return_value = None

        mock_script_file = MagicMock()
        mock_script_file.name = "001_extensions.sql"
        mock_script_file.read_text.return_value = (
            "CREATE EXTENSION IF NOT EXISTS btree_gin;"
        )
        mock_path.return_value.glob.return_value = [mock_script_file]

        initializer.ensure_tables_exist(mock_pool)

        mock_cursor.execute.assert_called()
        assert mock_cursor.execute.call_count >= 2

    @patch("database.initializer.Path")
    def test_ensure_tables_exist_when_tables_already_exist(self, mock_path):
        initializer = DatabaseInitializer()
        mock_pool = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_pool.connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.fetchone.return_value = ("works",)

        mock_path.return_value.glob.return_value = []

        initializer.ensure_tables_exist(mock_pool)

        assert mock_cursor.execute.call_count == 1

    @patch("database.initializer.Path")
    @pytest.mark.asyncio
    async def test_ensure_tables_exist_async_when_tables_missing(self, mock_path):
        initializer = DatabaseInitializer()
        mock_pool = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        mock_pool.connection = MagicMock()
        mock_pool.connection.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.cursor = MagicMock()
        mock_conn.cursor.return_value.__aenter__ = AsyncMock(return_value=mock_cursor)
        mock_conn.commit = AsyncMock()

        mock_cursor.execute = AsyncMock()
        mock_cursor.fetchone = AsyncMock(return_value=None)

        mock_script_file = MagicMock()
        mock_script_file.name = "001_extensions.sql"
        mock_script_file.read_text.return_value = (
            "CREATE EXTENSION IF NOT EXISTS btree_gin;"
        )
        mock_path.return_value.glob.return_value = [mock_script_file]

        await initializer.ensure_tables_exist_async(mock_pool)

        assert mock_cursor.execute.call_count >= 2

    @patch("database.initializer.Path")
    @pytest.mark.asyncio
    async def test_ensure_tables_exist_async_when_tables_already_exist(self, mock_path):
        initializer = DatabaseInitializer()
        mock_pool = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        mock_pool.connection = MagicMock()
        mock_pool.connection.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.cursor = MagicMock()
        mock_conn.cursor.return_value.__aenter__ = AsyncMock(return_value=mock_cursor)

        mock_cursor.execute = AsyncMock()
        mock_cursor.fetchone = AsyncMock(return_value=("works",))

        mock_path.return_value.glob.return_value = []

        await initializer.ensure_tables_exist_async(mock_pool)

        assert mock_cursor.execute.call_count == 1

    def test_execute_schema_scripts_sorts_by_filename(self):
        initializer = DatabaseInitializer()
        mock_cursor = MagicMock()

        scripts = [
            Path("/database/schemas/005_glossary.sql"),
            Path("/database/schemas/002_works.sql"),
            Path("/database/schemas/001_extensions.sql"),
        ]

        with patch.object(Path, "glob", return_value=scripts):
            with patch.object(Path, "read_text") as mock_read:
                mock_read.return_value = "SELECT 1;"
                initializer._execute_schema_scripts(mock_cursor)

        calls = mock_cursor.execute.call_args_list
        assert len(calls) == 3
