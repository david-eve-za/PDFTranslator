"""
Glossary Reference Value Object.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class GlossaryReference:
    """
    Immutable reference to a glossary used in translation.

    Value Object - compared by value, not identity.
    """

    glossary_id: int
    name: str
    source_lang: str
    target_lang: str
    priority: int = 0  # Higher = more important
    entry_count: int = 0

    def __post_init__(self) -> None:
        if self.glossary_id <= 0:
            raise ValueError("Glossary ID must be positive")
        if not self.name.strip():
            raise ValueError("Glossary name cannot be empty")
        if len(self.source_lang) != 2 or len(self.target_lang) != 2:
            raise ValueError("Languages must be ISO 639-1 codes")