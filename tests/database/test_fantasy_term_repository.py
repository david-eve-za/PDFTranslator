import pytest
from unittest.mock import MagicMock, patch
from database.repositories.fantasy_term_repository import FantasyTermRepository
from database.models import FantasyTerm
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


class TestFantasyTermRepository:
    def test_get_all_terms_returns_dict(self, mock_pool, mock_connection):
        mock_pool.get_sync_pool.return_value.connection.return_value.__enter__ = (
            MagicMock(return_value=mock_connection[0])
        )
        mock_connection[1].fetchall.return_value = [
            (1, "slime", "race", False, None),
            (2, "dragon", "race", False, None),
        ]

        repo = FantasyTermRepository(mock_pool)
        terms = repo.get_all_terms()

        assert isinstance(terms, dict)
        assert "slime" in terms
        assert terms["slime"].entity_type == "race"

    def test_get_by_term(self, mock_pool, mock_connection):
        mock_pool.get_sync_pool.return_value.connection.return_value.__enter__ = (
            MagicMock(return_value=mock_connection[0])
        )
        mock_connection[1].fetchone.return_value = (1, "dragon", "race", False, None)

        repo = FantasyTermRepository(mock_pool)
        term = repo.get_by_term("dragon")

        assert term is not None
        assert term.entity_type == "race"

    def test_get_by_term_case_insensitive(self, mock_pool, mock_connection):
        mock_pool.get_sync_pool.return_value.connection.return_value.__enter__ = (
            MagicMock(return_value=mock_connection[0])
        )
        mock_connection[1].fetchone.return_value = (1, "dragon", "race", False, None)

        repo = FantasyTermRepository(mock_pool)
        term = repo.get_by_term("DRAGON")

        assert term is not None

    def test_get_by_term_returns_none_for_missing(self, mock_pool, mock_connection):
        mock_pool.get_sync_pool.return_value.connection.return_value.__enter__ = (
            MagicMock(return_value=mock_connection[0])
        )
        mock_connection[1].fetchone.return_value = None

        repo = FantasyTermRepository(mock_pool)
        term = repo.get_by_term("nonexistent")

        assert term is None

    def test_get_all_returns_list(self, mock_pool, mock_connection):
        mock_pool.get_sync_pool.return_value.connection.return_value.__enter__ = (
            MagicMock(return_value=mock_connection[0])
        )
        mock_connection[1].fetchall.return_value = [
            (1, "elf", "race", False, None),
            (2, "mana", "resource", True, "magical energy"),
        ]

        repo = FantasyTermRepository(mock_pool)
        result = repo.get_all()

        assert isinstance(result, list)
        assert len(result) == 2

    def test_create_fantasy_term(self, mock_pool, mock_connection):
        mock_pool.get_sync_pool.return_value.connection.return_value.__enter__ = (
            MagicMock(return_value=mock_connection[0])
        )
        mock_connection[1].fetchone.return_value = (1, "goblin", "race", False, None)

        repo = FantasyTermRepository(mock_pool)
        term = FantasyTerm(id=None, term="goblin", entity_type="race")
        result = repo.create(term)

        assert result.id == 1
        assert result.term == "goblin"

    def test_delete_returns_true_when_deleted(self, mock_pool, mock_connection):
        mock_pool.get_sync_pool.return_value.connection.return_value.__enter__ = (
            MagicMock(return_value=mock_connection[0])
        )
        mock_connection[1].rowcount = 1

        repo = FantasyTermRepository(mock_pool)
        result = repo.delete(1)

        assert result is True
