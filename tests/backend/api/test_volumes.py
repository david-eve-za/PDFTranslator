"""Tests for volumes API endpoints."""

from fastapi.testclient import TestClient

from pdftranslator.backend.main import app

client = TestClient(app)


def test_list_volumes_by_work():
    """Test listing volumes by work ID."""
    response = client.get("/api/volumes?work_id=1")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
