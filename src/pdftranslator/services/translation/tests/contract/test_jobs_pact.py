"""
Contract tests for Translation Jobs API using Pact.

CUPID Principle: Composable & Predictable
- Consumer-driven contracts ensure frontend compatibility
- Independent service deployment verification
"""

from __future__ import annotations
import pytest
from pathlib import Path

# Pact imports - will be skipped if not installed
try:
    from pact import Consumer, Provider, Like, EachLike, Verifier
    PACT_AVAILABLE = True
except ImportError:
    PACT_AVAILABLE = False

pytestmark = pytest.mark.skipif(not PACT_AVAILABLE, reason="pact-python not installed")


class TestJobsContracts:
    """Contract tests for Translation Jobs API endpoints."""

    @pytest.fixture
    def pact(self, tmp_path):
        """Create Pact broker for consumer-driven contracts."""
        consumer = Consumer("PDFTranslator-Frontend")
        provider = Provider("PDFTranslator-Translation-Service")
        pact = consumer.has_pact_with(
            provider,
            pact_dir=str(tmp_path),
        )
        yield pact
        pact.stop_service()

    @pytest.fixture
    def translation_app(self):
        """Create FastAPI app for testing - would use testclient in real tests."""
        # This is a mock fixture - in real tests use TestClient
        pass

    def test_list_jobs_returns_paginated_list(self, pact):
        """Contract: GET /jobs returns paginated job list."""
        expected = {
            "items": EachLike({
                "id": Like(1),
                "uuid": Like("660e8400-e29b-41d4-a716-446655440000"),
                "source_lang": Like("en"),
                "target_lang": Like("es"),
                "work_id": Like(1),
                "volume_id": Like(1),
                "status": Like("pending"),
                "priority": Like(50),
                "source_text": Like("Hello world"),
                "target_text": Like(None),
                "llm_provider": Like("openai"),
                "model_name": Like("gpt-4"),
                "error_message": Like(None),
                "started_at": Like(None),
                "completed_at": Like(None),
                "glossary_refs": EachLike({
                    "glossary_id": Like(1),
                    "name": Like("Tech Glossary"),
                    "source_lang": Like("en"),
                    "target_lang": Like("es"),
                    "priority": Like(10),
                    "entry_count": Like(100),
                }),
                "segment_count": Like(0),
                "translated_segment_count": Like(0),
                "progress": Like(0.0),
                "word_count_source": Like(0),
                "word_count_target": Like(0),
                "created_at": Like("2024-01-15T10:30:00"),
                "updated_at": Like("2024-01-15T10:30:00"),
            }),
            "total": Like(1),
            "page": Like(1),
            "page_size": Like(20),
            "total_pages": Like(1),
        }

        (pact
         .given("translation jobs exist")
         .upon_receiving("a request for all translation jobs")
         .with_request("GET", "/jobs")
         .will_respond_with(200, body=expected))

        with pact:
            pass

    def test_list_jobs_with_status_filter(self, pact):
        """Contract: GET /jobs?status=in_progress filters by status."""
        expected = {
            "items": EachLike({
                "id": Like(2),
                "uuid": Like("660e8400-e29b-41d4-a716-446655440001"),
                "source_lang": Like("en"),
                "target_lang": Like("es"),
                "work_id": Like(1),
                "status": Like("in_progress"),
                "priority": Like(50),
            }),
            "total": Like(1),
            "page": Like(1),
            "page_size": Like(20),
            "total_pages": Like(1),
        }

        (pact
         .given("jobs with in_progress status exist")
         .upon_receiving("a request for jobs filtered by in_progress status")
         .with_request("GET", "/jobs", query="status=in_progress")
         .will_respond_with(200, body=expected))

        with pact:
            pass

    def test_get_job_by_id_returns_job(self, pact):
        """Contract: GET /jobs/{id} returns job with details."""
        expected = {
            "id": Like(1),
            "uuid": Like("660e8400-e29b-41d4-a716-446655440000"),
            "source_lang": Like("en"),
            "target_lang": Like("es"),
            "work_id": Like(1),
            "volume_id": Like(1),
            "status": Like("completed"),
            "priority": Like(50),
            "source_text": Like("Hello world, this is a test."),
            "target_text": Like("Hola mundo, esto es una prueba."),
            "llm_provider": Like("openai"),
            "model_name": Like("gpt-4"),
            "error_message": Like(None),
            "started_at": Like("2024-01-15T10:30:00"),
            "completed_at": Like("2024-01-15T10:35:00"),
            "glossary_refs": EachLike({
                "glossary_id": Like(1),
                "name": Like("Tech Glossary"),
                "source_lang": Like("en"),
                "target_lang": Like("es"),
                "priority": Like(10),
                "entry_count": Like(100),
            }),
            "segment_count": Like(5),
            "translated_segment_count": Like(5),
            "progress": Like(100.0),
            "word_count_source": Like(50),
            "word_count_target": Like(52),
            "created_at": Like("2024-01-15T10:30:00"),
            "updated_at": Like("2024-01-15T10:35:00"),
        }

        (pact
         .given("job 1 exists and is completed")
         .upon_receiving("a request for job 1")
         .with_request("GET", "/jobs/1")
         .will_respond_with(200, body=expected))

        with pact:
            pass

    def test_get_job_not_found_returns_404(self, pact):
        """Contract: GET /jobs/{id} returns 404 for non-existent job."""
        (pact
         .given("no job exists with id 999")
         .upon_receiving("a request for non-existent job 999")
         .with_request("GET", "/jobs/999")
         .will_respond_with(404, body={"detail": Like("Job not found")}))

        with pact:
            pass

    def test_get_job_segments_returns_segments(self, pact):
        """Contract: GET /jobs/{id}/segments returns segment summaries."""
        expected = {
            "items": EachLike({
                "id": Like(1),
                "segment_number": Like(1),
                "is_translated": Like(True),
                "word_count_source": Like(10),
                "word_count_target": Like(9),
            }),
        }

        (pact
         .given("job 1 has translation segments")
         .upon_receiving("a request for segments of job 1")
         .with_request("GET", "/jobs/1/segments")
         .will_respond_with(200, body=expected))

        with pact:
            pass

    def test_create_job_returns_created_job(self, pact):
        """Contract: POST /jobs creates new translation job."""
        request_body = {
            "source_lang": "en",
            "target_lang": "es",
            "work_id": 1,
            "volume_id": 1,
            "source_text": "New text to translate",
            "priority": 50,
            "llm_provider": "openai",
            "model_name": "gpt-4"
        }

        expected = {
            "id": Like(1),
            "uuid": Like("660e8400-e29b-41d4-a716-446655440000"),
            "source_lang": Like("en"),
            "target_lang": Like("es"),
            "work_id": Like(1),
            "volume_id": Like(1),
            "status": Like("pending"),
            "priority": Like(50),
            "source_text": Like("New text to translate"),
            "target_text": Like(None),
            "llm_provider": Like("openai"),
            "model_name": Like("gpt-4"),
            "error_message": Like(None),
            "started_at": Like(None),
            "completed_at": Like(None),
            "glossary_refs": EachLike({}),
            "segment_count": Like(0),
            "translated_segment_count": Like(0),
            "progress": Like(0.0),
            "word_count_source": Like(0),
            "word_count_target": Like(0),
            "created_at": Like("2024-01-15T10:30:00"),
            "updated_at": Like("2024-01-15T10:30:00"),
        }

        (pact
         .given("work 1 and volume 1 exist")
         .upon_receiving("a request to create a translation job")
         .with_request("POST", "/jobs", body=request_body)
         .will_respond_with(201, body=expected))

        with pact:
            pass

    def test_create_job_invalid_lang_returns_400(self, pact):
        """Contract: POST /jobs returns 400 for invalid language codes."""
        request_body = {
            "source_lang": "eng",
            "target_lang": "es",
            "work_id": 1,
            "source_text": "Text",
        }

        (pact
         .given("work 1 exists")
         .upon_receiving("a request to create job with invalid source_lang")
         .with_request("POST", "/jobs", body=request_body)
         .will_respond_with(400, body={"detail": Like("ISO 639-1")}))

        with pact:
            pass

    def test_update_job_status_returns_updated_job(self, pact):
        """Contract: PUT /jobs/{id}/status updates job status."""
        (pact
         .given("job 1 exists and is queued")
         .upon_receiving("a request to start job 1")
         .with_request("PUT", "/jobs/1/status", body={
             "status": "in_progress",
             "llm_provider": "openai",
             "model_name": "gpt-4"
         })
         .will_respond_with(200, body={
             "id": Like(1),
             "status": Like("in_progress"),
             "started_at": Like("2024-01-15T10:35:00"),
         }))

        with pact:
            pass

    def test_update_job_status_complete_returns_completed_job(self, pact):
        """Contract: PUT /jobs/{id}/status with completed status."""
        (pact
         .given("job 1 exists and is in_progress")
         .upon_receiving("a request to complete job 1")
         .with_request("PUT", "/jobs/1/status", body={
             "status": "completed",
             "target_text": "Translated text"
         })
         .will_respond_with(200, body={
             "id": Like(1),
             "status": Like("completed"),
             "target_text": Like("Translated text"),
             "progress": Like(100.0),
             "completed_at": Like("2024-01-15T10:40:00"),
         }))

        with pact:
            pass

    def test_update_job_status_fail_returns_failed_job(self, pact):
        """Contract: PUT /jobs/{id}/status with failed status."""
        (pact
         .given("job 1 exists and is in_progress")
         .upon_receiving("a request to fail job 1")
         .with_request("PUT", "/jobs/1/status", body={
             "status": "failed",
             "error_message": "API timeout"
         })
         .will_respond_with(200, body={
             "id": Like(1),
             "status": Like("failed"),
             "error_message": Like("API timeout"),
             "completed_at": Like("2024-01-15T10:45:00"),
         }))

        with pact:
            pass

    def test_update_job_status_invalid_transition_returns_400(self, pact):
        """Contract: PUT /jobs/{id}/status returns 400 for invalid state transition."""
        (pact
         .given("job 1 exists and is completed")
         .upon_receiving("a request to start already completed job")
         .with_request("PUT", "/jobs/1/status", body={
             "status": "in_progress"
         })
         .will_respond_with(400, body={"detail": Like("Cannot start job from status")}))

        with pact:
            pass

    def test_delete_job_returns_204(self, pact):
        """Contract: DELETE /jobs/{id} deletes job."""
        (pact
         .given("job 1 exists")
         .upon_receiving("a request to delete job 1")
         .with_request("DELETE", "/jobs/1")
         .will_respond_with(204, body={}))

        with pact:
            pass

    def test_delete_job_not_found_returns_404(self, pact):
        """Contract: DELETE /jobs/{id} returns 404 for non-existent job."""
        (pact
         .given("no job exists with id 999")
         .upon_receiving("a request to delete non-existent job 999")
         .with_request("DELETE", "/jobs/999")
         .will_respond_with(404, body={"detail": Like("Job not found")}))

        with pact:
            pass


