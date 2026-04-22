"""Document parser protocol.

Resolves DIP-7: Consumers should not depend on specific
document extraction implementations.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class DocumentParser(Protocol):
    """Interface for document text extraction."""

    @property
    def supported_extensions(self) -> set[str]:
        """File extensions this parser supports (e.g., {'.pdf', '.epub'})."""
        ...

    def parse(self, file_path: str) -> str | None:
        """Extract text from a document file.

        Returns None if extraction fails.
        """
        ...
