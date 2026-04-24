
import numpy as np
from langchain_core.documents import Document
from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings, NVIDIARerank

from pdftranslator.core.config.settings import Settings
from pdftranslator.domain.protocols.embedding import EmbeddingProvider
from pdftranslator.domain.protocols.reranking import RerankingProvider


class VectorStoreService:
    """
    Servicio interno para embeddings y reranking usando NVIDIA NIM.
    Encapsula completamente la funcionalidad de NVIDIA NIM dentro del módulo database.
    Este servicio es usado internamente por los repositorios y no se exporta.

    Now accepts optional injected providers for DIP-2 compliance.
    """

    def __init__(
        self,
        embedder: EmbeddingProvider | None = None,
        reranker: RerankingProvider | None = None,
    ):
        self._injected_embedder = embedder
        self._injected_reranker = reranker
        self._config = Settings.get()
        self._embedder: NVIDIAEmbeddings | None = None
        self._reranker: NVIDIARerank | None = None

    @property
    def _nvidia(self):
        """Convenience accessor for NVIDIA config"""
        return self._config.llm.nvidia

    @property
    def embedder(self):
        """Lazy initialization del embedder, or use injected provider"""
        if self._injected_embedder is not None:
            return self._injected_embedder
        if self._embedder is None:
            self._embedder = NVIDIAEmbeddings(
                model=self._nvidia.embed_model,
                api_key=self._config.llm.nvidia_api_key,
            )
        return self._embedder

    @property
    def reranker(self):
        """Lazy initialization del reranker, or use injected provider"""
        if self._injected_reranker is not None:
            return self._injected_reranker
        if self._reranker is None:
            self._reranker = NVIDIARerank(
                model=self._nvidia.rerank_model,
                api_key=self._config.llm.nvidia_api_key,
                top_n=self._nvidia.rerank_top_n,
            )
        return self._reranker

    def embed_query(self, text: str) -> list[float]:
        """
        Genera embedding para una consulta.

        Args:
            text: Texto de la consulta

        Returns:
            Lista de floats representando el embedding
        """
        return self.embedder.embed_query(text)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """
        Genera embeddings para múltiples documentos.

        Args:
            texts: Lista de textos a embeddear

        Returns:
            Lista de embeddings
        """
        return self.embedder.embed_documents(texts)

    def rerank_documents(
        self, query: str, documents: list[Document], top_n: int | None = None
    ) -> list[Document]:
        """
        Rerankear documentos basado en relevancia con la query.

        Args:
            query: Consulta original
            documents: Lista de documentos a rerankear
            top_n: Número máximo de documentos a retornar (default: config)

        Returns:
            Lista de documentos ordenados por relevancia
        """
        if not documents:
            return []

        if self._injected_reranker is not None:
            return self._injected_reranker.rerank(query, documents, top_n=top_n or self._nvidia.rerank_top_n)

        reranker = NVIDIARerank(
            model=self._nvidia.rerank_model,
            api_key=self._config.llm.nvidia_api_key,
            top_n=top_n or self._nvidia.rerank_top_n,
        )
        return reranker.compress_documents(documents=documents, query=query)

    def cosine_similarity(
        self, query_embedding: list[float], doc_embeddings: list[list[float]]
    ) -> list[float]:
        """
        Calcula similitud coseno entre un embedding de consulta y múltiples documentos.

        Args:
            query_embedding: Embedding de la consulta
            doc_embeddings: Lista de embeddings de documentos

        Returns:
            Lista de similitudes (valores entre -1 y 1)
        """
        query_vec = np.array(query_embedding)
        doc_vecs = np.array(doc_embeddings)

        if len(doc_vecs.shape) == 1:
            doc_vecs = doc_vecs.reshape(1, -1)

        query_norm = query_vec / np.linalg.norm(query_vec)
        doc_norms = doc_vecs / np.linalg.norm(doc_vecs, axis=1, keepdims=True)
        similarities = np.dot(doc_norms, query_norm)

        return similarities.tolist()

    def find_most_similar(
        self,
        query_embedding: list[float],
        doc_embeddings: list[list[float]],
        top_k: int = 5,
    ) -> list[int]:
        """
        Encuentra los índices de los documentos más similares a la consulta.

        Args:
            query_embedding: Embedding de la consulta
            doc_embeddings: Lista de embeddings de documentos
            top_k: Número de resultados a retornar

        Returns:
            Lista de índices ordenados por similitud descendente
        """
        similarities = self.cosine_similarity(query_embedding, doc_embeddings)
        indexed_sims = list(enumerate(similarities))
        indexed_sims.sort(key=lambda x: x[1], reverse=True)
        return [idx for idx, _ in indexed_sims[:top_k]]

    def embed_entities_for_glossary(
        self,
        entities: list,
    ) -> list[tuple]:
        """
        Genera embeddings para entidades candidatas.
        El texto a embeddear combina: término + tipo + contexto

        Args:
            entities: Lista de EntityCandidate

        Returns:
            Lista de tuplas (EntityCandidate, embedding)
        """
        if not entities:
            return []
        texts = [f"{e.text} {e.entity_type} {e.best_context()}" for e in entities]
        embeddings = self.embedder.embed_documents(texts)
        return list(zip(entities, embeddings, strict=False))
