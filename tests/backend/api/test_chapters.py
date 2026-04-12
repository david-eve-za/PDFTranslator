"""Tests for chapters API endpoints."""

from fastapi.testclient import TestClient

from pdftranslator.backend.main import app

client = TestClient(app)


def test_get_chapter():
    """Test getting a chapter by ID."""
    response = client.get("/api/chapters/1")
    assert response.status_code in [200, 404]
