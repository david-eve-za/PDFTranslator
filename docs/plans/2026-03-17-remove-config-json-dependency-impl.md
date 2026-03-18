# Remove config.json Dependency Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Remove dependency on config.json file from application execution, using only GlobalConfig.py defaults and CLI args.

**Architecture:** Eliminate load() and save() calls from PDFAgent.py, use only defaults + CLI args via update_from_args().

**Tech Stack:** Python, argparse, GlobalConfig singleton

---

## Task 1: Remove CONFIG_FILE_NAME constant

**Files:**
- Modify: `PDFAgent.py:24`

**Step 1: Open PDFAgent.py**

Read current content around line 24.

**Step 2: Remove CONFIG_FILE_NAME constant**

Delete line 24:
```python
CONFIG_FILE_NAME = "config.json"
```

**Step 3: Verify file compiles**

Run: `python -m py_compile PDFAgent.py`
Expected: No errors

**Step 4: Commit**

```bash
git add PDFAgent.py
git commit -m "refactor: remove CONFIG_FILE_NAME constant"
```

---

## Task 2: Remove config.load() call and error handling

**Files:**
- Modify: `PDFAgent.py:263-270`

**Step 1: Identify the load block**

Find the try/except block that calls `config.load(CONFIG_FILE_NAME)`.

**Step 2: Remove the entire load block**

Delete lines 263-270:
```python
try:
    config.load(CONFIG_FILE_NAME)
    logging.info(f"Loaded configuration from {CONFIG_FILE_NAME}")
except FileNotFoundError:
    logging.info(f"{CONFIG_FILE_NAME} not found. Using default settings and command-line arguments.")
except ValueError as e:
    logging.error(f"Error loading {CONFIG_FILE_NAME}: {e}. Please check the file format.")
    return
```

**Step 3: Verify file compiles**

Run: `python -m py_compile PDFAgent.py`
Expected: No errors

**Step 4: Commit**

```bash
git add PDFAgent.py
git commit -m "refactor: remove config.load() call and error handling"
```

---

## Task 3: Remove config.save() call

**Files:**
- Modify: `PDFAgent.py:280-282`

**Step 1: Identify the save block**

Find the lines that call `config.save(CONFIG_FILE_NAME)`.

**Step 2: Remove the save block**

Delete lines 280-282:
```python
# --- Save final config ---
config.save(CONFIG_FILE_NAME)
logging.info(f"Final configuration saved to {CONFIG_FILE_NAME}")
```

**Step 3: Verify file compiles**

Run: `python -m py_compile PDFAgent.py`
Expected: No errors

**Step 4: Commit**

```bash
git add PDFAgent.py
git commit -m "refactor: remove config.save() call"
```

---

## Task 4: Update error message for missing input_path

**Files:**
- Modify: `PDFAgent.py:275`

**Step 1: Find the error message**

Locate the line that mentions "config.json" in the error logging.

**Step 2: Update the message**

Replace:
```python
logging.error("Input path is not specified in config.json or as a command-line argument. Exiting.")
```

With:
```python
logging.error("Input path is not specified as a command-line argument. Exiting.")
```

**Step 3: Verify file compiles**

Run: `python -m py_compile PDFAgent.py`
Expected: No errors

**Step 4: Commit**

```bash
git add PDFAgent.py
git commit -m "refactor: update error message to remove config.json reference"
```

---

## Task 5: Test without input_path

**Files:**
- Modify: None (test)

**Step 1: Run without arguments**

Run: `python PDFAgent.py`
Expected: Error message showing "Input path is not specified as a command-line argument. Exiting." and argparse help

**Step 2: Verify no config.json is created**

Run: `ls -la | grep config.json || echo "No config.json found (expected)"`
Expected: "No config.json found (expected)"

**Step 3: Commit test notes**

```bash
# No code changes, test verification complete
# The behavior is correct
```

---

## Task 6: Create test config.json removal

**Files:**
- Create: `tests/test_no_config_json.py`

**Step 1: Write test to verify no config.json dependency**

```python
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
            timeout=30
        )

        # Verify config.json was not created
        config_file = tmpdir_path / "config.json"
        assert not config_file.exists(), f"config.json should not exist, but found at {config_file}"


def test_error_message_no_config_json_mention():
    """Test that error message doesn't mention config.json."""
    result = subprocess.run(
        ["python", "PDFAgent.py"],
        capture_output=True,
        text=True,
        timeout=5
    )

    # Check that "config.json" is NOT in error output
    assert "config.json" not in result.stderr, "Error message should not mention config.json"
    assert "command-line argument" in result.stderr, "Error should mention command-line argument"
```

**Step 2: Verify test compiles**

Run: `python -m py_compile tests/test_no_config_json.py`
Expected: No errors

**Step 3: Run test (expected to pass)**

Run: `pytest tests/test_no_config_json.py -v`
Expected: Tests pass

**Step 4: Commit**

```bash
git add tests/test_no_config_json.py
git commit -m "test: add tests for config.json removal"
```

---

## Task 7: Verify CLI args still work

**Files:**
- Modify: None (test)

**Step 1: Run with CLI args**

Run: `python PDFAgent.py --help`
Expected: Shows all CLI options (source_lang, target_lang, agent, etc.)

**Step 2: Verify argument parsing works**

Create a simple test or run manually with args:
```bash
echo '{"test": "content"}' > /tmp/test.json
python PDFAgent.py /tmp/test.json --agent ollama --help
```
Expected: Parses arguments correctly, no config.json errors

**Step 3: Commit verification notes**

```bash
# No code changes, CLI args working correctly verified
```

---

## Task 8: Final verification

**Files:**
- Modify: None (verification)

**Step 1: Check all references to config.json in codebase**

Run: `grep -r "config.json" --include="*.py" .`
Expected: No references in PDFAgent.py; may still exist in GlobalConfig.py comments (acceptable)

**Step 2: Run complete test suite**

Run: `pytest tests/ -v`
Expected: All tests pass

**Step 3: Verify GlobalConfig still has load/save methods**

Run: `python -c "from GlobalConfig import GlobalConfig; c = GlobalConfig(); assert hasattr(c, 'load'); assert hasattr(c, 'save'); print('OK')"`
Expected: `OK` (methods still exist but not used)

**Step 4: Final commit**

```bash
git add -A
git commit -m "finish: remove config.json dependency from application flow"
```

---

## Summary

After completion:
- PDFAgent.py no longer loads or saves config.json
- Configuration comes from GlobalConfig defaults + CLI args only
- config.json file is never created or referenced by the application
- GlobalConfig.load() and .save() methods remain available but unused
- All existing functionality preserved

**Breaking changes:**
- None for CLI usage
- Users who relied on config.json for persistence will need to use CLI args instead
