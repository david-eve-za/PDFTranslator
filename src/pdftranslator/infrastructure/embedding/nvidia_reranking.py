"""NVIDIA reranking provider — implements RerankingProvider protocol."""
from __future__ import annotations

from langchain_core.documents import Document
from langchain_nvidia_ai_endpoints import NVIDIARerank

from pdftranslator.core.config.settings import Settings


class NvidiaRerankingProvider:
    """NVIDIA NIM-based reranking provider."""

    def __init__(self, settings: Settings | None = None):
        self._settings = settings or Settings.get()
        self._reranker: NVIDIARerank | None = None

    @property
    def reranker(self) -> NVIDIARerank:
        if self._reranker is None:
            nvidia = self._settings.llm.nvidia
            self._reranker = NVIDIARerank(
                model=nvidia.rerank_model,
                api_key=self._settings.llm.nvidia_api_key,
                top_n=nvidia.rerank_top_n,
            )
        return self._reranker

    def rerank(
        self, query: str, documents: list[Document], top_n: int = 5
    ) -> list[Document]:
        if not documents:
            return []
        reranker = NVIDIARerank(
            model=self._settings.llm.nvidia.rerank_model,
            api_key=self._settings.llm.nvidia_api_key,
            top_n=top_n,
        )
        return reranker.compress_documents(documents=documents, query=query)
