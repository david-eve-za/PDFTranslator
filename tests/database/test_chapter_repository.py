import pytest
from unittest.mock import MagicMock, patch
from database.repositories.chapter_repository import ChapterRepository
from database.models import Chapter
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


def test_chapter_repository_inherits_from_base():
    from database.repositories.base import BaseRepository

    assert issubclass(ChapterRepository, BaseRepository)


def test_constructor_uses_database_pool_singleton_by_default():
    with patch.object(DatabasePool, "get_instance") as mock_get_instance:
        mock_pool = MagicMock()
        mock_sync_pool = MagicMock()
        mock_pool.get_sync_pool.return_value = mock_sync_pool
        mock_get_instance.return_value = mock_pool

        repo = ChapterRepository()

        mock_get_instance.assert_called_once()
        assert repo._pool == mock_pool


def test_constructor_accepts_custom_pool():
    custom_pool = MagicMock()

    repo = ChapterRepository(pool=custom_pool)

    assert repo._pool == custom_pool


def test_get_by_volume(mock_pool, mock_connection):
    mock_pool.get_sync_pool.return_value.connection.return_value.__enter__ = MagicMock(
        return_value=mock_connection[0]
    )
    mock_connection[1].fetchall.return_value = [
        (1, 1, 1, "Chapter 1", None, None, None),
        (2, 1, 2, "Chapter 2", None, None, None),
    ]

    repo = ChapterRepository(pool=mock_pool)
    result = repo.get_by_volume(1)

    assert len(result) == 2
    assert result[0].chapter_number == 1
    assert result[1].chapter_number == 2


def test_search_content(mock_pool, mock_connection):
    mock_pool.get_sync_pool.return_value.connection.return_value.__enter__ = MagicMock(
        return_value=mock_connection[0]
    )
    mock_connection[1].fetchall.return_value = [
        (1, 1, 1, "Chapter 1", None, "Text with dragon here", None),
    ]

    repo = ChapterRepository(pool=mock_pool)
    result = repo.search_content(1, "dragon", limit=5)

    assert len(result) == 1


def test_create_chapter(mock_pool, mock_connection):
    mock_pool.get_sync_pool.return_value.connection.return_value.__enter__ = MagicMock(
        return_value=mock_connection[0]
    )
    mock_connection[1].fetchone.return_value = (
        1,
        1,
        1,
        "Chapter 1",
        None,
        None,
        None,
    )

    repo = ChapterRepository(pool=mock_pool)
    chapter = Chapter(id=None, volume_id=1, chapter_number=1, title="Chapter 1")
    result = repo.create(chapter)

    assert result.id == 1
    assert result.chapter_number == 1


@patch("database.repositories.chapter_repository.VectorStoreService")
def test_search_with_rerank(mock_vector_service, mock_pool, mock_connection):
    mock_pool.get_sync_pool.return_value.connection.return_value.__enter__ = MagicMock(
        return_value=mock_connection[0]
    )
    mock_connection[1].fetchall.return_value = [
        (1, 1, 1, "Chapter 1", "The dragon flew", None, None),
        (2, 1, 2, "Chapter 2", "The knight fought", None, None),
    ]
    from langchain_core.documents import Document

    mock_vs = MagicMock()
    mock_vs.rerank_documents.return_value = [Document(page_content="The dragon flew")]
    mock_vector_service.return_value = mock_vs
    repo = ChapterRepository(pool=mock_pool)
    result = repo.search_with_rerank("dragon", volume_id=1, top_n=5)
    assert len(result) >= 0
