"""Embedding provider protocol.

Resolves OCP-3 and ISP-3: Embedding logic should be swappable
and consumers should only depend on what they need.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Interface for text embedding services."""

    def embed_query(self, text: str) -> list[float]:
        """Generate embedding for a single text."""
        ...

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts."""
        ...
