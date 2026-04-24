"""Routes module."""

from pdftranslator.backend.api.routes import (
    chapters,
    files,
    glossary,
    settings,
    split,
    substitution_rules,
    translation,
    volumes,
    works,
)

__all__ = [
    "files",
    "glossary",
    "translation",
    "works",
    "volumes",
    "chapters",
    "split",
    "settings",
    "substitution_rules",
]
