"""
Contract Tests for Translation Service API.

CUPID Principle: Predictable
- Ensures API contract stability for frontend integration
- Validates request/response schemas
- Tests endpoints against expected behavior
"""

from __future__ import annotations
import pytest
from httpx import AsyncClient, ASGITransport

from src.pdftranslator.services.translation.main import create_app


@pytest.fixture
async def app():
    """Create FastAPI app for testing."""
    app = create_app()
    return app


@pytest.fixture
async def client(app):
    """Create async test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


class TestHealthEndpoints:
    """Test health and readiness endpoints."""

    @pytest.mark.asyncio
    async def test_health_endpoint_returns_healthy(self, client):
        """GET /health returns healthy status."""
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "translation"

    @pytest.mark.asyncio
    async def test_ready_endpoint_structure(self, client):
        """GET /ready returns proper structure."""
        response = await client.get("/ready")
        # May return 200 or 503 depending on DB state
        assert response.status_code in (200, 503)
        data = response.json()
        assert "status" in data
        assert "database" in data


class TestJobsEndpoints:
    """Test translation jobs CRUD endpoints."""

    @pytest.mark.asyncio
    async def test_list_jobs_returns_paginated_response(self, client):
        """GET /jobs returns paginated list."""
        response = await client.get("/jobs")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert "total_pages" in data

    @pytest.mark.asyncio
    async def test_list_jobs_with_pagination(self, client):
        """GET /jobs supports pagination params."""
        response = await client.get("/jobs?page=1&page_size=10")
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 10

    @pytest.mark.asyncio
    async def test_list_jobs_with_status_filter(self, client):
        """GET /jobs supports status filtering."""
        response = await client.get("/jobs?status=pending")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_list_jobs_with_work_filter(self, client):
        """GET /jobs supports work_id filtering."""
        response = await client.get("/jobs?work_id=1")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_create_job_requires_required_fields(self, client):
        """POST /jobs validates required fields."""
        response = await client.post("/jobs", json={})
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_create_job_with_valid_data(self, client):
        """POST /jobs creates job with valid data."""
        job_data = {
            "source_lang": "en",
            "target_lang": "es",
            "work_id": 1,
            "volume_id": 1,
            "source_text": "Hello world",
            "priority": 50,
        }
        response = await client.post("/jobs", json=job_data)
        assert response.status_code == 201
        data = response.json()
        assert data["source_lang"] == "en"
        assert data["target_lang"] == "es"
        assert data["work_id"] == 1
        assert data["status"] == "pending"
        assert "id" in data
        assert "uuid" in data

    @pytest.mark.asyncio
    async def test_create_job_invalid_lang_codes(self, client):
        """POST /jobs rejects invalid language codes."""
        job_data = {
            "source_lang": "eng",  # Should be 2 chars
            "target_lang": "spa",
            "work_id": 1,
        }
        response = await client.post("/jobs", json=job_data)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_job_same_source_target_rejected(self, client):
        """POST /jobs rejects same source and target language."""
        job_data = {
            "source_lang": "en",
            "target_lang": "en",
            "work_id": 1,
        }
        response = await client.post("/jobs", json=job_data)
        assert response.status_code == 422
        assert "must differ" in response.text.lower() or "same" in response.text.lower()

    @pytest.mark.asyncio
    async def test_get_job_returns_404_for_missing(self, client):
        """GET /jobs/{id} returns 404 for non-existent job."""
        response = await client.get("/jobs/99999")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_job_status_valid_transitions(self, client):
        """PUT /jobs/{id}/status handles valid transitions."""
        # First create a job
        create_resp = await client.post("/jobs", json={
            "source_lang": "en",
            "target_lang": "es",
            "work_id": 1,
            "llm_provider": "nvidia",
            "model_name": "test-model",
        })
        assert create_resp.status_code == 201
        job = create_resp.json()

        # Queue it
        response = await client.put(f"/jobs/{job['id']}/status", params={"status": "queued"})
        assert response.status_code == 200
        assert response.json()["status"] == "queued"

        # Start it
        response = await client.put(f"/jobs/{job['id']}/status", params={"status": "in_progress"})
        assert response.status_code == 200
        assert response.json()["status"] == "in_progress"

        # Complete it
        response = await client.put(
            f"/jobs/{job['id']}/status",
            params={"status": "completed", "target_text": "Hola mundo"}
        )
        assert response.status_code == 200
        assert response.json()["status"] == "completed"

    @pytest.mark.asyncio
    async def test_update_job_status_invalid_transition(self, client):
        """PUT /jobs/{id}/status rejects invalid transitions."""
        create_resp = await client.post("/jobs", json={
            "source_lang": "en",
            "target_lang": "es",
            "work_id": 1,
        })
        job = create_resp.json()

        # Try to complete from pending (invalid)
        response = await client.put(
            f"/jobs/{job['id']}/status",
            params={"status": "completed", "target_text": "done"}
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_delete_job(self, client):
        """DELETE /jobs/{id} removes job."""
        create_resp = await client.post("/jobs", json={
            "source_lang": "en",
            "target_lang": "es",
            "work_id": 1,
        })
        job = create_resp.json()

        response = await client.delete(f"/jobs/{job['id']}")
        assert response.status_code == 204

        # Verify deleted
        response = await client.get(f"/jobs/{job['id']}")
        assert response.status_code == 404


class TestSegmentsEndpoints:
    """Test segment endpoints."""

    @pytest.mark.asyncio
    async def test_get_job_segments_returns_list(self, client):
        """GET /jobs/{id}/segments returns segment list."""
        # Create job
        create_resp = await client.post("/jobs", json={
            "source_lang": "en",
            "target_lang": "es",
            "work_id": 1,
        })
        job = create_resp.json()

        response = await client.get(f"/jobs/{job['id']}/segments")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestPipelineStageEndpoints:
    """Test individual pipeline stage endpoints."""

    @pytest.mark.asyncio
    async def test_detect_language_endpoint(self, client):
        """POST /pipelines/stages/detect detects language."""
        # This endpoint doesn't require a job to exist
        response = await client.post("/pipelines/stages/detect", json={
            "text": "Hello world, how are you?",
        })
        assert response.status_code == 200
        data = response.json()
        assert "detected_lang" in data
        assert "confidence" in data
        assert "text_stats" in data
        assert data["detected_lang"] in ["en", "es"]

    @pytest.mark.asyncio
    async def test_detect_language_with_job_id(self, client):
        """POST /pipelines/stages/detect works with job_id."""
        # Create job first
        create_resp = await client.post("/jobs", json={
            "source_lang": "en",
            "target_lang": "es",
            "work_id": 1,
        })
        job = create_resp.json()

        response = await client.post("/pipelines/stages/detect", json={
            "text": "This is a test",
            "job_id": job["id"],
        })
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_segment_text_endpoint(self, client):
        """POST /pipelines/stages/segment segments text."""
        create_resp = await client.post("/jobs", json={
            "source_lang": "en",
            "target_lang": "es",
            "work_id": 1,
        })
        job = create_resp.json()

        response = await client.post("/pipelines/stages/segment", json={
            "text": "Hello world. This is a test.",
            "source_lang": "en",
            "target_lang": "es",
            "job_id": job["id"],
        })
        assert response.status_code == 200
        data = response.json()
        assert "total_segments" in data
        assert "segments" in data
        assert isinstance(data["segments"], list)

    @pytest.mark.asyncio
    async def test_segment_text_with_options(self, client):
        """POST /pipelines/stages/segment accepts options."""
        create_resp = await client.post("/jobs", json={
            "source_lang": "en",
            "target_lang": "es",
            "work_id": 1,
        })
        job = create_resp.json()

        response = await client.post("/pipelines/stages/segment", json={
            "text": "One. Two. Three.",
            "source_lang": "en",
            "target_lang": "es",
            "job_id": job["id"],
            "max_segment_length": 100,
            "split_by_sentences": True,
        })
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_translate_segments_endpoint(self, client):
        """POST /pipelines/stages/translate translates segments."""
        create_resp = await client.post("/jobs", json={
            "source_lang": "en",
            "target_lang": "es",
            "work_id": 1,
            "llm_provider": "nvidia",
            "model_name": "test-model",
        })
        job = create_resp.json()

        response = await client.post("/pipelines/stages/translate", json={
            "job_id": job["id"],
            "llm_provider": "nvidia",
            "model_name": "meta/llama-3.1-70b-instruct",
        })
        assert response.status_code == 200
        data = response.json()
        assert "translated_count" in data
        assert "failed_count" in data
        assert "errors" in data
        assert "duration_ms" in data

    @pytest.mark.asyncio
    async def test_quality_check_endpoint(self, client):
        """POST /pipelines/stages/quality-check runs quality checks."""
        create_resp = await client.post("/jobs", json={
            "source_lang": "en",
            "target_lang": "es",
            "work_id": 1,
        })
        job = create_resp.json()

        response = await client.post("/pipelines/stages/quality-check", json={
            "job_id": job["id"],
            "check_types": ["completeness", "fluency"],
            "threshold": 0.7,
        })
        assert response.status_code == 200
        data = response.json()
        assert "checked_count" in data
        assert "passed_count" in data
        assert "failed_count" in data
        assert "issues" in data
        assert "overall_score" in data

    @pytest.mark.asyncio
    async def test_store_translations_endpoint(self, client):
        """POST /pipelines/stages/store stores translations."""
        create_resp = await client.post("/jobs", json={
            "source_lang": "en",
            "target_lang": "es",
            "work_id": 1,
        })
        job = create_resp.json()

        response = await client.post("/pipelines/stages/store", json={
            "job_id": job["id"],
            "overwrite": True,
        })
        assert response.status_code == 200
        data = response.json()
        assert "stored_count" in data
        assert "errors" in data


class TestFullPipelineEndpoint:
    """Test full pipeline execution endpoint."""

    @pytest.mark.asyncio
    async def test_run_pipeline_endpoint(self, client):
        """POST /pipelines/run executes full pipeline."""
        create_resp = await client.post("/jobs", json={
            "source_lang": "en",
            "target_lang": "es",
            "work_id": 1,
        })
        job = create_resp.json()

        response = await client.post("/pipelines/run", json={
            "job_id": job["id"],
            "work_id": 1,
            "source_lang": "en",
            "target_lang": "es",
            "source_text": "Hello world. This is a translation test.",
        })
        assert response.status_code == 200
        data = response.json()
        assert "pipeline_id" in data
        assert "job_id" in data
        assert "stages_completed" in data
        assert "stages_skipped" in data
        assert "errors" in data
        assert "duration_ms" in data
        assert "success" in data

    @pytest.mark.asyncio
    async def test_get_pipeline_status(self, client):
        """GET /pipelines/{job_id} returns pipeline status."""
        create_resp = await client.post("/jobs", json={
            "source_lang": "en",
            "target_lang": "es",
            "work_id": 1,
        })
        job = create_resp.json()

        # Run pipeline
        await client.post("/pipelines/run", json={
            "job_id": job["id"],
            "work_id": 1,
            "source_lang": "en",
            "target_lang": "es",
            "source_text": "Hello world.",
        })

        # Get status
        response = await client.get(f"/pipelines/{job['id']}")
        assert response.status_code == 200
        data = response.json()
        assert "pipeline_id" in data
        assert "status" in data
        assert "stages" in data
        assert isinstance(data["stages"], list)

    @pytest.mark.asyncio
    async def test_resume_pipeline(self, client):
        """POST /pipelines/{job_id}/resume resumes pipeline."""
        create_resp = await client.post("/jobs", json={
            "source_lang": "en",
            "target_lang": "es",
            "work_id": 1,
        })
        job = create_resp.json()

        response = await client.post(f"/pipelines/{job['id']}/resume", json={
            "job_id": job["id"],
        })
        assert response.status_code == 200


class TestAPICompatibility:
    """Test API contracts match expected types."""

    @pytest.mark.asyncio
    async def test_job_response_contains_all_fields(self, client):
        """Job response contains all documented fields."""
        create_resp = await client.post("/jobs", json={
            "source_lang": "en",
            "target_lang": "es",
            "work_id": 1,
            "source_text": "Test",
            "priority": 50,
            "llm_provider": "nvidia",
            "model_name": "test-model",
        })
        job = create_resp.json()

        required_fields = [
            "id", "uuid", "source_lang", "target_lang", "work_id",
            "status", "priority", "source_text", "target_text",
            "llm_provider", "model_name", "error_message",
            "started_at", "completed_at", "glossary_refs",
            "segment_count", "translated_segment_count", "progress",
            "word_count_source", "word_count_target",
            "created_at", "updated_at",
        ]
        for field in required_fields:
            assert field in job, f"Missing field: {field}"

    @pytest.mark.asyncio
    async def test_job_list_response_structure(self, client):
        """Job list response has correct pagination structure."""
        response = await client.get("/jobs")
        data = response.json()

        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert "total_pages" in data

    @pytest.mark.asyncio
    async def test_detect_response_structure(self, client):
        """Detect response has correct structure."""
        response = await client.post("/pipelines/stages/detect", json={
            "text": "Test text",
        })
        data = response.json()

        assert "detected_lang" in data
        assert "confidence" in data
        assert "text_stats" in data