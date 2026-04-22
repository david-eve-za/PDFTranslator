"""Tests for MacSaySynthesizer protocol compliance."""
from pdftranslator.domain.protocols.audio_synthesizer import AudioSynthesizer
from pdftranslator.infrastructure.audio.mac_say_synthesizer import MacSaySynthesizer


def test_mac_say_satisfies_protocol():
    synth = MacSaySynthesizer.__new__(MacSaySynthesizer)
    assert isinstance(synth, AudioSynthesizer)


def test_mac_say_name():
    synth = MacSaySynthesizer.__new__(MacSaySynthesizer)
    assert synth.name == "mac_say"


def test_mac_say_is_available_check():
    synth = MacSaySynthesizer.__new__(MacSaySynthesizer)
    result = synth.is_available
    assert isinstance(result, bool)