class TestSchemaCompatibility:
    """Tests to verify schema compatibility with frontend expectations."""

    def test_job_status_enum_values(self):
        """Verify JobStatus enum matches frontend expectations."""
        from src.pdftranslator.services.translation.api.schemas.job import JobStatus

        expected_statuses = {"pending", "queued", "in_progress", "completed", "failed", "paused", "cancelled"}
        actual_statuses = {s.value for s in JobStatus}
        assert actual_statuses == expected_statuses

    def test_job_priority_enum_values(self):
        """Verify JobPriority enum matches frontend expectations."""
        from src.pdftranslator.services.translation.api.schemas.job import JobPriority

        expected_priorities = {"low", "normal", "high", "urgent"}
        actual_priorities = {p.value for p in JobPriority}
        assert actual_priorities == expected_priorities

    def test_job_response_schema_fields(self):
        """Verify JobResponse has all expected fields."""
        from src.pdftranslator.services.translation.api.schemas.job import JobResponse

        expected_fields = {
            "id", "uuid", "source_lang", "target_lang", "work_id", "volume_id",
            "status", "priority", "source_text", "target_text", "llm_provider",
            "model_name", "error_message", "started_at", "completed_at",
            "glossary_refs", "segment_count", "translated_segment_count",
            "progress", "word_count_source", "word_count_target",
            "created_at", "updated_at",
        }

        actual_fields = set(JobResponse.model_fields.keys())
        assert expected_fields.issubset(actual_fields)

    def test_job_create_schema_fields(self):
        """Verify JobCreate has all required fields."""
        from src.pdftranslator.services.translation.api.schemas.job import JobCreate

        expected_fields = {
            "source_lang", "target_lang", "work_id", "volume_id",
            "source_text", "priority", "llm_provider", "model_name",
        }

        actual_fields = set(JobCreate.model_fields.keys())
        assert expected_fields.issubset(actual_fields)


