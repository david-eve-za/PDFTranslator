"""Tests for document configuration."""

import pytest

from config.document import DoclingConfig


def test_docling_config_defaults():
    """Test DoclingConfig has correct default values."""
    config = DoclingConfig()
    assert config.enable_ocr is True
    assert config.ocr_languages == ["en", "es"]
    assert config.do_table_structure is False
    assert config.generate_page_images is False
    assert config.accelerator_device == "auto"


def test_docling_config_custom_values():
    """Test DoclingConfig accepts custom values."""
    config = DoclingConfig(
        enable_ocr=False, ocr_languages=["en", "fr", "de"], accelerator_device="cuda"
    )
    assert config.enable_ocr is False
    assert config.ocr_languages == ["en", "fr", "de"]
    assert config.accelerator_device == "cuda"


def test_docling_config_validates_accelerator_device():
    """Test DoclingConfig validates accelerator_device."""
    with pytest.raises(ValueError):
        DoclingConfig(accelerator_device="invalid")


def test_settings_includes_docling_config():
    """Test Settings includes DoclingConfig."""
    from config.settings import Settings

    settings = Settings()
    assert hasattr(settings, "document")
    assert isinstance(settings.document, DoclingConfig)
