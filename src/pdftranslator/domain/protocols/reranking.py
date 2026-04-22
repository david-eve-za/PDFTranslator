"""Reranking provider protocol.

Resolves ISP-3: Reranking is a separate concern from embedding.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from langchain_core.documents import Document


@runtime_checkable
class RerankingProvider(Protocol):
    """Interface for document reranking services."""

    def rerank(
        self, query: str, documents: list[Document], top_n: int = 5
    ) -> list[Document]:
        """Rerank documents by relevance to query."""
        ...
