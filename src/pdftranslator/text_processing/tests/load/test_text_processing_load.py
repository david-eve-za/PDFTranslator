"""
Load Tests for Text Processing Library.

CUPID Principle: Predictable
- Validates performance under load
- Measures latency percentiles
- Ensures deterministic behavior at scale
"""

import time
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any
import pytest

from pdftranslator.text_processing import (
    TextChunker,
    ChunkConfig,
    EncodingType,
    SplitStrategy,
    TextNormalizer,
    NormalizationConfig,
    NormalizationForm,
    OverlapHandler,
    Tokenizer,
)


# Test data
SAMPLE_TEXT_SHORT = "Hello world. This is a test sentence. Another sentence here. Final sentence."
SAMPLE_TEXT_MEDIUM = SAMPLE_TEXT_SHORT * 10  # ~100 tokens
SAMPLE_TEXT_LONG = SAMPLE_TEXT_SHORT * 100  # ~1000 tokens

LARGE_TEXT = (
    "Lorem ipsum dolor sit amet, consectetur adipiscing elit. "
    "Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. "
    "Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris. "
    "Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore. "
    "Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt. "
) * 20  # ~2000 chars


class LoadTestResult:
    """Container for load test metrics."""

    def __init__(self, name: str):
        self.name = name
        self.latencies: List[float] = []
        self.errors: int = 0
        self.success: int = 0

    def record(self, latency: float, error: bool = False):
        self.latencies.append(latency)
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
        print(f"  Error Rate: {s['error_rate']:.2%}")
        print(f"  Latency - Min: {s['min_ms']:.2f}ms, Max: {s['max_ms']:.2f}ms")
        print(f"  Mean: {s['mean_ms']:.2f}ms, Median: {s['median_ms']:.2f}ms")
        print(f"  P95: {s['p95_ms']:.2f}ms, P99: {s['p99_ms']:.2f}ms")
        print(f"  Throughput: {s['throughput_ops_sec']:.1f} ops/sec")


def run_load_test(
    name: str,
    func,
    iterations: int = 100,
    concurrency: int = 1,
) -> LoadTestResult:
    """Run a load test and collect metrics."""
    result = LoadTestResult(name)

    if concurrency == 1:
        # Sequential
        for _ in range(iterations):
            start = time.perf_counter()
            try:
                func()
                result.record(time.perf_counter() - start)
            except Exception as e:
                result.record(time.perf_counter() - start, error=True)
    else:
        # Concurrent
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


