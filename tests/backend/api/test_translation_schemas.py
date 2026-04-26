"""Tests for translation API schemas."""

from pdftranslator.backend.api.models.schemas import (
    TranslationStartRequest,
    TranslationJobResponse,
    TranslationJobListResponse,
)


def test_translation_start_request_defaults():
    req = TranslationStartRequest(work_id=1, scope="all_book")
    assert req.work_id == 1
    assert req.scope == "all_book"
    assert req.volume_id is None
    assert req.chapter_id is None
    assert req.source_lang == "en"
    assert req.target_lang == "es"
    assert req.skip_translated is True
    assert req.dry_run is False


def test_translation_start_request_with_volume():
    req = TranslationStartRequest(
        work_id=1, scope="all_volume", volume_id=3,
        source_lang="ja", target_lang="es",
    )
    assert req.volume_id == 3
    assert req.source_lang == "ja"


def test_translation_job_response():
    resp = TranslationJobResponse(
        id=1, work_id=1, scope="all_book",
        source_lang="en", target_lang="es",
        skip_translated=True, dry_run=False,
        status="in_progress", total_chapters=10,
        completed_chapters=5, success_count=5,
        failure_count=0, current_chapter_info="Chapter 6",
    )
    assert resp.id == 1
    assert resp.status == "in_progress"
    assert resp.completed_chapters == 5


def test_translation_job_list_response():
    job = TranslationJobResponse(
        id=1, work_id=1, scope="all_book",
        source_lang="en", target_lang="es",
        skip_translated=True, dry_run=False,
        status="completed", total_chapters=5,
        completed_chapters=5, success_count=5,
        failure_count=0,
    )
    resp = TranslationJobListResponse(items=[job], total=1)
    assert len(resp.items) == 1
    assert resp.total == 1
