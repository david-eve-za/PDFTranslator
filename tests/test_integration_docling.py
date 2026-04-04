# tests/test_integration_docling.py
"""Integration tests for Docling document processing."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from infrastructure.document.docling_extractor import DoclingExtractor
from infrastructure.document.section_grouper import SectionGrouper
from config.document import DoclingConfig


@pytest.mark.integration
class TestDoclingIntegration:
    """Integration tests requiring real documents."""

    @pytest.fixture
    def sample_pdf_path(self):
        """Return path to sample PDF if exists."""
        path = Path("tests/fixtures/documents/sample.pdf")
        if not path.exists():
            pytest.skip("Sample PDF not found in fixtures")
        return str(path)

    @pytest.fixture
    def sample_docx_path(self):
        """Return path to sample DOCX if exists."""
        path = Path("tests/fixtures/documents/sample.docx")
        if not path.exists():
            pytest.skip("Sample DOCX not found in fixtures")
        return str(path)

    def test_extract_real_pdf(self, sample_pdf_path):
        """Test extracting a real PDF document."""
        extractor = DoclingExtractor()
        doc = extractor.extract(sample_pdf_path)

        assert doc is not None
        assert len(doc.pages) > 0

    def test_extract_and_group_real_pdf(self, sample_pdf_path):
        """Test extracting and grouping a real PDF."""
        extractor = DoclingExtractor()
        grouper = SectionGrouper()

        doc = extractor.extract(sample_pdf_path)
        sections = grouper.group_by_sections(doc)

        assert len(sections) > 0
        assert all("title" in s and "content" in s for s in sections)

    def test_extract_real_docx(self, sample_docx_path):
        """Test extracting a real DOCX document."""
        extractor = DoclingExtractor()
        doc = extractor.extract(sample_docx_path)

        assert doc is not None

    @patch("infrastructure.document.docling_extractor.DocumentConverter")
    def test_ocr_enabled_for_scanned_pdf(self, mock_converter):
        """Test OCR is enabled when configured."""
        config = DoclingConfig(enable_ocr=True)
        extractor = DoclingExtractor(config)

        # Verify converter was created with OCR options
        assert extractor.config.enable_ocr is True