class TestHealthContracts:
    """Contract tests for health endpoints."""

    @pytest.fixture
    def pact(self, tmp_path):
        """Create Pact broker for health endpoints."""
        consumer = Consumer("PDFTranslator-Frontend")
        provider = Provider("PDFTranslator-Translation-Service")
        pact = consumer.has_pact_with(
            provider,
            pact_dir=str(tmp_path),
        )
        yield pact
        pact.stop_service()

    def test_health_endpoint(self, pact):
        """Contract: GET /health returns service health."""
        expected = {"status": "healthy", "service": "translation"}

        (pact
         .given("translation service is running")
         .upon_receiving("a request for health check")
         .with_request("GET", "/health")
         .will_respond_with(200, body=expected))

        with pact:
            pass

    def test_ready_endpoint_ready(self, pact):
        """Contract: GET /ready returns ready when DB connected."""
        expected = {"status": "ready", "database": "connected"}

        (pact
         .given("database is connected")
         .upon_receiving("a request for readiness check")
         .with_request("GET", "/ready")
         .will_respond_with(200, body=expected))

        with pact:
            pass

    def test_ready_endpoint_not_ready(self, pact):
        """Contract: GET /ready returns 503 when DB disconnected."""
        (pact
         .given("database is disconnected")
         .upon_receiving("a request for readiness check when DB down")
         .with_request("GET", "/ready")
         .will_respond_with(503, body={"status": "not ready", "database": "disconnected"}))

        with pact:
            pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])