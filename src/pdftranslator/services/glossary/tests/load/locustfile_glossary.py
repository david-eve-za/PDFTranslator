"""
Load Tests for Glossary Service API.

Run with:
    locust -f locustfile_glossary.py --headless -u 30 -r 5 -t 60s --host http://localhost:8003
"""

from locust import HttpUser, task, between, events
import random


class GlossaryUser(HttpUser):
    """Simulates glossary service usage."""

    wait_time = between(1, 3)

    def on_start(self):
        """Create initial glossary."""
        # This would need a glossary service endpoint
        pass

    @task(5)
    def health_check(self):
        self.client.get("/health", catch_response=True)

    @task(3)
    def list_glossaries(self):
        self.client.get("/api/v1/glossaries?page=1&page_size=20", catch_response=True)

    @task(2)
    def search_glossary(self):
        if not hasattr(self, "glossary_id"):
            return
        self.client.get(
            f"/api/v1/glossaries/{self.glossary_id}/search",
            params={"query": random.choice(["test", "translation", "term", "slime", "goblin"])},
            catch_response=True,
        )

    @task(2)
    def build_pipeline(self):
        """Trigger glossary build pipeline."""
        payload = {
            "work_id": random.randint(1, 10),
            "volume_id": random.randint(1, 20),
            "text": "Test text for glossary extraction with terms like slime, goblin, mana, dragon.",
            "source_lang": "en",
            "target_lang": "es",
        }
        self.client.post("/api/v1/glossaries/build", json=payload, catch_response=True)

    @task(1)
    def list_pipelines(self):
        self.client.get("/api/v1/glossaries/pipelines", catch_response=True)

    @task(1)
    def pipeline_stages(self):
        """Test individual pipeline stages."""
        text_samples = [
            "The slime attacked the goblin with mana.",
            "The hero used a sword to defeat the dragon.",
            "Mana potions restore magical energy.",
        ]

        stages = [
            ("extract", {"text": random.choice(text_samples), "source_lang": "en", "min_frequency": 1}),
            ("filter", {"work_id": 1, "entities": []}),
            ("validate", {"entities": [], "source_lang": "en", "work_id": 1, "volume_id": 1}),
            ("embed", {"entities": []}),
            ("translate", {"entities": [], "source_lang": "en", "target_lang": "es"}),
            ("store", {"work_id": 1, "entities": [], "source_lang": "en", "target_lang": "es"}),
        ]

        stage, payload = random.choice(stages)
        self.client.post(f"/api/v1/glossaries/pipelines/stages/{stage}", json=payload, catch_response=True)


if __name__ == "__main__":
    from locust.env import Environment

    env = Environment(user_classes=[GlossaryUser])
    env.create_local_runner()
    env.runner.start(user_count=10, spawn_rate=2)
    env.runner.greenlet.join(timeout=30)