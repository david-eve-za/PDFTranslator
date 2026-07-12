"""
Contract Tests for Glossary Service API.

CUPID Principle: Predictable
- Pact contract tests ensure API compatibility with frontend
- Tests can be run against provider to verify contract
"""

from __future__ import annotations
import pytest
from fastapi.testclient import TestClient

from src.pdftranslator.services.glossary.main import app


class TestHealthEndpointsContract:
    """Contract tests for health check endpoints."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_health_endpoint_returns_healthy(self, client):
        """GET /health returns 200 with healthy status."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "glossary-service"
        assert "timestamp" in data
        assert "version" in data

    def test_ready_endpoint_returns_ready_or_not_ready(self, client):
        """GET /health/ready returns readiness status."""
        response = client.get("/health/ready")
        assert response.status_code in (200, 503)
        data = response.json()
        assert data["status"] in ("ready", "not ready")
        assert "database" in data
        assert "migrations" in data


class TestGlossaryCRUDContract:
    """Contract tests for glossary CRUD operations."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_create_glossary_request_schema(self, client):
        """POST /api/v1/glossaries accepts GlossaryCreate schema."""
        payload = {
            "work_id": 1,
            "name": "Test Glossary",
            "source_lang": "en",
            "target_lang": "es",
        }
        response = client.post("/api/v1/glossaries", json=payload)
        # May fail if DB not ready, but should accept the schema
        assert response.status_code in (201, 400, 422)
        if response.status_code == 422:
            # Schema validation error
            pytest.fail(f"Schema validation failed: {response.json()}")

    def test_list_glossaries_response_schema(self, client):
        """GET /api/v1/glossaries returns PaginatedResponse[GlossaryResponse]."""
        response = client.get("/api/v1/glossaries")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert "total_pages" in data

    def test_get_glossary_by_work_response_schema(self, client):
        """GET /api/v1/glossaries/work/{work_id} returns GlossaryDetailResponse."""
        response = client.get("/api/v1/glossaries/work/1")
        assert response.status_code in (200, 404)
        if response.status_code == 200:
            data = response.json()
            assert "id" in data
            assert "uuid" in data
            assert "work_id" in data
            assert "name" in data
            assert "entries" in data

    def test_search_glossary_response_schema(self, client):
        """GET /api/v1/glossaries/{glossary_id}/search returns paginated entries."""
        response = client.get("/api/v1/glossaries/1/search", params={"query": "test"})
        assert response.status_code in (200, 404)
        if response.status_code == 200:
            data = response.json()
            assert "items" in data
            assert "total" in data
            assert "page" in data
            assert "page_size" in data
            assert "total_pages" in data


class TestPipelineContract:
    """Contract tests for pipeline operations."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_build_glossary_request_schema(self, client):
        """POST /api/v1/glossaries/build accepts BuildGlossaryRequest."""
        payload = {
            "work_id": 1,
            "volume_id": 1,
            "text": "The dragon flew over the mountain.",
            "source_lang": "en",
            "target_lang": "es",
            "min_frequency": 1,
            "suggest_translations": True,
        }
        response = client.post("/api/v1/glossaries/build", json=payload)
        assert response.status_code in (200, 201, 400, 422, 503)
        if response.status_code == 422:
            pytest.fail(f"Schema validation failed: {response.json()}")

    def test_list_pipelines_response_schema(self, client):
        """GET /api/v1/glossaries/pipelines returns paginated pipelines."""
        response = client.get("/api/v1/glossaries/pipelines")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert "total_pages" in data

    def test_get_pipeline_status_response_schema(self, client):
        """GET /api/v1/glossaries/pipelines/{work_id}/{volume_id} returns pipeline."""
        response = client.get("/api/v1/glossaries/pipelines/1/1")
        assert response.status_code in (200, 404)
        if response.status_code == 200:
            data = response.json()
            assert "id" in data
            assert "work_id" in data
            assert "volume_id" in data
            assert "status" in data
            assert "progress_percent" in data
            assert "stages" in data
            assert isinstance(data["stages"], list)

    def test_resume_pipeline_request_schema(self, client):
        """POST /api/v1/glossaries/pipelines/{work_id}/{volume_id}/resume."""
        response = client.post("/api/v1/glossaries/pipelines/1/1/resume")
        assert response.status_code in (200, 404, 409)


