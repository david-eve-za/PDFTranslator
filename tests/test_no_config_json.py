import os
import subprocess
import tempfile
import re
from pathlib import Path


def test_no_config_json_created():
    """Test that running PDFAgent.py does not create config.json file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Create a test PDF file
        test_pdf = tmpdir_path / "test.pdf"
        test_pdf.write_text("test content")

        # Run PDFAgent.py with input argument
        result = subprocess.run(
            ["python", "PDFAgent.py", str(test_pdf), "--agent", "gemini"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Verify config.json was not created
        config_file = tmpdir_path / "config.json"
        assert not config_file.exists(), (
            f"config.json should not exist, but found at {config_file}"
        )


def test_error_message_no_config_json_mention():
    """Test that error message doesn't mention config.json."""
    result = subprocess.run(
        ["python", "PDFAgent.py"], capture_output=True, text=True, timeout=5
    )

    # Check that "config.json" is NOT in error output
    error_output = result.stdout + result.stderr
    assert "config.json" not in error_output, (
        "Error message should not mention config.json"
    )
    assert "command-line argument" in error_output, (
        "Error should mention command-line argument"
    )
