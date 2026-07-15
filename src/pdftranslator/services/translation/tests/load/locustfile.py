"""
Locust Load Test Suite for Translation Service API.

CUPID Principle: Predictable + Composable
- Realistic user behavior simulation
- Can run headless in CI/CD
- Generates HTML reports

Run with:
    locust -f locustfile.py --headless -u 50 -r 10 -t 60s --host http://localhost:8002

Or for UI:
    locust -f locustfile.py
"""

from locust import HttpUser, task, between, events
import random
import json


class TranslationUser(HttpUser):
    """Simulates a user interacting with the Translation Service API."""

    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks

    def on_start(self):
        """Initialize user session - create a job to work with."""
        # Create initial job
        job_data = {
            "source_lang": "en",
            "target_lang": "es",
            "work_id": 1,
            "source_text": "Hello world. This is a test document for translation.",
            "priority": 50,
            "llm_provider": "nvidia",
            "model_name": "meta/llama-3.1-70b-instruct",
        }
        with self.client.post("/jobs", json=job_data, catch_response=True) as response:
            if response.status_code == 201:
                self.job_id = response.json()["id"]
                response.success()
            else:
                self.job_id = None
                response.failure(f"Failed to create job: {response.status_code}")

        # Also create a job for pipeline testing
        pipeline_job = {
            "source_lang": "en",
            "target_lang": "fr",
            "work_id": 2,
            "source_text": "Bonjour le monde. Comment allez-vous aujourd'hui?",
            "llm_provider": "nvidia",
        }
        with self.client.post("/jobs", json=pipeline_job, catch_response=True) as response:
            if response.status_code == 201:
                self.pipeline_job_id = response.json()["id"]
                response.success()
            else:
                self.pipeline_job_id = None
                response.failure(f"Failed to create pipeline job: {response.status_code}")

    @task(5)
    def health_check(self):
        """Regular health checks - most frequent operation."""
        with self.client.get("/health", catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"Health check failed: {response.status_code}")
            elif response.json().get("status") != "healthy":
                response.failure("Health check returned unhealthy")

    @task(3)
    def readiness_check(self):
        """Readiness checks."""
        self.client.get("/ready", catch_response=True)

    @task(2)
    def list_jobs(self):
        """List translation jobs."""
        with self.client.get("/jobs?page=1&page_size=20", catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"List jobs failed: {response.status_code}")

    @task(2)
    def get_job_details(self):
        """Get specific job details."""
        if self.job_id:
            self.client.get(f"/jobs/{self.job_id}", catch_response=True)

    @task(1)
    def create_job(self):
        """Create a new translation job."""
        job_data = {
            "source_lang": random.choice(["en", "es", "fr", "de"]),
            "target_lang": random.choice(["en", "es", "fr", "de", "it", "pt"]),
            "work_id": random.randint(1, 100),
            "source_text": random.choice([
                "Short text for translation.",
                "Medium length text for testing the translation service with multiple sentences here.",
                "Longer document content that will be chunked and processed through the translation pipeline with glossary support.",
            ]),
            "priority": random.randint(10, 90),
            "llm_provider": "nvidia",
            "model_name": "meta/llama-3.1-70b-instruct",
        }
        with self.client.post("/jobs", json=job_data, catch_response=True) as response:
            if response.status_code == 201:
                # Track for potential update
                job = response.json()
                if not hasattr(self, "created_job_ids"):
                    self.created_job_ids = []
                self.created_job_ids.append(job["id"])
                response.success()
            else:
                response.failure(f"Create job failed: {response.status_code}")

    @task(1)
    def update_job_status(self):
        """Update job status - queued, in_progress, completed."""
        if not hasattr(self, "created_job_ids") or not self.created_job_ids:
            return

        job_id = random.choice(self.created_job_ids)
        status = random.choice(["queued", "in_progress"])
        params = {"status": status}

        with self.client.put(f"/jobs/{job_id}/status", params=params, catch_response=True) as response:
            if response.status_code not in (200, 400, 404):
                response.failure(f"Status update failed: {response.status_code}")

    @task(1)
    def pipeline_detect_language(self):
        """Test language detection pipeline stage."""
        text = random.choice([
            "Hello, how are you?",
            "Bonjour, comment allez-vous?",
            "Hola, ¿cómo estás?",
            "Guten Tag, wie geht es dir?",
        ])
        with self.client.post("/pipelines/stages/detect", json={"text": text}, catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"Detect language failed: {response.status_code}")

    @task(1)
    def pipeline_segment_text(self):
        """Test text segmentation pipeline stage."""
        if not self.job_id:
            return

        text = "First sentence. Second sentence here. Third sentence for testing. Final sentence."
        with self.client.post("/pipelines/stages/segment", json={
            "text": text,
            "source_lang": "en",
            "target_lang": "es",
            "job_id": self.job_id,
        }, catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"Segment text failed: {response.status_code}")

    @task(1)
    def pipeline_quality_check(self):
        """Test quality check pipeline stage."""
        if not self.pipeline_job_id:
            return

        with self.client.post("/pipelines/stages/quality-check", json={
            "job_id": self.pipeline_job_id,
            "check_types": ["completeness", "fluency"],
            "threshold": 0.7,
        }, catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"Quality check failed: {response.status_code}")

    @task(1)
    def run_full_pipeline(self):
        """Run full translation pipeline."""
        if not hasattr(self, "pipeline_job_id") or not self.pipeline_job_id:
            return

        with self.client.post("/pipelines/run", json={
            "job_id": self.pipeline_job_id,
            "work_id": 2,
            "source_lang": "en",
            "target_lang": "fr",
            "source_text": "This is a test document for the full translation pipeline.",
        }, catch_response=True) as response:
            if response.status_code not in (200, 400):
                response.failure(f"Run pipeline failed: {response.status_code}")

    @task(1)
    def get_pipeline_status(self):
        """Get pipeline status."""
        if not self.job_id:
            return

        with self.client.get(f"/pipelines/{self.job_id}", catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"Pipeline status failed: {response.status_code}")

    @task(1)
    def get_job_segments(self):
        """Get job segments."""
        if not self.job_id:
            return

        self.client.get(f"/jobs/{self.job_id}/segments", catch_response=True)

    @task(1)
    def delete_job(self):
        """Delete a job (cleanup)."""
        if not hasattr(self, "created_job_ids") or not self.created_job_ids:
            return

        job_id = self.created_job_ids.pop()
        with self.client.delete(f"/jobs/{job_id}", catch_response=True) as response:
            if response.status_code not in (204, 404):
                response.failure(f"Delete job failed: {response.status_code}")


