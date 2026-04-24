import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from tools.TextExtractor import TextExtractor


def test_extract_text_returns_string_not_tuple():
    """Test that extract_text returns str, not Tuple[str, List[Path]]."""
    extractor = TextExtractor()

    # Mock a simple PDF
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        # We'll mock the actual extraction since PDF parsing is complex
        with patch.object(extractor, "_extract_from_pdf") as mock_extract:
            mock_extract.return_value = "test text"
            result = extractor.extract_text(tmp_path)

            # Verify result is string, not tuple
            assert isinstance(result, str)
            assert result == "test text"
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_no_image_extraction_occurs():
    """Test that no image extraction directories are created."""
    extractor = TextExtractor()

    with tempfile.TemporaryDirectory() as tmpdir:
        test_pdf = Path(tmpdir) / "test.pdf"
        test_pdf.write_text("dummy content")

        # Mock the PDF extraction to return text
        with patch.object(extractor, "_extract_from_pdf") as mock_extract:
            mock_extract.return_value = "test text"
            result = extractor.extract_text(str(test_pdf))

            # Verify no images directory was created
            images_dir = test_pdf.parent / f"images_{test_pdf.stem}"
            assert not images_dir.exists(), (
                f"Image directory {images_dir} should not exist"
            )


def test_extract_text_error_returns_none():
    """Test that extract_text returns None on error."""
    extractor = TextExtractor()

    # Test with non-existent file
    result = extractor.extract_text("/non/existent/file.pdf")
    assert result is None, "Should return None for non-existent file"
