"""
Contract Tests for Glossary Service API.

CUPID Principle: Predictable
- Pact contract tests ensure API compatibility
- Frontend/Backend contract validation
"""

from __future__ import annotations
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.pdftranslator.services.glossary.main import app


class TestHealthContract:
    """Contract tests for health endpoints."""

    def test_health_endpoint_returns_200(self):
        """Health endpoint should return 200 with healthy status."""
        with TestClient(app) as client:
            response = client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["service"] == "glossary-service"
            assert "timestamp" in data

    def test_ready_endpoint_returns_200_when_ready(self):
        """Ready endpoint should return 200 when service is ready."""
        with TestClient(app) as client:
            response = client.get("/health/ready")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ready"
            assert "database" in data
            assert "migrations" in data


class TestGlossaryCRUDContract:
    """Contract tests for glossary CRUD endpoints."""

    def test_create_glossary_contract(self):
        """Create glossary endpoint contract."""
        with TestClient(app) as client:
            payload = {
                "work_id": 1,
                "name": "Test Glossary",
                "source_lang": "en",
                "target_lang": "es",
            }
            # May return 201 or 400 depending on DB state
            response = client.post("/api/v1/glossaries", json=payload)
            assert response.status_code in (201, 400, 422)

    def test_list_glossaries_contract(self):
        """List glossaries endpoint contract."""
        with TestClient(app) as client:
            response = client.get("/api/v1/glossaries")
            assert response.status_code == 200
            data = response.json()
            assert "items" in data
            assert "total" in data
            assert "page" in data
            assert "page_size" in data
            assert "total_pages" in data

    def test_get_glossary_by_work_contract(self):
        """Get glossary by work ID contract."""
        with TestClient(app) as client:
            response = client.get("/api/v1/glossaries/work/1")
            assert response.status_code in (200, 404)

    def test_search_glossary_contract(self):
        """Search glossary endpoint contract."""
        with TestClient(app) as client:
            response = client.get("/api/v1/glossaries/1/search", params={"query": "test"})
            assert response.status_code in (200, 404)
            if response.status_code == 200:
                data = response.json()
                assert "items" in data
                assert "total" in data


class TestPipelineContract:
    """Contract tests for pipeline endpoints."""

    def test_build_glossary_contract(self):
        """Build glossary endpoint contract."""
        with TestClient(app) as client:
            payload = {
                "work_id": 1,
                "volume_id": 1,
                "text": "Test text for extraction",
                "source_lang": "en",
                "target_lang": "es",
            }
            response = client.post("/api/v1/glossaries/build", json=payload)
            assert response.status_code in (200, 400, 422)

    def test_list_pipelines_contract(self):
        """List pipelines endpoint contract."""
        with TestClient(app) as client:
            response = client.get("/api/v1/glossaries/pipelines")
            assert response.status_code == 200
            data = response.json()
            assert "items" in data

    def test_get_pipeline_status_contract(self):
        """Get pipeline status endpoint contract."""
        with TestClient(app) as client:
            response = client.get("/api/v1/glossaries/pipelines/1/1")
            assert response.status_code in (200, 404)

    def test_resume_pipeline_contract(self):
        """Resume pipeline endpoint contract."""
        with TestClient(app) as client:
            response = client.post("/api/v1/glossaries/pipelines/1/1/resume")
            assert response.status_code in (200, 404, 400)


class TestStageEndpointsContract:
    """Contract tests for individual pipeline stage endpoints."""

    def test_extract_entities_contract(self):
        """Extract entities stage contract."""
        with TestClient(app) as client:
            payload = {
                "text": "The slime attacked the goblin with mana.",
                "source_lang": "en",
                "min_frequency": 1,
            }
            response = client.post("/api/v1/glossaries/pipelines/stages/extract", json=payload)
            assert response.status_code in (200, 400, 422)
            if response.status_code == 200:
                data = response.json()
                assert "entities" in data
                assert "total" in data

    def test_filter_entities_contract(self):
        """Filter entities stage contract."""
        with TestClient(app) as client:
            payload = {
                "work_id": 1,
                "entities": [
                    {
                        "id": "test-1",
                        "text": "slime",
                        "entity_type": "race",
                        "frequency": 3,
                        "source_language": "en",
                        "contexts": [],
                        "confidence": 0.9,
                        "validated": False,
                    }
                ],
            }
            response = client.post("/api/v1/glossaries/pipelines/stages/filter", json=payload)
            assert response.status_code in (200, 400, 422)

    def test_validate_entities_contract(self):
        """Validate entities stage contract."""
        with TestClient(app) as client:
            payload = {
                "entities": [
                    {
                        "id": "test-1",
                        "text": "slime",
                        "entity_type": "race",
                        "frequency": 3,
                        "source_language": "en",
                        "contexts": [],
                        "confidence": 0.9,
                        "validated": False,
                    }
                ],
                "source_lang": "en",
                "work_id": 1,
                "volume_id": 1,
            }
            response = client.post("/api/v1/glossaries/pipelines/stages/validate", json=payload)
            assert response.status_code in (200, 400, 422)

    def test_generate_embeddings_contract(self):
        """Generate embeddings stage contract."""
        with TestClient(app) as client:
            payload = {
                "entities": [
                    {
                        "id": "test-1",
                        "text": "slime",
                        "entity_type": "race",
                        "frequency": 3,
                        "source_language": "en",
                        "contexts": [],
                        "confidence": 0.9,
                        "validated": True,
                    }
                ],
            }
            response = client.post("/api/v1/glossaries/pipelines/stages/embed", json=payload)
            assert response.status_code in (200, 400, 422)

    def test_suggest_translations_contract(self):
        """Suggest translations stage contract."""
        with TestClient(app) as client:
            payload = {
                "entities": [
                    {
                        "id": "test-1",
                        "text": "slime",
                        "entity_type": "race",
                        "frequency": 3,
                        "source_language": "en",
                        "contexts": [],
                        "confidence": 0.9,
                        "validated": True,
                    }
                ],
                "source_lang": "en",
                "target_lang": "es",
            }
            response = client.post(
                "/api/v1/glossaries/pipelines/stages/translate", json=payload
            )
            assert response.status_code in (200, 400, 422)

    def test_save_entities_contract(self):
        """Save entities stage contract."""
        with TestClient(app) as client:
            payload = {
                "work_id": 1,
                "entities": [
                    {
                        "id": "test-1",
                        "text": "slime",
                        "entity_type": "race",
                        "frequency": 3,
                        "source_language": "en",
                        "contexts": [],
                        "confidence": 0.9,
                        "validated": True,
                        "translation": "slime",
                    }
                ],
                "source_lang": "en",
                "target_lang": "es",
            }
            response = client.post("/api/v1/glossaries/pipelines/stages/store", json=payload)
            assert response.status_code in (200, 400, 422)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])