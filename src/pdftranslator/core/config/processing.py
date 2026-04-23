"""Processing configuration models."""

from enum import Enum
from pydantic import BaseModel, Field
from pathlib import Path


class TTSEngine(str, Enum):
    """Available TTS engine backends."""

    MAC_SAY = "mac_say"
    MLX = "mlx"
    FISH_SPEECH = "fish_speech"


class ProcessingSettings(BaseModel):
    """Settings for PDF/audio processing workflow."""

    input_path: Path = Field(
        default=Path("."), description="Path to input file or directory"
    )
    source_lang: str = Field(default="en", description="Source language code")
    target_lang: str = Field(default="es", description="Target language code")
    output_format: str = Field(default="m4a", description="Audio output format")
    voice: str = Field(default="Paulina", description="macOS 'say' voice for TTS")
    gen_video: bool = Field(default=False, description="Generate video from audio")
    develop_mode: bool = Field(default=True, description="Enable development features")
    tts_engine: TTSEngine = Field(
        default=TTSEngine.MAC_SAY,
        description="TTS engine: mac_say, mlx, fish_speech",
    )