class HeavyLoadUser(TranslationUser):
    """User that performs heavier operations more frequently."""

    wait_time = between(0.5, 1.5)

    @task(10)
    def health_check(self):
        super().health_check()

    @task(5)
    def run_full_pipeline(self):
        super().run_full_pipeline()


class PipelineStageUser(HttpUser):
    """User focused on pipeline stage testing."""

    wait_time = between(1, 2)

    @task
    def stage_detect(self):
        """Language detection."""
        self.client.post("/pipelines/stages/detect", json={
            "text": "Test text for language detection."
        })

    @task
    def stage_segment(self):
        """Text segmentation."""
        # Need job first
        resp = self.client.post("/jobs", json={
            "source_lang": "en",
            "target_lang": "es",
            "work_id": 1,
            "source_text": "Test.",
        })
        if resp.status_code == 201:
            job_id = resp.json()["id"]
            self.client.post("/pipelines/stages/segment", json={
                "text": "Sentence one. Sentence two. Sentence three.",
                "source_lang": "en",
                "target_lang": "es",
                "job_id": job_id,
            })

    @task
    def stage_translate(self):
        """Translation stage."""
        resp = self.client.post("/jobs", json={
            "source_lang": "en",
            "target_lang": "es",
            "work_id": 1,
            "source_text": "Test.",
            "llm_provider": "nvidia",
            "model_name": "test-model",
        })
        if resp.status_code == 201:
            job_id = resp.json()["id"]
            self.client.post("/pipelines/stages/translate", json={
                "job_id": job_id,
                "llm_provider": "nvidia",
                "model_name": "meta/llama-3.1-70b-instruct",
            })


# Event hooks for custom reporting
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    print("Starting Translation Service Load Test")

@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    print("Load test completed")


if __name__ == "__main__":
    # Allow running directly for simple tests
    import sys
    from locust.env import Environment
    from locust.stats import stats_printer, stats_history
    from locust.log import setup_logging

    setup_logging("INFO", None)

    env = Environment(user_classes=[TranslationUser])
    env.create_local_runner()
    env.runner.start(user_count=10, spawn_rate=2)
    env.runner.greenlet.join(timeout=30)