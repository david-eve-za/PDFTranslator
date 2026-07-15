"""
Locust Load Test for Text Processing Library CLI/API.

Run with:
    locust -f locustfile_text_processing.py --headless -u 20 -r 5 -t 30s
"""

from locust import HttpUser, task, between, events
import random


class TextProcessingUser(HttpUser):
    """Simulates text processing API usage."""

    wait_time = between(0.5, 2)

    # Sample texts for testing
    TEXTS = [
        "Short text for chunking.",
        "Medium length text that will be chunked into smaller pieces for processing. "
        "It has multiple sentences and should demonstrate overlap handling.",
        "Long text document for testing chunking performance. " * 20,
    ]

    @task(5)
    def chunk_text(self):
        """Chunk text via API."""
        text = random.choice(self.TEXTS)
        params = {
            "max_tokens": random.choice([100, 256, 512]),
            "overlap": random.choice([10, 25, 50]),
            "min_tokens": random.choice([20, 50, 100]),
            "encoding": "cl100k_base",
            "strategy": "tokens",
        }
        with self.client.post(
            "/api/v1/text/chunk",
            json={"text": text, "config": params},
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(f"Chunk failed: {response.status_code}")

    @task(3)
    def tokenize_text(self):
        """Tokenize text."""
        text = random.choice(self.TEXTS)
        with self.client.post(
            "/api/v1/text/tokenize",
            json={"text": text, "encoding": "cl100k_base"},
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(f"Tokenize failed: {response.status_code}")

    @task(2)
    def analyze_text(self):
        """Analyze text statistics."""
        text = random.choice(self.TEXTS)
        with self.client.post(
            "/api/v1/text/analyze",
            json={"text": text},
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(f"Analyze failed: {response.status_code}")

    @task(2)
    def normalize_text(self):
        """Normalize text."""
        text = "  UNCLEAN   TEXT  WITH  EXTRA   SPACES  \t\n "
        with self.client.post(
            "/api/v1/text/normalize",
            json={
                "text": text,
                "config": {
                    "unicode_form": "NFC",
                    "lower_case": False,
                    "collapse_whitespace": True,
                    "normalize_quotes": True,
                    "normalize_dashes": True,
                },
            },
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(f"Normalize failed: {response.status_code}")

    @task(1)
    def health_check(self):
        """Health endpoint."""
        self.client.get("/health", catch_response=True)


# Alternative: Direct library load test (no HTTP)
class TextProcessingLibraryUser:
    """Direct library load test - run with pytest."""

    # This is a template for pytest-based load tests
    # Actual implementation uses ThreadPoolExecutor in test_text_processing_load.py
    pass


if __name__ == "__main__":
    # Quick standalone test
    import sys
    from locust.env import Environment

    env = Environment(user_classes=[TextProcessingUser])
    env.create_local_runner()
    env.runner.start(user_count=5, spawn_rate=1)
    env.runner.greenlet.join(timeout=30)