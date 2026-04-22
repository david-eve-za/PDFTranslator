"""Audio synthesizer implementations."""
from pdftranslator.infrastructure.audio.mac_say_synthesizer import MacSaySynthesizer  # noqa: F401
from pdftranslator.infrastructure.audio.ffmpeg_merger import merge_audio_files  # noqa: F401

__all__ = ["MacSaySynthesizer", "merge_audio_files"]
