"""Path configuration models."""

from pathlib import Path
from pydantic import BaseModel, Field


def _get_project_root() -> Path:
    """Get the project root directory."""
    # This file is at src/pdftranslator/core/config/paths.py
    # Project root is 4 levels up from this file
    return Path(__file__).resolve().parents[4]


class PathSettings(BaseModel):
    """Application path settings."""

    base_dir: Path = Field(default_factory=_get_project_root)
    audiobooks_dir: Path = Field(default_factory=lambda: Path("audiobooks"))
    videos_dir: Path = Field(default_factory=lambda: Path("videos"))
    translation_prompt_path: Path = Field(
        default_factory=lambda: (
            _get_project_root()
            / "src"
            / "pdftranslator"
            / "tools"
            / "translation_prompt.txt"
        )
    )
    tokenizer_path: Path = Field(
        default_factory=lambda: (
            Path.home() / ".cache" / "sentencepiece" / "tokenizer.model"
        )
    )

    def ensure_directories(self) -> None:
        """Create output directories if they don't exist."""
        self.audiobooks_dir.mkdir(parents=True, exist_ok=True)
        self.videos_dir.mkdir(parents=True, exist_ok=True)
