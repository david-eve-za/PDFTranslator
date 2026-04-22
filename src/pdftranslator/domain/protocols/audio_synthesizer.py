"""Audio synthesizer protocol.

Resolves OCP-4 and SRP-7: TTS backends should be swappable
without modifying existing code.
"""
from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable


@runtime_checkable
class AudioSynthesizer(Protocol):
    """Interface for text-to-speech synthesis."""

    @property
    def is_available(self) -> bool:
        """Check if this engine is available on the current system."""
        ...

    @property
    def name(self) -> str:
        """Engine name for logging and configuration."""
        ...

    def synthesize(
        self,
        text: str,
        output_path: Path,
        voice: str = "default",
        speed: float = 1.0,
        language: str = "es",
    ) -> bool:
        """Synthesize text to audio file. Returns True on success."""
        ...

    def merge_audio(
        self,
        audio_files: list[Path],
        output_path: Path,
    ) -> bool:
        """Merge multiple audio files into one. Returns True on success."""
        ...
