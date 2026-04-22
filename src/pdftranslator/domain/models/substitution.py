"""Domain model for text substitution rules.

Maps from SQL schema: text_substitution_rules -> SubstitutionRule
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class SubstitutionRule:
    id: int | None = None
    name: str = ""
    pattern: str = ""
    replacement: str = ""
    description: str | None = None
    is_active: bool = True
    apply_on_extract: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None
