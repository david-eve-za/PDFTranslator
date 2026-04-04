"""Tests for DoclingExtractor."""

import pytest
from unittest.mock import MagicMock, patch
from docling_core.types.doc import DoclingDocument

from infrastructure.document.docling_extractor import DoclingExtractor
from config.document import DoclingConfig


def test_docling_extractor_initializes_with_defaults():
    """Test DoclingExtractor initializes with default config."""
    extractor = DoclingExtractor()
    assert extractor.config is not None
    assert isinstance(extractor.config, DoclingConfig)


def test_docling_extractor_initializes_with_custom_config():
    """Test DoclingExtractor accepts custom config."""
    config = DoclingConfig(enable_ocr=False, accelerator_device="cpu")
    extractor = DoclingExtractor(config=config)
    assert extractor.config.enable_ocr is False
    assert extractor.config.accelerator_device == "cpu"


def test_docling_extractor_creates_converter():
    """Test DoclingExtractor creates DocumentConverter."""
    extractor = DoclingExtractor()
    assert extractor._converter is not None


@patch("infrastructure.document.docling_extractor.DocumentConverter")
@patch("infrastructure.document.docling_extractor.Path")
def test_docling_extractor_extract_returns_document(mock_path, mock_converter_class):
    """Test extract() returns DoclingDocument."""
    # Setup mock path
    mock_path_instance = MagicMock()
    mock_path_instance.exists.return_value = True
    mock_path_instance.suffix = ".pdf"
    mock_path_instance.__str__ = lambda self: "test.pdf"
    mock_path.return_value = mock_path_instance

    # Setup mock converter
    mock_doc = MagicMock(spec=DoclingDocument)
    mock_doc.pages = [MagicMock(), MagicMock()]
    mock_result = MagicMock()
    mock_result.document = mock_doc
    mock_converter_instance = MagicMock()
    mock_converter_instance.convert.return_value = mock_result
    mock_converter_class.return_value = mock_converter_instance

    # Execute
    extractor = DoclingExtractor()
    doc = extractor.extract("test.pdf")

    # Assert
    assert isinstance(doc, DoclingDocument)
    mock_converter_instance.convert.assert_called_once()
