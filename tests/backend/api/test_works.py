"""Tests for works API endpoints."""

from fastapi.testclient import TestClient

from pdftranslator.backend.main import app

client = TestClient(app)


def test_list_works_empty():
    """Test listing works when empty."""
    response = client.get("/api/works")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data


def test_create_work():
    """Test creating a new work."""
    work_data = {"title": "Test Book", "author": "Test Author"}
    response = client.post("/api/works", json=work_data)
    assert response.status_code == 201
    assert response.json()["title"] == "Test Book"
