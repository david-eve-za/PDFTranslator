"""Tests for NvidiaRerankingProvider protocol compliance."""
from pdftranslator.domain.protocols.reranking import RerankingProvider
from pdftranslator.infrastructure.embedding.nvidia_reranking import NvidiaRerankingProvider


def test_nvidia_reranking_satisfies_protocol():
    provider = NvidiaRerankingProvider.__new__(NvidiaRerankingProvider)
    assert isinstance(provider, RerankingProvider)
