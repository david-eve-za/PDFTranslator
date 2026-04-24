import pytest
from unittest.mock import MagicMock, patch
from database.repositories.entity_blacklist_repository import EntityBlacklistRepository
from database.models import EntityBlacklist
from database.connection import DatabasePool


@pytest.fixture
def mock_pool():
    return MagicMock()


@pytest.fixture
def mock_connection():
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    return conn, cursor


@pytest.fixture(autouse=True)
def reset_database_pool():
    DatabasePool.reset_instance()
    yield
    DatabasePool.reset_instance()


class TestEntityBlacklistRepository:
    def test_get_all_terms_returns_set(self, mock_pool, mock_connection):
        mock_pool.get_sync_pool.return_value.connection.return_value.__enter__ = (
            MagicMock(return_value=mock_connection[0])
        )
        mock_connection[1].fetchall.return_value = [
            ("the",),
            ("chapter",),
        ]

        repo = EntityBlacklistRepository(mock_pool)
        terms = repo.get_all_terms()

        assert isinstance(terms, set)
        assert "the" in terms
        assert "chapter" in terms

    def test_add_and_remove(self, mock_pool, mock_connection):
        mock_pool.get_sync_pool.return_value.connection.return_value.__enter__ = (
            MagicMock(return_value=mock_connection[0])
        )

        mock_connection[1].fetchone.return_value = (1, "test_term_123", "test reason")
        repo = EntityBlacklistRepository(mock_pool)
        added = repo.add("test_term_123", "test reason")

        assert added.term == "test_term_123"

        mock_connection[1].fetchone.return_value = (1,)
        assert repo.exists("test_term_123")

        mock_connection[1].rowcount = 1
        removed = repo.remove("test_term_123")
        assert removed is True

    def test_exists_returns_false_for_missing_term(self, mock_pool, mock_connection):
        mock_pool.get_sync_pool.return_value.connection.return_value.__enter__ = (
            MagicMock(return_value=mock_connection[0])
        )
        mock_connection[1].fetchone.return_value = None

        repo = EntityBlacklistRepository(mock_pool)
        result = repo.exists("nonexistent_term")

        assert result is False

    def test_get_by_id_returns_entity(self, mock_pool, mock_connection):
        mock_pool.get_sync_pool.return_value.connection.return_value.__enter__ = (
            MagicMock(return_value=mock_connection[0])
        )
        mock_connection[1].fetchone.return_value = (1, "the", "common word")

        repo = EntityBlacklistRepository(mock_pool)
        result = repo.get_by_id(1)

        assert result is not None
        assert result.term == "the"
        assert result.reason == "common word"

    def test_get_all_returns_list(self, mock_pool, mock_connection):
        mock_pool.get_sync_pool.return_value.connection.return_value.__enter__ = (
            MagicMock(return_value=mock_connection[0])
        )
        mock_connection[1].fetchall.return_value = [
            (1, "the", "common word"),
            (2, "a", "article"),
        ]

        repo = EntityBlacklistRepository(mock_pool)
        result = repo.get_all()

        assert isinstance(result, list)
        assert len(result) == 2

    def test_remove_returns_false_when_not_found(self, mock_pool, mock_connection):
        mock_pool.get_sync_pool.return_value.connection.return_value.__enter__ = (
            MagicMock(return_value=mock_connection[0])
        )
        mock_connection[1].rowcount = 0

        repo = EntityBlacklistRepository(mock_pool)
        result = repo.remove("nonexistent")

        assert result is False
