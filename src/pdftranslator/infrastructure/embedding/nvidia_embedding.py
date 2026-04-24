"""NVIDIA embedding provider — implements EmbeddingProvider protocol.

Resolves DIP-2: Embedding logic decoupled from VectorStoreService.
"""
from __future__ import annotations

from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings

from pdftranslator.core.config.settings import Settings


class NvidiaEmbeddingProvider:
    """NVIDIA NIM-based embedding provider."""

    def __init__(self, settings: Settings | None = None):
        self._settings = settings or Settings.get()
        self._embedder: NVIDIAEmbeddings | None = None

    @property
    def embedder(self) -> NVIDIAEmbeddings:
        if self._embedder is None:
            nvidia_config = self._settings.llm.nvidia
            self._embedder = NVIDIAEmbeddings(
                model=nvidia_config.embed_model,
                api_key=self._settings.llm.nvidia_api_key,
            )
        return self._embedder

    def embed_query(self, text: str) -> list[float]:
        return self.embedder.embed_query(text)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self.embedder.embed_documents(texts)
