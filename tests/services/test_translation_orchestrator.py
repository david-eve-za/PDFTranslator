"""Tests for translation orchestrator service."""

from unittest.mock import MagicMock, patch
from pdftranslator.services.translation_orchestrator import (
    TranslationOrchestrator,
    TranslationProgress,
    _get_chapter_sort_key,
    _format_chapter_display,
)
from pdftranslator.core.models.work import Chapter, Volume
from pdftranslator.database.repositories.translation_job_repository import TranslationJob


def test_get_chapter_sort_key_numbered():
    chapter = Chapter(chapter_number=5, title="The Battle")
    assert _get_chapter_sort_key(chapter) == (1, 5)


def test_get_chapter_sort_key_prologue():
    chapter = Chapter(chapter_number=None, title="Prologue")
    assert _get_chapter_sort_key(chapter) == (0, 0)


def test_get_chapter_sort_key_epilogue():
    chapter = Chapter(chapter_number=None, title="Epilogue")
    assert _get_chapter_sort_key(chapter) == (2, 0)


def test_get_chapter_sort_key_unknown_unnumbered():
    chapter = Chapter(chapter_number=None, title="Interlude")
    assert _get_chapter_sort_key(chapter) == (1, 0)


def test_format_chapter_display_numbered():
    chapter = Chapter(chapter_number=5, title="The Battle")
    assert _format_chapter_display(chapter) == "Chapter 5 - The Battle"


def test_format_chapter_display_numbered_no_title():
    chapter = Chapter(chapter_number=3, title=None)
    assert _format_chapter_display(chapter) == "Chapter 3"


def test_format_chapter_display_prologue():
    chapter = Chapter(chapter_number=None, title="Prologue")
    assert _format_chapter_display(chapter) == "Prologue"


def test_translation_progress_dataclass():
    progress = TranslationProgress(
        completed_chapters=3,
        total_chapters=15,
        current_chapter="Chapter 5 - The Battle",
        chapter_id=42,
        chapter_title="Chapter 5",
        chapter_status="success",
    )
    assert progress.completed_chapters == 3
    assert progress.total_chapters == 15
    assert progress.chapter_status == "success"


def test_translation_progress_defaults():
    progress = TranslationProgress(
        completed_chapters=0,
        total_chapters=0,
    )
    assert progress.current_chapter is None
    assert progress.chapter_id is None
    assert progress.chapter_title is None
    assert progress.chapter_status is None


def test_orchestrator_translate_chapter_skips_no_original_text():
    mock_chapter_repo = MagicMock()
    mock_glossary_repo = MagicMock()
    mock_chapter = Chapter(id=1, chapter_number=1, title="Ch 1", original_text=None)
    mock_chapter_repo.get_by_id.return_value = mock_chapter

    progress_calls = []
    def on_progress(p: TranslationProgress):
        progress_calls.append(p)

    orchestrator = TranslationOrchestrator(
        chapter_repo=mock_chapter_repo,
        glossary_repo=mock_glossary_repo,
    )
    result = orchestrator.translate_chapter(
        chapter_id=1,
        source_lang="en",
        target_lang="es",
        on_progress=on_progress,
    )
    assert result is False


def test_orchestrator_translate_chapter_no_id():
    mock_chapter_repo = MagicMock()
    mock_glossary_repo = MagicMock()
    mock_chapter = Chapter(id=None, chapter_number=1, title="Ch 1", original_text="Hello")
    mock_chapter_repo.get_by_id.return_value = mock_chapter

    orchestrator = TranslationOrchestrator(
        chapter_repo=mock_chapter_repo,
        glossary_repo=mock_glossary_repo,
    )
    result = orchestrator.translate_chapter(
        chapter_id=1,
        source_lang="en",
        target_lang="es",
    )
    assert result is False


