from typing import List, Optional
import numpy as np
from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings, NVIDIARerank
from langchain_core.documents import Document
from GlobalConfig import GlobalConfig


class VectorStoreService:
    """
    Servicio interno para embeddings y reranking usando NVIDIA NIM.
    Encapsula completamente la funcionalidad de NVIDIA NIM dentro del módulo database.
    Este servicio es usado internamente por los repositorios y no se exporta.
    """

    def __init__(self):
        self._config = GlobalConfig()
        self._embedder: Optional[NVIDIAEmbeddings] = None
        self._reranker: Optional[NVIDIARerank] = None

    @property
    def embedder(self) -> NVIDIAEmbeddings:
        """Lazy initialization del embedder"""
        if self._embedder is None:
            self._embedder = NVIDIAEmbeddings(
                model=self._config.nvidia_embed_model,
                api_key=self._config.nvidia_nim_api_key,
            )
        return self._embedder

    @property
    def reranker(self) -> NVIDIARerank:
        """Lazy initialization del reranker"""
        if self._reranker is None:
            self._reranker = NVIDIARerank(
                model=self._config.nvidia_rerank_model,
                api_key=self._config.nvidia_nim_api_key,
                top_n=self._config.nvidia_rerank_top_n,
            )
        return self._reranker

    def embed_query(self, text: str) -> List[float]:
        """
        Genera embedding para una consulta.

        Args:
            text: Texto de la consulta

        Returns:
            Lista de floats representando el embedding
        """
        return self.embedder.embed_query(text)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Genera embeddings para múltiples documentos.

        Args:
            texts: Lista de textos a embeddear

        Returns:
            Lista de embeddings
        """
        return self.embedder.embed_documents(texts)

    def rerank_documents(
        self, query: str, documents: List[Document], top_n: Optional[int] = None
    ) -> List[Document]:
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

        reranker = NVIDIARerank(
            model=self._config.nvidia_rerank_model,
            api_key=self._config.nvidia_nim_api_key,
            top_n=top_n or self._config.nvidia_rerank_top_n,
        )
        return reranker.compress_documents(documents=documents, query=query)

    def cosine_similarity(
        self, query_embedding: List[float], doc_embeddings: List[List[float]]
    ) -> List[float]:
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
        query_embedding: List[float],
        doc_embeddings: List[List[float]],
        top_k: int = 5,
    ) -> List[int]:
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