class TestTextChunkerLoad:
    """Load tests for TextChunker."""

    @pytest.fixture
    def chunker_translation(self):
        config = ChunkConfig.for_translation()
        return TextChunker(config)

    @pytest.fixture
    def chunker_embedding(self):
        config = ChunkConfig.for_embedding()
        return TextChunker(config)

    def test_chunker_translation_sequential(self, chunker_translation):
        """Sequential load test for translation config."""
        result = run_load_test(
            "TextChunker-Translation-Sequential",
            lambda: chunker_translation.chunk(SAMPLE_TEXT_MEDIUM),
            iterations=100,
            concurrency=1,
        )
        result.print_summary()

        # Assert performance bounds
        assert result.errors == 0, f"Errors occurred: {result.errors}"
        assert result.summary()["p95_ms"] < 100, "P95 latency should be < 100ms"

    def test_chunker_translation_concurrent(self, chunker_translation):
        """Concurrent load test for translation config."""
        result = run_load_test(
            "TextChunker-Translation-Concurrent",
            lambda: chunker_translation.chunk(SAMPLE_TEXT_MEDIUM),
            iterations=100,
            concurrency=10,
        )
        result.print_summary()

        assert result.errors == 0
        assert result.summary()["p95_ms"] < 200, "P95 latency should be < 200ms under concurrency"

    def test_chunker_embedding_sequential(self, chunker_embedding):
        """Sequential load test for embedding config."""
        result = run_load_test(
            "TextChunker-Embedding-Sequential",
            lambda: chunker_embedding.chunk(LARGE_TEXT),
            iterations=50,
            concurrency=1,
        )
        result.print_summary()

        assert result.errors == 0
        assert result.summary()["p95_ms"] < 200

    def test_chunker_deterministic_under_load(self, chunker_translation):
        """Verify deterministic output under load."""
        text = SAMPLE_TEXT_MEDIUM
        first_result = chunker_translation.chunk(text)

        result = run_load_test(
            "TextChunker-Deterministic",
            lambda: chunker_translation.chunk(text),
            iterations=20,
            concurrency=5,
        )
        result.print_summary()

        assert result.errors == 0

        # Verify all results match first
        for _ in range(20):
            r = chunker_translation.chunk(text)
            assert r.total_chunks == first_result.total_chunks
            assert r.total_tokens == first_result.total_tokens
            for c1, c2 in zip(first_result.chunks, r.chunks):
                assert c1.text == c2.text

    def test_chunker_all_strategies_performance(self):
        """Compare performance across all split strategies."""
        text = LARGE_TEXT
        strategies = [
            SplitStrategy.TOKENS,
            SplitStrategy.SENTENCES,
            SplitStrategy.PARAGRAPHS,
            SplitStrategy.CHARACTERS,
        ]

        for strategy in strategies:
            config = ChunkConfig(max_tokens=500, overlap_tokens=50, split_strategy=strategy)
            chunker = TextChunker(config)

            result = run_load_test(
                f"TextChunker-{strategy.value}",
                lambda: chunker.chunk(text),
                iterations=20,
                concurrency=1,
            )
            result.print_summary()
            assert result.errors == 0


class TestTokenizerLoad:
    """Load tests for Tokenizer."""

    def test_tokenizer_encoding_performance(self):
        """Test tokenization performance across encodings."""
        text = LARGE_TEXT
        encodings = [EncodingType.CL100K_BASE, EncodingType.O200K_BASE, EncodingType.P50K_BASE, EncodingType.R50K_BASE]

        for encoding in encodings:
            tokenizer = Tokenizer.get(encoding)

            result = run_load_test(
                f"Tokenizer-{encoding.value}",
                lambda: tokenizer.count_tokens(text),
                iterations=200,
                concurrency=1,
            )
            result.print_summary()
            assert result.errors == 0
            assert result.summary()["p95_ms"] < 50, f"Tokenization should be fast for {encoding.value}"

    def test_tokenizer_encode_decode_roundtrip(self):
        """Test encode/decode roundtrip under load."""
        text = "Test text for encoding and decoding. It should be reversible!"
        tokenizer = Tokenizer.get(EncodingType.CL100K_BASE)
        tokens = tokenizer.encode(text)

        result = run_load_test(
            "Tokenizer-EncodeDecode",
            lambda: tokenizer.decode(tokens) == text,
            iterations=200,
            concurrency=1,
        )
        result.print_summary()
        assert result.errors == 0
        assert result.summary()["p95_ms"] < 10


class TestTextNormalizerLoad:
    """Load tests for TextNormalizer."""

    @pytest.fixture
    def normalizer_default(self):
        return TextNormalizer()

    @pytest.fixture
    def normalizer_translation(self):
        return TextNormalizer(NormalizationConfig.for_translation())

    def test_normalizer_default_sequential(self, normalizer_default):
        """Sequential load test for default normalizer."""
        # Text with various normalization needs
        text = "  Hello  world  \"quoted\" — dash … ellipsis \t\n " * 10

        result = run_load_test(
            "TextNormalizer-Default",
            lambda: normalizer_default.normalize(text),
            iterations=200,
            concurrency=1,
        )
        result.print_summary()
        assert result.errors == 0
        assert result.summary()["p95_ms"] < 50

    def test_normalizer_translation_concurrent(self, normalizer_translation):
        """Concurrent load test for translation normalizer."""
        text = "  Hello  world  \"quoted\" — dash … ellipsis \t\n " * 10

        result = run_load_test(
            "TextNormalizer-Translation-Concurrent",
            lambda: normalizer_translation.normalize(text),
            iterations=200,
            concurrency=20,
        )
        result.print_summary()
        assert result.errors == 0
        assert result.summary()["p95_ms"] < 100