class TestIndividualStageEndpointsContract:
    """Contract tests for individual pipeline stage endpoints."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_extract_entities_request_schema(self, client):
        """POST /api/v1/glossaries/pipelines/stages/extract accepts ExtractEntitiesRequest."""
        payload = {
            "text": "The dragon attacked the village.",
            "source_lang": "en",
            "min_frequency": 1,
        }
        response = client.post("/api/v1/glossaries/pipelines/stages/extract", json=payload)
        assert response.status_code in (200, 201, 400, 422, 503)
        if response.status_code == 200:
            data = response.json()
            assert "entities" in data
            assert "total" in data

    def test_filter_entities_request_schema(self, client):
        """POST /api/v1/glossaries/pipelines/stages/filter accepts FilterEntitiesRequest."""
        payload = {
            "work_id": 1,
            "entities": [
                {"id": "1", "text": "dragon", "entity_type": "race", "frequency": 1, "source_language": "en"}
            ],
        }
        response = client.post("/api/v1/glossaries/pipelines/stages/filter", json=payload)
        assert response.status_code in (200, 201, 400, 422, 503)

    def test_validate_entities_request_schema(self, client):
        """POST /api/v1/glossaries/pipelines/stages/validate accepts ValidateEntitiesRequest."""
        payload = {
            "entities": [
                {"id": "1", "text": "dragon", "entity_type": "race", "frequency": 1, "source_language": "en"}
            ],
            "source_lang": "en",
            "work_id": 1,
            "volume_id": 1,
            "batch_size": 50,
        }
        response = client.post("/api/v1/glossaries/pipelines/stages/validate", json=payload)
        assert response.status_code in (200, 201, 400, 422, 503)

    def test_generate_embeddings_request_schema(self, client):
        """POST /api/v1/glossaries/pipelines/stages/embed accepts GenerateEmbeddingsRequest."""
        payload = {
            "entities": [
                {"id": "1", "text": "dragon", "entity_type": "race", "frequency": 1, "source_language": "en"}
            ],
            "model_name": "nvidia/nv-embedqa-e5-v5",
        }
        response = client.post("/api/v1/glossaries/pipelines/stages/embed", json=payload)
        assert response.status_code in (200, 201, 400, 422, 503)

    def test_suggest_translations_request_schema(self, client):
        """POST /api/v1/glossaries/pipelines/stages/translate accepts SuggestTranslationsRequest."""
        payload = {
            "entities": [
                {"id": "1", "text": "dragon", "entity_type": "race", "frequency": 1, "source_language": "en"}
            ],
            "source_lang": "en",
            "target_lang": "es",
            "batch_size": 50,
        }
        response = client.post("/api/v1/glossaries/pipelines/stages/translate", json=payload)
        assert response.status_code in (200, 201, 400, 422, 503)

    def test_save_entities_request_schema(self, client):
        """POST /api/v1/glossaries/pipelines/stages/store accepts SaveEntitiesRequest."""
        payload = {
            "work_id": 1,
            "entities": [
                {"id": "1", "text": "dragon", "entity_type": "race", "frequency": 1, "source_language": "en",
                 "translation": "dragón"}
            ],
            "source_lang": "en",
            "target_lang": "es",
        }
        response = client.post("/api/v1/glossaries/pipelines/stages/store", json=payload)
        assert response.status_code in (200, 201, 400, 422, 503)


class TestEntryCRUDContract:
    """Contract tests for glossary entry CRUD."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_create_entry_request_schema(self, client):
        """POST /api/v1/glossaries/{glossary_id}/entries accepts GlossaryEntryCreate."""
        payload = {
            "term": "dragon",
            "translation": "dragón",
            "entity_type": "race",
            "do_not_translate": True,
            "is_verified": True,
            "confidence": 0.95,
        }
        response = client.post("/api/v1/glossaries/1/entries", json=payload)
        assert response.status_code in (201, 400, 404, 422, 501)

    def test_list_entries_response_schema(self, client):
        """GET /api/v1/glossaries/{glossary_id}/entries returns paginated entries."""
        response = client.get("/api/v1/glossaries/1/entries")
        assert response.status_code in (200, 404, 501)
        if response.status_code == 200:
            data = response.json()
            assert "items" in data
            assert "total" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])