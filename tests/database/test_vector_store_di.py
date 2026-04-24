"""Tests that VectorStoreService accepts injected providers."""
from unittest.mock import MagicMock

from pdftranslator.database.services.vector_store import VectorStoreService
from pdftranslator.domain.protocols.embedding import EmbeddingProvider


def test_vector_store_accepts_injected_embedder():
    mock_embedder = MagicMock(spec=EmbeddingProvider)
    mock_embedder.embed_query.return_value = [0.1, 0.2, 0.3]
    mock_embedder.embed_documents.return_value = [[0.1, 0.2, 0.3]]
    service = VectorStoreService(embedder=mock_embedder)
    result = service.embed_query("test")
    assert result == [0.1, 0.2, 0.3]


def test_vector_store_uses_injected_embedder_for_documents():
    mock_embedder = MagicMock(spec=EmbeddingProvider)
    mock_embedder.embed_documents.return_value = [[0.1, 0.2], [0.3, 0.4]]
    service = VectorStoreService(embedder=mock_embedder)
    result = service.embed_documents(["doc1", "doc2"])
    assert result == [[0.1, 0.2], [0.3, 0.4]]
