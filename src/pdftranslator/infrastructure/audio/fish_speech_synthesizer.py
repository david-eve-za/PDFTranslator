"""FishSpeechSynthesizer — implements AudioSynthesizer protocol using Fish Speech TTS.

Resolves OCP-4: New TTS backend added without modifying existing code.
Uses Fish Speech API for remote TTS synthesis.
"""
from __future__ import annotations

import logging
from pathlib import Path

from pdftranslator.infrastructure.audio.ffmpeg_merger import merge_audio_files

logger = logging.getLogger(__name__)


class FishSpeechSynthesizer:
    """Fish Speech TTS synthesizer.

    Uses the Fish Speech API/server for TTS synthesis.
    Requires a running Fish Speech server endpoint.
    """

    def __init__(
        self,
        server_url: str = "http://localhost:8080",
        api_key: str | None = None,
        settings=None,
    ):
        self._server_url = server_url.rstrip("/")
        self._api_key = api_key
        self._settings = settings

    @property
    def is_available(self) -> bool:
        try:
            import requests

            try:
                resp = requests.get(f"{self._server_url}/health", timeout=3)
                return resp.status_code == 200
            except Exception:
                return False
        except ImportError:
            logger.debug("requests not installed, FishSpeechSynthesizer unavailable")
            return False

    @property
    def name(self) -> str:
        return "fish_speech"

    def synthesize(
        self,
        text: str,
        output_path: Path,
        voice: str = "default",
        speed: float = 1.0,
        language: str = "es",
    ) -> bool:
        if not text or not text.strip():
            logger.warning("Input text is empty. Skipping audio generation.")
            return False

        try:
            import requests

            output_path.parent.mkdir(parents=True, exist_ok=True)

            headers = {"Content-Type": "application/json"}
            if self._api_key:
                headers["Authorization"] = f"Bearer {self._api_key}"

            payload = {
                "text": text,
                "voice": voice,
                "speed": speed,
                "language": language,
            }

            resp = requests.post(
                f"{self._server_url}/v1/tts",
                json=payload,
                headers=headers,
                timeout=300,
            )
            resp.raise_for_status()

            with open(output_path, "wb") as f:
                f.write(resp.content)

            logger.info(f"Fish Speech audio saved: {output_path}")
            return True

        except ImportError:
            logger.error(
                "requests package not installed. Install with: pip install requests"
            )
            return False
        except Exception as e:
            logger.error(f"Error in Fish Speech TTS synthesis: {e}", exc_info=True)
            return False

    def merge_audio(
        self,
        audio_files: list[Path],
        output_path: Path,
    ) -> bool:
        if not audio_files:
            return False
        try:
            return merge_audio_files(audio_files, output_path)
        except Exception as e:
            logger.error(f"Error merging audio files: {e}", exc_info=True)
            return False
