"""Tests for translation API routes."""

from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from pdftranslator.backend.main import app

client = TestClient(app)


def test_list_translation_jobs():
    with patch(
        "pdftranslator.backend.api.routes.translation.TranslationJobRepository"
    ) as mock_repo_cls:
        mock_repo = MagicMock()
        mock_repo_cls.return_value = mock_repo
        mock_repo.get_all.return_value = []
        response = client.get("/api/translate")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data


def test_start_translation_missing_work():
    response = client.post(
        "/api/translate",
        json={"scope": "all_book"},
    )
    assert response.status_code == 422


def test_start_translation_invalid_scope():
    response = client.post(
        "/api/translate",
        json={"work_id": 1, "scope": "invalid_scope"},
    )
    assert response.status_code == 422


def test_get_translation_job_not_found():
    with patch(
        "pdftranslator.backend.api.routes.translation.TranslationJobRepository"
    ) as mock_repo_cls:
        mock_repo = MagicMock()
        mock_repo_cls.return_value = mock_repo
        mock_repo.get_by_id.return_value = None
        response = client.get("/api/translate/999")
        assert response.status_code == 404


def test_start_translation_creates_job():
    from pdftranslator.database.repositories.translation_job_repository import TranslationJob

    mock_job = TranslationJob(
        id=1, work_id=1, scope="all_book",
        source_lang="en", target_lang="es",
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
            json={"work_id": 1, "scope": "all_book"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "pending"


def test_get_translation_job_returns_status():
    from pdftranslator.database.repositories.translation_job_repository import TranslationJob
    from datetime import datetime

    mock_job = TranslationJob(
        id=1, work_id=1, scope="all_book",
        source_lang="en", target_lang="es",
        status="in_progress", total_chapters=5,
        completed_chapters=2, success_count=2,
        created_at=datetime(2026, 1, 1), updated_at=datetime(2026, 1, 1),
    )

    with patch(
        "pdftranslator.backend.api.routes.translation.TranslationJobRepository"
    ) as mock_repo_cls:
        mock_repo = MagicMock()
        mock_repo_cls.return_value = mock_repo
        mock_repo.get_by_id.return_value = mock_job
        response = client.get("/api/translate/1")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "in_progress"
        assert data["completed_chapters"] == 2
