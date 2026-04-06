"""Path configuration models."""

from pathlib import Path
from pydantic import BaseModel, Field


class PathSettings(BaseModel):
    """Application path settings."""

    base_dir: Path = Field(default_factory=lambda: Path.cwd())
    audiobooks_dir: Path = Field(default_factory=lambda: Path("audiobooks"))
    videos_dir: Path = Field(default_factory=lambda: Path("videos"))
    translation_prompt_path: Path = Field(
        default_factory=lambda: Path("tools/translation_prompt.txt")
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
