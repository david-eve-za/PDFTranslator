"""Text Chunk Data Models.

CUPID Principle: Domain-Focused - Pure data models with invariants.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
from uuid import UUID, uuid4


@dataclass(frozen=True, slots=True)
class TextChunk:
    """A single text chunk with metadata.

    Invariants:
    - text is never empty
    - token_count > 0
    - sequence_number >= 0
    """

    text: str
    token_count: int
    sequence_number: int
    char_start: int
    char_end: int
    uuid: UUID = field(default_factory=uuid4)
    metadata: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.text or not self.text.strip():
            raise ValueError("text cannot be empty")
        if self.token_count <= 0:
            raise ValueError("token_count must be > 0")
        if self.sequence_number < 0:
            raise ValueError("sequence_number must be >= 0")
        if self.char_end <= self.char_start:
            raise ValueError("char_end must be > char_start")
        if len(self.text) != self.char_end - self.char_start:
            raise ValueError("text length must match char range")

    @classmethod
    def create(
        cls,
        text: str,
        token_count: int,
        sequence_number: int,
        char_start: int,
        metadata: Optional[dict] = None,
    ) -> TextChunk:
        """Factory method to create chunk with derived fields."""
        return cls(
            text=text,
            token_count=token_count,
            sequence_number=sequence_number,
            char_start=char_start,
            char_end=char_start + len(text),
            metadata=metadata or {},
        )


@dataclass(frozen=True, slots=True)
class ChunkResult:
    """Result of a chunking operation."""

    chunks: tuple[TextChunk, ...]
    total_chunks: int
    total_tokens: int
    total_chars: int
    config: "ChunkConfig"

    @classmethod
    def from_chunks(cls, chunks: list[TextChunk], config: "ChunkConfig") -> ChunkResult:
        return cls(
            chunks=tuple(chunks),
            total_chunks=len(chunks),
            total_tokens=sum(c.token_count for c in chunks),
            total_chars=sum(len(c.text) for c in chunks),
            config=config,
        )