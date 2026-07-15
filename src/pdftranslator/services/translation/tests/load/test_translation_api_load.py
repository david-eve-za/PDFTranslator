"""
Load Tests for Translation Service HTTP API.

CUPID Principle: Predictable + Composable
- Validates API performance under load
- Tests individual pipeline stages
- Ensures health endpoints respond quickly
"""

import time
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional
import pytest
from httpx import AsyncClient, ASGITransport

from src.pdftranslator.services.translation.main import create_app


# Test data
SAMPLE_TEXT = "Hello world. This is a test sentence for translation. Another sentence here. Final sentence."
SAMPLE_JOB_DATA = {
    "source_lang": "en",
    "target_lang": "es",
    "work_id": 1,
    "source_text": SAMPLE_TEXT,
    "priority": 50,
    "llm_provider": "nvidia",
    "model_name": "test-model",
}


class LoadTestResult:
    """Container for load test metrics."""

    def __init__(self, name: str):
        self.name = name
        self.latencies: List[float] = []
        self.errors: int = 0
        self.success: int = 0
        self.status_codes: Dict[int, int] = {}

    def record(self, latency: float, error: bool = False, status_code: Optional[int] = None):
        self.latencies.append(latency)
        if status_code:
            self.status_codes[status_code] = self.status_codes.get(status_code, 0) + 1
        if error:
            self.errors += 1
        else:
            self.success += 1

    def summary(self) -> Dict[str, Any]:
        if not self.latencies:
            return {"name": self.name, "error": "No samples"}

        sorted_lat = sorted(self.latencies)
        n = len(sorted_lat)

        return {
            "name": self.name,
            "total_requests": n,
            "success": self.success,
            "errors": self.errors,
            "error_rate": self.errors / n if n > 0 else 0,
            "status_codes": self.status_codes,
            "min_ms": min(sorted_lat) * 1000,
            "max_ms": max(sorted_lat) * 1000,
            "mean_ms": statistics.mean(sorted_lat) * 1000,
            "median_ms": statistics.median(sorted_lat) * 1000,
            "p95_ms": sorted_lat[int(n * 0.95)] * 1000,
            "p99_ms": sorted_lat[int(n * 0.99)] * 1000,
            "throughput_ops_sec": self.success / sum(sorted_lat) if sum(sorted_lat) > 0 else 0,
        }

    def print_summary(self):
        s = self.summary()
        if "error" in s:
            print(f"{self.name}: {s['error']}")
            return
        print(f"\n{self.name} Load Test Results:")
        print(f"  Requests: {s['total_requests']} (Success: {s['success']}, Errors: {s['errors']})")
        print(f"  Status codes: {s['status_codes']}")
        print(f"  Error Rate: {s['error_rate']:.2%}")
        print(f"  Latency - Min: {s['min_ms']:.2f}ms, Max: {s['max_ms']:.2f}ms")
        print(f"  Mean: {s['mean_ms']:.2f}ms, Median: {s['median_ms']:.2f}ms")
        print(f"  P95: {s['p95_ms']:.2f}ms, P99: {s['p99_ms']:.2f}ms")
        print(f"  Throughput: {s['throughput_ops_sec']:.1f} ops/sec")


def run_async_load_test(
    name: str,
    func,
    iterations: int = 50,
    concurrency: int = 1,
) -> LoadTestResult:
    """Run an async load test and collect metrics."""
    import asyncio

    result = LoadTestResult(name)

    async def run_single():
        start = time.perf_counter()
        try:
            await func()
            result.record(time.perf_counter() - start)
        except Exception as e:
            result.record(time.perf_counter() - start, error=True)

    if concurrency == 1:
        for _ in range(iterations):
            asyncio.run(run_single())
    else:
        async def run_concurrent():
            tasks = [run_single() for _ in range(iterations)]
            # Limit concurrency
            semaphore = asyncio.Semaphore(concurrency)

            async def limited(task):
                async with semaphore:
                    await task

            await asyncio.gather(*[limited(t) for t in tasks])

        asyncio.run(run_concurrent())

    return result


