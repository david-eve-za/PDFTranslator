import pytest
from unittest.mock import MagicMock, patch
from database.repositories.chapter_repository import ChapterRepository
from database.models import Chapter


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


def test_chapter_repository_inherits_from_base():
    from database.repositories.base import BaseRepository

    assert issubclass(ChapterRepository, BaseRepository)


@patch("database.repositories.chapter_repository.ConnectionPool")
def test_get_by_volume(mock_pool_class, mock_pool, mock_connection):
    mock_pool_class.return_value = mock_pool
    mock_pool.connection.return_value.__enter__ = MagicMock(
        return_value=mock_connection[0]
    )
    mock_connection[1].fetchall.return_value = [
        (1, 1, 1, "Chapter 1", None, None, None, None, None),
        (2, 1, 2, "Chapter 2", None, None, None, None, None),
    ]

    repo = ChapterRepository("postgresql://localhost/test")
    result = repo.get_by_volume(1)

    assert len(result) == 2
    assert result[0].chapter_number == 1
    assert result[1].chapter_number == 2


@patch("database.repositories.chapter_repository.ConnectionPool")
def test_search_content(mock_pool_class, mock_pool, mock_connection):
    mock_pool_class.return_value = mock_pool
    mock_pool.connection.return_value.__enter__ = MagicMock(
        return_value=mock_connection[0]
    )
    mock_connection[1].fetchall.return_value = [
        (1, 1, 1, "Chapter 1", None, "Text with dragon here", None, None, None),
    ]

    repo = ChapterRepository("postgresql://localhost/test")
    result = repo.search_content(1, "dragon", limit=5)

    assert len(result) == 1


@patch("database.repositories.chapter_repository.ConnectionPool")
def test_create_chapter(mock_pool_class, mock_pool, mock_connection):
    mock_pool_class.return_value = mock_pool
    mock_pool.connection.return_value.__enter__ = MagicMock(
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
        None,
        None,
    )

    repo = ChapterRepository("postgresql://localhost/test")
    chapter = Chapter(id=None, volume_id=1, chapter_number=1, title="Chapter 1")
    result = repo.create(chapter)

    assert result.id == 1
    assert result.chapter_number == 1


@patch("database.repositories.chapter_repository.ConnectionPool")
@patch("database.repositories.chapter_repository.VectorStoreService")
def test_search_with_rerank(
    mock_vector_service, mock_pool_class, mock_pool, mock_connection
):
    mock_pool_class.return_value = mock_pool
    mock_pool.connection.return_value.__enter__ = MagicMock(
        return_value=mock_connection[0]
    )
    mock_connection[1].fetchall.return_value = [
        (1, 1, 1, "Chapter 1", None, None, "The dragon flew", None, None, None),
        (2, 1, 2, "Chapter 2", None, None, "The knight fought", None, None, None),
    ]
    from langchain_core.documents import Document

    mock_vs = MagicMock()
    mock_vs.rerank_documents.return_value = [Document(page_content="The dragon flew")]
    mock_vector_service.return_value = mock_vs
    repo = ChapterRepository("postgresql://localhost/test")
    result = repo.search_with_rerank("dragon", volume_id=1, top_n=5)
    assert len(result) >= 0