def test_orchestrator_translate_volume():
    mock_chapter_repo = MagicMock()
    mock_glossary_repo = MagicMock()
    chapters = [
        Chapter(id=1, chapter_number=1, title="Ch 1", original_text="Hello"),
        Chapter(id=2, chapter_number=2, title="Ch 2", original_text="World"),
    ]
    mock_chapter_repo.get_by_volume.return_value = chapters

    with patch.object(
        TranslationOrchestrator, "translate_chapter", return_value=True
    ) as mock_translate:
        orchestrator = TranslationOrchestrator(
            chapter_repo=mock_chapter_repo,
            glossary_repo=mock_glossary_repo,
        )
        success, failure = orchestrator.translate_volume(
            volume_id=1,
            source_lang="en",
            target_lang="es",
            skip_translated=False,
        )
        assert success == 2
        assert failure == 0
        assert mock_translate.call_count == 2


def test_orchestrator_translate_volume_skip_translated():
    mock_chapter_repo = MagicMock()
    mock_glossary_repo = MagicMock()
    chapters = [
        Chapter(id=1, chapter_number=1, title="Ch 1", original_text="Hello", translated_text="Hola"),
        Chapter(id=2, chapter_number=2, title="Ch 2", original_text="World"),
    ]
    mock_chapter_repo.get_by_volume.return_value = chapters

    with patch.object(
        TranslationOrchestrator, "translate_chapter", return_value=True
    ) as mock_translate:
        orchestrator = TranslationOrchestrator(
            chapter_repo=mock_chapter_repo,
            glossary_repo=mock_glossary_repo,
        )
        success, failure = orchestrator.translate_volume(
            volume_id=1,
            source_lang="en",
            target_lang="es",
            skip_translated=True,
        )
        assert success == 1
        assert failure == 0
        assert mock_translate.call_count == 1


def test_orchestrator_translate_book():
    mock_chapter_repo = MagicMock()
    mock_glossary_repo = MagicMock()
    mock_volume_repo = MagicMock()

    volumes = [
        Volume(id=1, work_id=1, volume_number=1),
        Volume(id=2, work_id=1, volume_number=2),
    ]
    mock_volume_repo.get_by_work_id.return_value = volumes

    with patch.object(
        TranslationOrchestrator, "translate_volume", return_value=(3, 1)
    ) as mock_translate:
        orchestrator = TranslationOrchestrator(
            chapter_repo=mock_chapter_repo,
            glossary_repo=mock_glossary_repo,
            volume_repo=mock_volume_repo,
        )
        success, failure = orchestrator.translate_book(
            work_id=1,
            source_lang="en",
            target_lang="es",
            skip_translated=True,
        )
        assert success == 6
        assert failure == 2
        assert mock_translate.call_count == 2


def test_orchestrator_execute_job_all_book():
    mock_chapter_repo = MagicMock()
    mock_glossary_repo = MagicMock()
    mock_volume_repo = MagicMock()
    mock_job_repo = MagicMock()

    job = TranslationJob(id=1, work_id=1, scope="all_book", source_lang="en", target_lang="es")
    mock_job_repo.get_by_id.return_value = job

    with patch.object(
        TranslationOrchestrator, "translate_book", return_value=(5, 0)
    ):
        orchestrator = TranslationOrchestrator(
            chapter_repo=mock_chapter_repo,
            glossary_repo=mock_glossary_repo,
            volume_repo=mock_volume_repo,
            job_repo=mock_job_repo,
        )
        orchestrator.execute_job(job)
        assert mock_job_repo.update.call_count >= 2
        final_job = mock_job_repo.update.call_args[0][0]
        assert final_job.status == "completed"
        assert final_job.success_count == 5


def test_orchestrator_execute_job_single_chapter():
    mock_chapter_repo = MagicMock()
    mock_glossary_repo = MagicMock()
    mock_job_repo = MagicMock()

    job = TranslationJob(
        id=1, work_id=1, scope="single_chapter", chapter_id=5,
        source_lang="en", target_lang="es",
    )
    mock_job_repo.get_by_id.return_value = job

    with patch.object(
        TranslationOrchestrator, "translate_chapter", return_value=True
    ):
        orchestrator = TranslationOrchestrator(
            chapter_repo=mock_chapter_repo,
            glossary_repo=mock_glossary_repo,
            job_repo=mock_job_repo,
        )
        orchestrator.execute_job(job)
        final_job = mock_job_repo.update.call_args[0][0]
        assert final_job.status == "completed"
        assert final_job.success_count == 1
