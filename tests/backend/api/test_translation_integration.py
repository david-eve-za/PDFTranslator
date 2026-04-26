"""Integration tests for translation API lifecycle."""

from unittest.mock import MagicMock, patch
from datetime import datetime
from fastapi.testclient import TestClient

from pdftranslator.backend.main import app
from pdftranslator.database.repositories.translation_job_repository import TranslationJob

client = TestClient(app)


def test_full_translation_lifecycle():
    """Test: create job -> get status -> list jobs."""
    mock_job_pending = TranslationJob(
        id=1, work_id=1, scope="all_book",
        source_lang="en", target_lang="es",
        status="pending",
        created_at=datetime(2026, 1, 1), updated_at=datetime(2026, 1, 1),
    )
    mock_job_in_progress = TranslationJob(
        id=1, work_id=1, scope="all_book",
        source_lang="en", target_lang="es",
        status="in_progress", total_chapters=5, completed_chapters=2,
        current_chapter_info="Chapter 3",
        created_at=datetime(2026, 1, 1), updated_at=datetime(2026, 1, 1),
    )
    mock_job_completed = TranslationJob(
        id=1, work_id=1, scope="all_book",
        source_lang="en", target_lang="es",
        status="completed", total_chapters=5, completed_chapters=5,
        success_count=5,
        created_at=datetime(2026, 1, 1), updated_at=datetime(2026, 1, 1),
    )

    with patch(
        "pdftranslator.backend.api.routes.translation.TranslationJobRepository"
    ) as mock_repo_cls:
        mock_repo = MagicMock()
        mock_repo_cls.return_value = mock_repo

        mock_repo.create.return_value = mock_job_pending
        mock_repo.get_by_id.return_value = mock_job_pending
        mock_repo.get_all.return_value = [mock_job_completed]

        with patch(
            "pdftranslator.backend.api.routes.translation.asyncio"
        ) as mock_asyncio:
            mock_asyncio.create_task.return_value = None
            mock_asyncio.Queue.return_value = MagicMock()

            start_response = client.post(
                "/api/translate",
                json={"work_id": 1, "scope": "all_book"},
            )
            assert start_response.status_code == 200
            assert start_response.json()["status"] == "pending"

            mock_repo.get_by_id.return_value = mock_job_in_progress
            status_response = client.get("/api/translate/1")
            assert status_response.status_code == 200
            data = status_response.json()
            assert data["status"] == "in_progress"
            assert data["completed_chapters"] == 2
            assert data["current_chapter_info"] == "Chapter 3"

            list_response = client.get("/api/translate")
            assert list_response.status_code == 200
            list_data = list_response.json()
            assert list_data["total"] >= 1


def test_translation_job_not_found():
    """Test getting a non-existent job returns 404."""
    with patch(
        "pdftranslator.backend.api.routes.translation.TranslationJobRepository"
    ) as mock_repo_cls:
        mock_repo = MagicMock()
        mock_repo_cls.return_value = mock_repo
        mock_repo.get_by_id.return_value = None

        response = client.get("/api/translate/9999")
        assert response.status_code == 404


def test_translation_validation_errors():
    """Test that invalid requests return 422."""
    response = client.post("/api/translate", json={})
    assert response.status_code == 422

    response = client.post("/api/translate", json={"work_id": 1, "scope": "invalid"})
    assert response.status_code == 422

    response = client.post("/api/translate", json={"scope": "all_book"})
    assert response.status_code == 422


def test_sse_returns_completed_job_immediately():
    """Test SSE endpoint for already completed job."""
    mock_job = TranslationJob(
        id=2, work_id=1, scope="all_volume", volume_id=3,
        source_lang="en", target_lang="es",
        status="completed", total_chapters=3, completed_chapters=3,
        success_count=3,
        created_at=datetime(2026, 1, 1), updated_at=datetime(2026, 1, 1),
    )

    with patch(
        "pdftranslator.backend.api.routes.translation.TranslationJobRepository"
    ) as mock_repo_cls:
        mock_repo = MagicMock()
        mock_repo_cls.return_value = mock_repo
        mock_repo.get_by_id.return_value = mock_job

        response = client.get("/api/translate/2/stream")
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")


def test_volume_scope_requires_volume_id():
    """Test that volume scope translation can be started."""
    mock_job = TranslationJob(
        id=3, work_id=1, scope="all_volume", volume_id=2,
        source_lang="en", target_lang="es",
        created_at=datetime(2026, 1, 1), updated_at=datetime(2026, 1, 1),
    )

    with patch(
        "pdftranslator.backend.api.routes.translation.TranslationJobRepository"
    ) as mock_repo_cls, patch(
        "pdftranslator.backend.api.routes.translation.asyncio"
    ) as mock_asyncio:
        mock_repo = MagicMock()
        mock_repo_cls.return_value = mock_repo
        mock_repo.create.return_value = mock_job
        mock_asyncio.create_task.return_value = None
        mock_asyncio.Queue.return_value = MagicMock()

        response = client.post(
            "/api/translate",
            json={"work_id": 1, "scope": "all_volume", "volume_id": 2},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "pending"


def test_single_chapter_scope():
    """Test that single chapter translation can be started."""
    mock_job = TranslationJob(
        id=4, work_id=1, scope="single_chapter", chapter_id=10,
        source_lang="en", target_lang="es",
        created_at=datetime(2026, 1, 1), updated_at=datetime(2026, 1, 1),
    )

    with patch(
        "pdftranslator.backend.api.routes.translation.TranslationJobRepository"
    ) as mock_repo_cls, patch(
        "pdftranslator.backend.api.routes.translation.asyncio"
    ) as mock_asyncio:
        mock_repo = MagicMock()
        mock_repo_cls.return_value = mock_repo
        mock_repo.create.return_value = mock_job
        mock_asyncio.create_task.return_value = None
        mock_asyncio.Queue.return_value = MagicMock()

        response = client.post(
            "/api/translate",
            json={"work_id": 1, "scope": "single_chapter", "chapter_id": 10},
        )
        assert response.status_code == 200


def test_skip_translated_and_dry_run_options():
    """Test that skip_translated and dry_run options are accepted."""
    mock_job = TranslationJob(
        id=5, work_id=1, scope="all_book",
        source_lang="ja", target_lang="es",
        skip_translated=False, dry_run=True,
        created_at=datetime(2026, 1, 1), updated_at=datetime(2026, 1, 1),
    )

    with patch(
        "pdftranslator.backend.api.routes.translation.TranslationJobRepository"
    ) as mock_repo_cls, patch(
        "pdftranslator.backend.api.routes.translation.asyncio"
    ) as mock_asyncio:
        mock_repo = MagicMock()
        mock_repo_cls.return_value = mock_repo
        mock_repo.create.return_value = mock_job
        mock_asyncio.create_task.return_value = None
        mock_asyncio.Queue.return_value = MagicMock()

        response = client.post(
            "/api/translate",
            json={
                "work_id": 1,
                "scope": "all_book",
                "source_lang": "ja",
                "target_lang": "es",
                "skip_translated": False,
                "dry_run": True,
            },
        )
        assert response.status_code == 200
