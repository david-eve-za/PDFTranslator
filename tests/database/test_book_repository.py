import pytest
from unittest.mock import MagicMock, patch
from database.repositories.book_repository import BookRepository
from database.models import Work, Volume
from database.exceptions import EntityNotFoundError


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


def test_book_repository_inherits_from_base():
    from database.repositories.base import BaseRepository

    assert issubclass(BookRepository, BaseRepository)


@patch("database.repositories.book_repository.ConnectionPool")
def test_get_by_id_returns_work(mock_pool_class, mock_pool, mock_connection):
    mock_pool_class.return_value = mock_pool
    mock_pool.connection.return_value.__enter__ = MagicMock(
        return_value=mock_connection[0]
    )
    mock_connection[1].fetchone.return_value = (
        1,
        "Test Novel",
        None,
        "en",
        "es",
        None,
        None,
        None,
    )
    repo = BookRepository("postgresql://localhost/test")
    result = repo.get_by_id(1)
    assert result is not None
    assert result.id == 1
    assert result.title == "Test Novel"


@patch("database.repositories.book_repository.ConnectionPool")
def test_get_by_id_not_found(mock_pool_class, mock_pool, mock_connection):
    mock_pool_class.return_value = mock_pool
    mock_pool.connection.return_value.__enter__ = MagicMock(
        return_value=mock_connection[0]
    )
    mock_connection[1].fetchone.return_value = None
    repo = BookRepository("postgresql://localhost/test")
    result = repo.get_by_id(999)
    assert result is None


@patch("database.repositories.book_repository.ConnectionPool")
def test_create_work(mock_pool_class, mock_pool, mock_connection):
    mock_pool_class.return_value = mock_pool
    mock_pool.connection.return_value.__enter__ = MagicMock(
        return_value=mock_connection[0]
    )
    mock_connection[1].fetchone.return_value = (
        1,
        "New Novel",
        None,
        "en",
        "es",
        None,
        None,
        None,
    )
    repo = BookRepository("postgresql://localhost/test")
    work = Work(id=None, title="New Novel", title_translated=None)
    result = repo.create(work)
    assert result.id == 1
    assert result.title == "New Novel"


@patch("database.repositories.book_repository.ConnectionPool")
def test_get_volumes(mock_pool_class, mock_pool, mock_connection):
    mock_pool_class.return_value = mock_pool
    mock_pool.connection.return_value.__enter__ = MagicMock(
        return_value=mock_connection[0]
    )
    mock_connection[1].fetchall.return_value = [
        (1, 1, 1, "Vol 1", None, None, None, None),
        (2, 1, 2, "Vol 2", None, None, None, None),
    ]
    repo = BookRepository("postgresql://localhost/test")
    result = repo.get_volumes(1)
    assert len(result) == 2
    assert result[0].volume_number == 1
    assert result[1].volume_number == 2


@patch("database.repositories.book_repository.ConnectionPool")
def test_find_by_title_exact(mock_pool_class, mock_pool, mock_connection):
    mock_pool_class.return_value = mock_pool
    mock_pool.connection.return_value.__enter__ = MagicMock(
        return_value=mock_connection[0]
    )
    mock_connection[1].fetchall.return_value = [
        (1, "Test Novel", None, "en", "es", None, None, None)
    ]
    repo = BookRepository("postgresql://localhost/test")
    result = repo.find_by_title("Test Novel", fuzzy=False)
    assert len(result) == 1
    assert result[0].title == "Test Novel"
