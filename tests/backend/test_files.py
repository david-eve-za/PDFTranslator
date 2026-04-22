"""Tests for file upload endpoints."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from pdftranslator.backend.api.routes.files import get_file_service, router
from pdftranslator.backend.services.file_service import FileService, ProcessingResult
from pdftranslator.database.models import UploadedFile


@pytest.fixture
def mock_file_service():
    """Create a mock FileService."""
    service = MagicMock(spec=FileService)
    return service


@pytest.fixture
def app(mock_file_service):
    """Create a test FastAPI app with mocked dependencies."""
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_file_service] = lambda: mock_file_service
    yield app
    app.dependency_overrides.clear()


@pytest.fixture
def client(app):
    """Create a test client."""
    return TestClient(app)


class TestFileUpload:
    """Tests for file upload endpoint."""

    def test_upload_valid_file(self, client, mock_file_service, tmp_path):
        """Test uploading a valid PDF file."""
        test_file = tmp_path / "test - Volume 1.pdf"
        test_file.write_text("test content")

        uploaded_file = UploadedFile(
            id=1,
            filename="abc123.pdf",
            original_name="test - Volume 1.pdf",
            file_size=12,
            file_type="pdf",
            status="done",
            created_at=datetime.now(),
        )

        result = ProcessingResult(
            success=True,
            work_id=1,
            work_title="test",
            volume_id=1,
            volume_number=1,
        )

        mock_file_service.validate_file.return_value = (True, None)
        mock_file_service.save_upload_file = AsyncMock(return_value=uploaded_file)
        mock_file_service.process_file.return_value = result

        with open(test_file, "rb") as f:
            response = client.post(
                "/api/files/upload",
                files={"file": ("test - Volume 1.pdf", f, "application/pdf")},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["original_name"] == "test - Volume 1.pdf"
        assert data["work_id"] == 1
        assert data["volume_number"] == 1

    def test_upload_invalid_extension(self, client, mock_file_service):
        """Test uploading a file with invalid extension."""
        mock_file_service.validate_file.return_value = (
            False,
            "File extension '.txt' not allowed",
        )

        response = client.post(
            "/api/files/upload",
            files={"file": ("test.txt", b"content", "text/plain")},
        )

        assert response.status_code == 400
        assert "not allowed" in response.json()["detail"]

    def test_upload_file_too_large(self, client, mock_file_service):
        """Test uploading a file that exceeds size limit."""
        mock_file_service.validate_file.return_value = (
            False,
            "File size exceeds limit",
        )

        large_content = b"x" * (400 * 1024 * 1024)
        response = client.post(
            "/api/files/upload",
            files={"file": ("large.pdf", large_content, "application/pdf")},
        )

        assert response.status_code == 400


class TestFileList:
    """Tests for file listing endpoint."""

    def test_list_files_empty(self, client, mock_file_service):
        """Test listing when no files exist."""
        mock_file_service.list_files.return_value = ([], 0)

        response = client.get("/api/files/")

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_list_files_with_pagination(self, client, mock_file_service):
        """Test file listing with pagination."""
        files = [
            UploadedFile(
                id=1,
                filename="file1.pdf",
                original_name="test1.pdf",
                file_size=1000,
                file_type="pdf",
                status="done",
                created_at=datetime.now(),
            ),
        ]
        mock_file_service.list_files.return_value = (files, 1)

        response = client.get("/api/files/?page=1&page_size=20")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["total"] == 1
        assert data["page"] == 1


class TestFileGet:
    """Tests for get file endpoint."""

    def test_get_existing_file(self, client, mock_file_service):
        """Test getting an existing file."""
        uploaded_file = UploadedFile(
            id=1,
            filename="test.pdf",
            original_name="test - Volume 1.pdf",
            file_size=1000,
            file_type="pdf",
            status="done",
            work_id=1,
            volume_id=1,
            created_at=datetime.now(),
        )
        mock_file_service.get_file.return_value = uploaded_file

        response = client.get("/api/files/1")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1
        assert data["filename"] == "test.pdf"

    def test_get_nonexistent_file(self, client, mock_file_service):
        """Test getting a non-existent file."""
        mock_file_service.get_file.return_value = None

        response = client.get("/api/files/999")

        assert response.status_code == 404


class TestFileDelete:
    """Tests for delete file endpoint."""

    def test_delete_existing_file(self, client, mock_file_service):
        """Test deleting an existing file."""
        mock_file_service.delete_file.return_value = True

        response = client.delete("/api/files/1")

        assert response.status_code == 200
        assert response.json()["message"] == "File deleted"

    def test_delete_nonexistent_file(self, client, mock_file_service):
        """Test deleting a non-existent file."""
        mock_file_service.delete_file.return_value = False

        response = client.delete("/api/files/999")

        assert response.status_code == 404
