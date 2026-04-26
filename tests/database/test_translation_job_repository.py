"""Tests for translation job repository."""

from unittest.mock import MagicMock
from pdftranslator.database.repositories.translation_job_repository import (
    TranslationJobRepository,
    TranslationJob,
)


def test_translation_job_dataclass_defaults():
    job = TranslationJob()
    assert job.id is None
    assert job.work_id == 0
    assert job.scope == ""
    assert job.volume_id is None
    assert job.chapter_id is None
    assert job.source_lang == "en"
    assert job.target_lang == "es"
    assert job.skip_translated is True
    assert job.dry_run is False
    assert job.status == "pending"
    assert job.total_chapters == 0
    assert job.completed_chapters == 0
    assert job.success_count == 0
    assert job.failure_count == 0
    assert job.current_chapter_info is None
    assert job.error_message is None


def test_translation_job_repository_create():
    mock_pool = MagicMock()
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_pool.get_sync_pool.return_value.connection.return_value.__enter__ = MagicMock(
        return_value=mock_conn
    )
    mock_pool.get_sync_pool.return_value.connection.return_value.__exit__ = MagicMock(
        return_value=False
    )
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    mock_cur.fetchone.return_value = (
        1, 1, "all_book", None, None, "en", "es", True, False,
        "pending", 0, 0, 0, 0, None, None, "2026-01-01", "2026-01-01",
    )

    repo = TranslationJobRepository(pool=mock_pool)
    job = TranslationJob(work_id=1, scope="all_book", source_lang="en", target_lang="es")
    result = repo.create(job)
    assert result.id == 1
    assert result.scope == "all_book"


def test_translation_job_repository_get_by_id():
    mock_pool = MagicMock()
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_pool.get_sync_pool.return_value.connection.return_value.__enter__ = MagicMock(
        return_value=mock_conn
    )
    mock_pool.get_sync_pool.return_value.connection.return_value.__exit__ = MagicMock(
        return_value=False
    )
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    mock_cur.fetchone.return_value = (
        1, 1, "all_book", None, None, "en", "es", True, False,
        "in_progress", 5, 2, 2, 0, "Chapter 3 - The Battle", None,
        "2026-01-01", "2026-01-01",
    )

    repo = TranslationJobRepository(pool=mock_pool)
    result = repo.get_by_id(1)
    assert result is not None
    assert result.id == 1
    assert result.status == "in_progress"
    assert result.completed_chapters == 2
    assert result.current_chapter_info == "Chapter 3 - The Battle"


def test_translation_job_repository_get_by_id_not_found():
    mock_pool = MagicMock()
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_pool.get_sync_pool.return_value.connection.return_value.__enter__ = MagicMock(
        return_value=mock_conn
    )
    mock_pool.get_sync_pool.return_value.connection.return_value.__exit__ = MagicMock(
        return_value=False
    )
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    mock_cur.fetchone.return_value = None

    repo = TranslationJobRepository(pool=mock_pool)
    result = repo.get_by_id(999)
    assert result is None


def test_translation_job_repository_update_status():
    mock_pool = MagicMock()
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_pool.get_sync_pool.return_value.connection.return_value.__enter__ = MagicMock(
        return_value=mock_conn
    )
    mock_pool.get_sync_pool.return_value.connection.return_value.__exit__ = MagicMock(
        return_value=False
    )
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    mock_cur.fetchone.return_value = (
        1, 1, "all_book", None, None, "en", "es", True, False,
        "in_progress", 5, 3, 3, 0, "Chapter 4", None,
        "2026-01-01", "2026-01-01",
    )

    repo = TranslationJobRepository(pool=mock_pool)
    job = TranslationJob(
        id=1, work_id=1, scope="all_book", source_lang="en", target_lang="es",
        status="in_progress", total_chapters=5, completed_chapters=3,
        success_count=3, current_chapter_info="Chapter 4",
    )
    result = repo.update(job)
    assert result is not None
    assert result.completed_chapters == 3


def test_translation_job_repository_list_by_work():
    mock_pool = MagicMock()
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_pool.get_sync_pool.return_value.connection.return_value.__enter__ = MagicMock(
        return_value=mock_conn
    )
    mock_pool.get_sync_pool.return_value.connection.return_value.__exit__ = MagicMock(
        return_value=False
    )
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    mock_cur.fetchall.return_value = [
        (
            1, 1, "all_book", None, None, "en", "es", True, False,
            "completed", 5, 5, 5, 0, None, None, "2026-01-01", "2026-01-01",
        ),
        (
            2, 1, "all_volume", 3, None, "en", "es", True, False,
            "in_progress", 3, 1, 1, 0, "Chapter 2", None, "2026-01-02", "2026-01-02",
        ),
    ]

    repo = TranslationJobRepository(pool=mock_pool)
    results = repo.list_by_work(1)
    assert len(results) == 2
