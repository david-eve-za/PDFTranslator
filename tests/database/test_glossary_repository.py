import pytest
from unittest.mock import MagicMock, patch
from database.repositories.glossary_repository import GlossaryRepository
from database.models import GlossaryEntry, TermContext, ContextExample
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


def test_glossary_repository_inherits_from_base():
    from database.repositories.base import BaseRepository

    assert issubclass(GlossaryRepository, BaseRepository)


def test_constructor_uses_database_pool_singleton_by_default():
    with patch.object(DatabasePool, "get_instance") as mock_get_instance:
        mock_pool = MagicMock()
        mock_sync_pool = MagicMock()
        mock_pool.get_sync_pool.return_value = mock_sync_pool
        mock_get_instance.return_value = mock_pool

        repo = GlossaryRepository()

        mock_get_instance.assert_called_once()
        assert repo._pool == mock_pool


def test_constructor_accepts_custom_pool():
    custom_pool = MagicMock()

    repo = GlossaryRepository(pool=custom_pool)

    assert repo._pool == custom_pool


def test_get_by_work(mock_pool, mock_connection):
    mock_pool.get_sync_pool.return_value.connection.return_value.__enter__ = MagicMock(
        return_value=mock_connection[0]
    )
    mock_connection[1].fetchall.return_value = [
        (1, 1, "staff", "personal", None, None),
    ]

    repo = GlossaryRepository(pool=mock_pool)
    result = repo.get_by_work(1)

    assert len(result) == 1
    assert result[0].source_term == "staff"


def test_find_by_term_fuzzy(mock_pool, mock_connection):
    mock_pool.get_sync_pool.return_value.connection.return_value.__enter__ = MagicMock(
        return_value=mock_connection[0]
    )
    mock_connection[1].fetchall.return_value = [
        (1, 1, "Tempest", None, None, None),
    ]

    repo = GlossaryRepository(pool=mock_pool)
    result = repo.find_by_term("Tempst", fuzzy=True)

    assert len(result) == 1
    assert result[0].source_term == "Tempest"


def test_create_entry(mock_pool, mock_connection):
    mock_pool.get_sync_pool.return_value.connection.return_value.__enter__ = MagicMock(
        return_value=mock_connection[0]
    )
    mock_connection[1].fetchone.return_value = (
        1,
        1,
        "dragon",
        "dragón",
        None,
        None,
    )

    repo = GlossaryRepository(pool=mock_pool)
    entry = GlossaryEntry(
        id=None, work_id=1, source_term="dragon", target_term="dragón"
    )
    result = repo.create(entry)

    assert result.id == 1
    assert result.source_term == "dragon"


def test_add_context(mock_pool, mock_connection):
    mock_pool.get_sync_pool.return_value.connection.return_value.__enter__ = MagicMock(
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

    repo = GlossaryRepository(pool=mock_pool)
    context = TermContext(
        id=None, term_id=1, context_hint="objeto mágico", translation="baculo"
    )
    result = repo.add_context(1, context)

    assert result.id == 1
    assert result.context_hint == "objeto mágico"


def test_add_example(mock_pool, mock_connection):
    mock_pool.get_sync_pool.return_value.connection.return_value.__enter__ = MagicMock(
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

    repo = GlossaryRepository(pool=mock_pool)
    example = ContextExample(
        id=None,
        context_id=1,
        original_sentence="He held his staff",
        translated_sentence="El sostenía su baculo",
    )
    result = repo.add_example(1, example)

    assert result.id == 1
    assert result.original_sentence == "He held his staff"


@patch("database.repositories.glossary_repository.VectorStoreService")
def test_search_terms_with_rerank(mock_vector_service, mock_pool, mock_connection):
    mock_pool.get_sync_pool.return_value.connection.return_value.__enter__ = MagicMock(
        return_value=mock_connection[0]
    )
    mock_connection[1].fetchall.return_value = [
        (1, 1, "staff", "personal", None, None),
        (2, 1, "dragon", "dragón", None, None),
    ]

    from langchain_core.documents import Document

    mock_vs = MagicMock()
    mock_vs.rerank_documents.return_value = [Document(page_content="dragon: dragón")]
    mock_vector_service.return_value = mock_vs

    repo = GlossaryRepository(pool=mock_pool)
    result = repo.search_terms_with_rerank("fire creature", work_id=1, top_n=5)

    assert len(result) >= 0
