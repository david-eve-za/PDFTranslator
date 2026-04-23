"""Tests for TTS engine configuration."""
from pdftranslator.core.config.processing import ProcessingSettings, TTSEngine


def test_default_tts_engine_is_mac_say():
    settings = ProcessingSettings()
    assert settings.tts_engine == TTSEngine.MAC_SAY


def test_tts_engine_enum_values():
    assert TTSEngine.MAC_SAY.value == "mac_say"
    assert TTSEngine.MLX.value == "mlx"
    assert TTSEngine.FISH_SPEECH.value == "fish_speech"


def test_tts_engine_from_string():
    settings = ProcessingSettings(tts_engine="mlx")
    assert settings.tts_engine == TTSEngine.MLX
