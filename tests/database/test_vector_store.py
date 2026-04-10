import pytest
from unittest.mock import MagicMock, patch
from langchain_core.documents import Document


@patch("src.database.services.vector_store.NVIDIAEmbeddings")
@patch("src.database.services.vector_store.Settings")
def test_embed_query(mock_settings_class, mock_embeddings_class):
    mock_config = MagicMock()
    mock_config.llm.nvidia.embed_model = "test-model"
    mock_config.llm.nvidia_api_key = "test-key"
    mock_settings_class.get.return_value = mock_config

    mock_embedder = MagicMock()
    mock_embedder.embed_query.return_value = [0.1, 0.2, 0.3]
    mock_embeddings_class.return_value = mock_embedder

    from src.database.services.vector_store import VectorStoreService

    service = VectorStoreService()
    result = service.embed_query("test query")
    assert result == [0.1, 0.2, 0.3]


@patch("src.database.services.vector_store.NVIDIAEmbeddings")
@patch("src.database.services.vector_store.Settings")
def test_embed_documents(mock_settings_class, mock_embeddings_class):
    mock_config = MagicMock()
    mock_config.llm.nvidia.embed_model = "test-model"
    mock_config.llm.nvidia_api_key = "test-key"
    mock_settings_class.get.return_value = mock_config

    mock_embedder = MagicMock()
    mock_embedder.embed_documents.return_value = [[0.1, 0.2], [0.3, 0.4]]
    mock_embeddings_class.return_value = mock_embedder

    from src.database.services.vector_store import VectorStoreService

    service = VectorStoreService()
    result = service.embed_documents(["doc1", "doc2"])
    assert result == [[0.1, 0.2], [0.3, 0.4]]


@patch("src.database.services.vector_store.NVIDIARerank")
@patch("src.database.services.vector_store.Settings")
def test_rerank_documents(mock_settings_class, mock_rerank_class):
    mock_config = MagicMock()
    mock_config.llm.nvidia.rerank_model = "test-model"
    mock_config.llm.nvidia.rerank_top_n = 5
    mock_config.llm.nvidia_api_key = "test-key"
    mock_settings_class.get.return_value = mock_config

    docs = [Document(page_content="doc1"), Document(page_content="doc2")]
    mock_reranker = MagicMock()
    mock_reranker.compress_documents.return_value = [docs[0]]
    mock_rerank_class.return_value = mock_reranker

    from src.database.services.vector_store import VectorStoreService

    service = VectorStoreService()
    result = service.rerank_documents("query", docs)
    assert len(result) == 1
    assert result[0].page_content == "doc1"


@patch("src.database.services.vector_store.Settings")
def test_cosine_similarity(mock_settings_class):
    mock_config = MagicMock()
    mock_config.llm.nvidia_api_key = "test-key"
    mock_settings_class.get.return_value = mock_config

    from src.database.services.vector_store import VectorStoreService

    service = VectorStoreService()
    query = [1.0, 0.0, 0.0]
    docs = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.5, 0.5, 0.0]]
    similarities = service.cosine_similarity(query, docs)
    assert similarities[0] == pytest.approx(1.0)
    assert similarities[1] == pytest.approx(0.0)
    assert similarities[2] == pytest.approx(0.707, abs=0.01)


@patch("src.database.services.vector_store.Settings")
def test_find_most_similar(mock_settings_class):
    mock_config = MagicMock()
    mock_config.llm.nvidia_api_key = "test-key"
    mock_settings_class.get.return_value = mock_config

    from src.database.services.vector_store import VectorStoreService

    service = VectorStoreService()
    query = [1.0, 0.0]
    docs = [[0.0, 1.0], [1.0, 0.0], [0.5, 0.5]]
    indices = service.find_most_similar(query, docs, top_k=2)
    assert indices == [1, 2]


@patch("src.database.services.vector_store.Settings")
def test_rerank_empty_documents(mock_settings_class):
    mock_config = MagicMock()
    mock_config.llm.nvidia_api_key = "test-key"
    mock_settings_class.get.return_value = mock_config

    from src.database.services.vector_store import VectorStoreService

    service = VectorStoreService()
    result = service.rerank_documents("query", [])
    assert result == []
