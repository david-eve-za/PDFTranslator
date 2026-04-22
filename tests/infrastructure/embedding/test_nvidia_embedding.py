"""Tests for NvidiaEmbeddingProvider protocol compliance."""
from pdftranslator.domain.protocols.embedding import EmbeddingProvider
from pdftranslator.infrastructure.embedding.nvidia_embedding import NvidiaEmbeddingProvider


def test_nvidia_embedding_satisfies_protocol():
    provider = NvidiaEmbeddingProvider.__new__(NvidiaEmbeddingProvider)
    assert isinstance(provider, EmbeddingProvider)
