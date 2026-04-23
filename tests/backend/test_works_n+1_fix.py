"""Tests for works.py N+1 query fix."""
from unittest.mock import MagicMock, call

from pdftranslator.backend.api.routes.works import _work_to_response


def test_work_to_response_reuses_chapter_repo():
    mock_volume_repo = MagicMock()
    mock_chapter_repo = MagicMock()

    mock_work = MagicMock()
    mock_work.id = 1
    mock_work.title = "Test Book"
    mock_work.title_translated = None
    mock_work.author = "Author"
    mock_work.source_lang = "en"
    mock_work.target_lang = "es"
    mock_work.created_at = None
    mock_work.updated_at = None

    vol1 = MagicMock()
    vol1.id = 10
    vol1.volume_number = 1
    vol2 = MagicMock()
    vol2.id = 20
    vol2.volume_number = 2

    mock_volume_repo.get_by_work_id.return_value = [vol1, vol2]

    ch1 = MagicMock()
    ch1.translated_text = "translated"
    ch2 = MagicMock()
    ch2.translated_text = None

    mock_chapter_repo.get_by_volume.side_effect = [[ch1], [ch2]]

    result = _work_to_response(mock_work, mock_volume_repo, mock_chapter_repo)

    assert result["total_chapters"] == 2
    assert result["translated_chapters"] == 1
    assert mock_chapter_repo.get_by_volume.call_count == 2
    mock_chapter_repo.get_by_volume.assert_any_call(10)
    mock_chapter_repo.get_by_volume.assert_any_call(20)


def test_work_to_response_no_database_pool_in_function():
    import inspect
    from pdftranslator.backend.api.routes.works import _work_to_response

    source = inspect.getsource(_work_to_response)
    assert "DatabasePool.get_instance()" not in source