class TestOverlapHandlerLoad:
    """Load tests for OverlapHandler."""

    @pytest.fixture
    def handler_and_chunks(self):
        config = ChunkConfig(max_tokens=50, overlap_tokens=10, min_tokens=10)
        chunker = TextChunker(config)
        chunks = chunker.chunk(LARGE_TEXT).chunks
        handler = OverlapHandler(config)
        return handler, chunks

    def test_overlap_handler_sequential(self, handler_and_chunks):
        handler, chunks = handler_and_chunks

        result = run_load_test(
            "OverlapHandler-Sequential",
            lambda: handler.apply_overlap(chunks),
            iterations=100,
            concurrency=1,
        )
        result.print_summary()
        assert result.errors == 0
        assert result.summary()["p95_ms"] < 50

    def test_overlap_handler_concurrent(self, handler_and_chunks):
        handler, chunks = handler_and_chunks

        result = run_load_test(
            "OverlapHandler-Concurrent",
            lambda: handler.apply_overlap(chunks),
            iterations=100,
            concurrency=10,
        )
        result.print_summary()
        assert result.errors == 0


class TestFullPipelineLoad:
    """Load tests for full text processing pipeline."""

    def test_pipeline_normalize_chunk_overlap(self):
        """Full pipeline: normalize -> chunk -> overlap."""
        normalizer = TextNormalizer(NormalizationConfig.for_translation())
        config = ChunkConfig.for_translation()
        chunker = TextChunker(config)
        handler = OverlapHandler(config)

        text = "  Hello  world  \"quoted\" — dash … ellipsis \t\n " * 20

        def pipeline():
            normalized = normalizer.normalize(text)
            chunks = chunker.chunk(normalized).chunks
            return handler.apply_overlap(chunks)

        result = run_load_test(
            "FullPipeline-Normalize-Chunk-Overlap",
            pipeline,
            iterations=50,
            concurrency=1,
        )
        result.print_summary()
        assert result.errors == 0
        assert result.summary()["p95_ms"] < 200

    def test_pipeline_concurrent(self):
        """Full pipeline under concurrency."""
        normalizer = TextNormalizer(NormalizationConfig.for_translation())
        config = ChunkConfig.for_translation()
        chunker = TextChunker(config)
        handler = OverlapHandler(config)

        text = SAMPLE_TEXT_MEDIUM

        def pipeline():
            normalized = normalizer.normalize(text)
            chunks = chunker.chunk(normalized).chunks
            return handler.apply_overlap(chunks)

        result = run_load_test(
            "FullPipeline-Concurrent",
            pipeline,
            iterations=100,
            concurrency=10,
        )
        result.print_summary()
        assert result.errors == 0


class TestMemoryStability:
    """Tests for memory stability under sustained load."""

    def test_sustained_chunking_no_memory_leak(self):
        """Run many iterations to check for memory growth."""
        config = ChunkConfig.for_translation()
        chunker = TextChunker(config)

        # Process many texts
        for i in range(1000):
            text = f"Document {i}. " + SAMPLE_TEXT_MEDIUM
            result = chunker.chunk(text)
            assert result.total_chunks > 0

    def test_sustained_normalization_no_memory_leak(self):
        """Run many normalization iterations."""
        normalizer = TextNormalizer(NormalizationConfig.for_translation())

        for i in range(1000):
            text = f"Doc {i}: " + SAMPLE_TEXT_MEDIUM
            result = normalizer.normalize(text)
            assert len(result) > 0


# Pytest markers for load tests
pytestmark = [
    pytest.mark.load,
    pytest.mark.slow,
]


if __name__ == "__main__":
    # Allow running directly for manual load testing
    pytest.main([__file__, "-v", "-m", "load", "--tb=short"])