def run_sync_load_test(
    name: str,
    func,
    iterations: int = 50,
    concurrency: int = 1,
) -> LoadTestResult:
    """Run a sync load test."""
    result = LoadTestResult(name)

    if concurrency == 1:
        for _ in range(iterations):
            start = time.perf_counter()
            try:
                func()
                result.record(time.perf_counter() - start)
            except Exception:
                result.record(time.perf_counter() - start, error=True)
    else:
        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = [executor.submit(func) for _ in range(iterations)]
            for future in as_completed(futures):
                start = time.perf_counter()
                try:
                    future.result()
                    result.record(time.perf_counter() - start)
                except Exception:
                    result.record(time.perf_counter() - start, error=True)

    return result


@pytest.fixture(scope="module")
def app():
    """Create FastAPI app for testing."""
    return create_app()


@pytest.fixture(scope="module")
async def client(app):
    """Create async test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


class TestHealthEndpointsLoad:
    """Load tests for health endpoints."""

    @pytest.mark.asyncio
    async def test_health_endpoint_load(self, client):
        """Health endpoint should handle high load."""
        result = run_async_load_test(
            "GET /health",
            lambda: client.get("/health"),
            iterations=200,
            concurrency=20,
        )
        result.print_summary()

        assert result.errors == 0
        assert result.summary()["p95_ms"] < 50, "Health check should be very fast"
        assert result.status_codes.get(200) == 200

    @pytest.mark.asyncio
    async def test_ready_endpoint_load(self, client):
        """Ready endpoint load test."""
        result = run_async_load_test(
            "GET /ready",
            lambda: client.get("/ready"),
            iterations=100,
            concurrency=10,
        )
        result.print_summary()
        assert result.status_codes.get(200, 0) + result.status_codes.get(503, 0) == 100


class TestJobsEndpointsLoad:
    """Load tests for jobs CRUD endpoints."""

    @pytest.mark.asyncio
    async def test_list_jobs_load(self, client):
        """List jobs under load."""
        result = run_async_load_test(
            "GET /jobs",
            lambda: client.get("/jobs?page=1&page_size=20"),
            iterations=100,
            concurrency=10,
        )
        result.print_summary()
        assert result.errors == 0
        assert result.summary()["p95_ms"] < 200

    @pytest.mark.asyncio
    async def test_create_job_load(self, client):
        """Create job under load."""
        job_counter = {"count": 0}

        async def create_job():
            job_counter["count"] += 1
            data = SAMPLE_JOB_DATA.copy()
            data["source_text"] = f"Job {job_counter['count']}. " + SAMPLE_TEXT
            return await client.post("/jobs", json=data)

        result = run_async_load_test(
            "POST /jobs",
            create_job,
            iterations=50,
            concurrency=5,
        )
        result.print_summary()
        # Some may fail due to DB constraints, but most should succeed
        assert result.success >= 40, f"Too many errors: {result.errors}/{result.success}"

    @pytest.mark.asyncio
    async def test_job_lifecycle_load(self, client):
        """Full job lifecycle: create -> queue -> in_progress -> complete."""
        # Create job
        create_resp = await client.post("/jobs", json=SAMPLE_JOB_DATA)
        assert create_resp.status_code == 201
        job = create_resp.json()
        job_id = job["id"]

        # Test status transitions under load
        statuses = ["queued", "in_progress", "completed"]

        for status in statuses:
            for _ in range(10):
                params = {"status": status}
                if status == "completed":
                    params["target_text"] = "Traducción completada"

                result = run_async_load_test(
                    f"PUT /jobs/{job_id}/status ({status})",
                    lambda: client.put(f"/jobs/{job_id}/status", params=params),
                    iterations=10,
                    concurrency=5,
                )
                result.print_summary()


class TestPipelineStageEndpointsLoad:
    """Load tests for individual pipeline stage endpoints."""

    @pytest.mark.asyncio
    async def test_detect_language_load(self, client):
        """Language detection stage under load."""
        result = run_async_load_test(
            "POST /pipelines/stages/detect",
            lambda: client.post("/pipelines/stages/detect", json={"text": SAMPLE_TEXT}),
            iterations=50,
            concurrency=5,
        )
        result.print_summary()
        assert result.errors == 0
        assert result.status_codes.get(200) == 50

    @pytest.mark.asyncio
    async def test_segment_text_load(self, client):
        """Text segmentation stage under load."""
        # Create job first
        create_resp = await client.post("/jobs", json=SAMPLE_JOB_DATA)
        job = create_resp.json()
        job_id = job["id"]

        result = run_async_load_test(
            "POST /pipelines/stages/segment",
            lambda: client.post("/pipelines/stages/segment", json={
                "text": SAMPLE_TEXT * 5,
                "source_lang": "en",
                "target_lang": "es",
                "job_id": job_id,
            }),
            iterations=30,
            concurrency=3,
        )
        result.print_summary()
        # May have some failures due to DB
        assert result.success >= 20

    @pytest.mark.asyncio
    async def test_quality_check_load(self, client):
        """Quality check stage under load."""
        create_resp = await client.post("/jobs", json=SAMPLE_JOB_DATA)
        job = create_resp.json()
        job_id = job["id"]

        result = run_async_load_test(
            "POST /pipelines/stages/quality-check",
            lambda: client.post("/pipelines/stages/quality-check", json={
                "job_id": job_id,
                "check_types": ["completeness", "fluency"],
                "threshold": 0.7,
            }),
            iterations=30,
            concurrency=3,
        )
        result.print_summary()


class TestFullPipelineLoad:
    """Load tests for full pipeline execution."""

    @pytest.mark.asyncio
    async def test_run_pipeline_load(self, client):
        """Full pipeline execution under load."""
        create_resp = await client.post("/jobs", json=SAMPLE_JOB_DATA)
        job = create_resp.json()
        job_id = job["id"]

        result = run_async_load_test(
            "POST /pipelines/run",
            lambda: client.post("/pipelines/run", json={
                "job_id": job_id,
                "work_id": 1,
                "source_lang": "en",
                "target_lang": "es",
                "source_text": SAMPLE_TEXT * 3,
            }),
            iterations=10,
            concurrency=2,
        )
        result.print_summary()
        # Pipeline is heavier, allow some failures
        assert result.success >= 5


class TestConcurrentMixedLoad:
    """Mixed workload simulating real usage."""

    @pytest.mark.asyncio
    async def test_mixed_read_write_load(self, client):
        """Simulate mixed read/write workload."""
        async def mixed_workload():
            # 70% reads, 30% writes
            import random
            if random.random() < 0.7:
                # Read operations
                ops = [
                    lambda: client.get("/health"),
                    lambda: client.get("/ready"),
                    lambda: client.get("/jobs"),
                    lambda: client.get("/jobs/1"),
                ]
                await random.choice(ops)()
            else:
                # Write operations
                data = SAMPLE_JOB_DATA.copy()
                data["source_text"] = "Mixed load test. " + SAMPLE_TEXT
                await client.post("/jobs", json=data)

        result = run_async_load_test(
            "Mixed Read/Write",
            mixed_workload,
            iterations=100,
            concurrency=10,
        )
        result.print_summary()
        assert result.success >= 80


@pytest.mark.slow
class TestStressLoad:
    """Stress tests - run separately with --run-stress flag."""

    @pytest.mark.asyncio
    async def test_sustained_load_1min(self, client):
        """Sustained load for ~1 minute."""
        import asyncio

        async def health_check():
            await client.get("/health")

        start_time = time.time()
        count = 0
        errors = 0

        async def worker():
            nonlocal count, errors
            while time.time() - start_time < 60:
                try:
                    await health_check()
                    count += 1
                except Exception:
                    errors += 1
                await asyncio.sleep(0.01)

        await asyncio.gather(*[worker() for _ in range(20)])

        elapsed = time.time() - start_time
        print(f"\nStress Test: {count} requests in {elapsed:.1f}s ({count/elapsed:.1f} req/s)")
        print(f"Errors: {errors}")

        assert errors < count * 0.01, "Error rate should be < 1%"


# Pytest markers
pytestmark = [
    pytest.mark.load,
]


if __name__ == "__main__":
    # Run with: pytest test_translation_api_load.py -v -m load
    pytest.main([__file__, "-v", "-m", "load", "--tb=short"])