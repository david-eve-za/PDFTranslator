import pytest
from unittest.mock import MagicMock, patch
from database.repositories.glossary_repository import GlossaryRepository
from database.models import GlossaryEntry, TermContext, ContextExample


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


def test_glossary_repository_inherits_from_base():
    from database.repositories.base import BaseRepository

    assert issubclass(GlossaryRepository, BaseRepository)


@patch("database.repositories.glossary_repository.ConnectionPool")
def test_get_by_work(mock_pool_class, mock_pool, mock_connection):
    mock_pool_class.return_value = mock_pool
    mock_pool.connection.return_value.__enter__ = MagicMock(
        return_value=mock_connection[0]
    )
    mock_connection[1].fetchall.return_value = [
        (1, 1, "staff", "personal", None, False, None, None),
    ]

    repo = GlossaryRepository("postgresql://localhost/test")
    result = repo.get_by_work(1)

    assert len(result) == 1
    assert result[0].term == "staff"


@patch("database.repositories.glossary_repository.ConnectionPool")
def test_find_by_term_fuzzy(mock_pool_class, mock_pool, mock_connection):
    mock_pool_class.return_value = mock_pool
    mock_pool.connection.return_value.__enter__ = MagicMock(
        return_value=mock_connection[0]
    )
    mock_connection[1].fetchall.return_value = [
        (1, 1, "Tempest", None, None, True, None, None),
    ]

    repo = GlossaryRepository("postgresql://localhost/test")
    result = repo.find_by_term("Tempst", fuzzy=True)

    assert len(result) == 1
    assert result[0].term == "Tempest"


@patch("database.repositories.glossary_repository.ConnectionPool")
def test_create_entry(mock_pool_class, mock_pool, mock_connection):
    mock_pool_class.return_value = mock_pool
    mock_pool.connection.return_value.__enter__ = MagicMock(
        return_value=mock_connection[0]
    )
    mock_connection[1].fetchone.return_value = (
        1,
        1,
        "dragon",
        "dragón",
        None,
        False,
        None,
        None,
    )

    repo = GlossaryRepository("postgresql://localhost/test")
    entry = GlossaryEntry(id=None, work_id=1, term="dragon", translation="dragón")
    result = repo.create(entry)

    assert result.id == 1
    assert result.term == "dragon"


@patch("database.repositories.glossary_repository.ConnectionPool")
def test_add_context(mock_pool_class, mock_pool, mock_connection):
    mock_pool_class.return_value = mock_pool
    mock_pool.connection.return_value.__enter__ = MagicMock(
        return_value=mock_connection[0]
    )
    mock_connection[1].fetchone.return_value = (
        1,
        1,
        "objeto mágico",
        "baculo",
        None,
        None,
    )

    repo = GlossaryRepository("postgresql://localhost/test")
    context = TermContext(
        id=None, term_id=1, context_hint="objeto mágico", translation="baculo"
    )
    result = repo.add_context(1, context)

    assert result.id == 1
    assert result.context_hint == "objeto mágico"


@patch("database.repositories.glossary_repository.ConnectionPool")
def test_add_example(mock_pool_class, mock_pool, mock_connection):
    mock_pool_class.return_value = mock_pool
    mock_pool.connection.return_value.__enter__ = MagicMock(
        return_value=mock_connection[0]
    )
    mock_connection[1].fetchone.return_value = (
        1,
        1,
        "He held his staff",
        "El sostenía su baculo",
        None,
        None,
    )

    repo = GlossaryRepository("postgresql://localhost/test")
    example = ContextExample(
        id=None,
        context_id=1,
        original_sentence="He held his staff",
        translated_sentence="El sostenía su baculo",
    )
    result = repo.add_example(1, example)

    assert result.id == 1
    assert result.original_sentence == "He held his staff"
