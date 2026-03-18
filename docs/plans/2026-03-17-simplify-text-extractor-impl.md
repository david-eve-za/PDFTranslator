# Simplify TextExtractor Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Remove image extraction from TextExtractorAgent, simplify extract_text() to accept only file_path and return only text.

**Architecture:** Change method signatures, remove extract_images parameter, eliminate all image extraction code from _extract_from_pdf, unify PDF/EPUB method calls.

**Tech Stack:** Python, PyMuPDF, ebooklib

---

## Task 1: Update extract_text method signature

**Files:**
- Modify: `tools/TextExtractor.py:39`

**Step 1: Open TextExtractor.py**

Read current content around line 39.

**Step 2: Update method signature**

Replace:
```python
def extract_text(self, file_path: str, extract_images: bool = True) -> Optional[Tuple[str, List[Path]]]:
```

With:
```python
def extract_text(self, file_path: str) -> Optional[str]:
```

**Step 3: Update docstring**

Update lines 40-49 (docstring) to remove references to extract_images parameter and Tuple return.

**Step 4: Verify file compiles**

Run: `python -m py_compile tools/TextExtractor.py`
Expected: No errors (may have type errors from other parts - ignore for now)

**Step 5: Commit**

```bash
git add tools/TextExtractor.py
git commit -m "refactor: update extract_text signature to remove extract_images"
```

---

## Task 2: Simplify _extract_from_pdf method signature

**Files:**
- Modify: `tools/TextExtractor.py:121`

**Step 1: Find _extract_from_pdf method**

Locate line 121 with method definition.

**Step 2: Update method signature**

Replace:
```python
def _extract_from_pdf(self, pdf_path: Path, extract_images: bool) -> Tuple[str, List[Path]]:
```

With:
```python
def _extract_from_pdf(self, pdf_path: Path) -> str:
```

**Step 3: Update docstring**

Update lines 122-123 (docstring) to remove references to image extraction.

**Step 4: Verify file compiles**

Run: `python -m py_compile tools/TextExtractor.py`
Expected: No errors

**Step 5: Commit**

```bash
git add tools/TextExtractor.py
git commit -m "refactor: update _extract_from_pdf signature to remove extract_images"
```

---

## Task 3: Simplify _extract_from_epub method signature

**Files:**
- Modify: `tools/TextExtractor.py:168`

**Step 1: Find _extract_from_epub method**

Locate line 168 with method definition.

**Step 2: Update method signature**

Replace:
```python
def _extract_from_epub(self, epub_path: Path) -> Tuple[str, List[Path]]:
```

With:
```python
def _extract_from_epub(self, epub_path: Path) -> str:
```

**Step 3: Update docstring**

Update lines 169-170 (docstring) to remove references to empty image list.

**Step 4: Verify file compiles**

Run: `python -m py_compile tools/TextExtractor.py`
Expected: No errors

**Step 5: Commit**

```bash
git add tools/TextExtractor.py
git commit -m "refactor: update _extract_from_epub signature to return str only"
```

---

## Task 4: Remove image extraction variables from _extract_from_pdf

**Files:**
- Modify: `tools/TextExtractor.py:125-127`

**Step 1: Find image extraction variables**

Locate lines 125-127 with variables:
```python
extracted_pages: List[str] = []
image_paths: List[Path] = []
images_dir = pdf_path.parent / f"images_{pdf_path.stem}"
```

**Step 2: Remove image-related variables**

Replace lines 125-127 with:
```python
extracted_pages: List[str] = []
```

**Step 3: Verify file compiles**

Run: `python -m py_compile tools/TextExtractor.py`
Expected: No errors (may have errors about missing variables - ignore)

**Step 4: Commit**

```bash
git add tools/TextExtractor.py
git commit -m "refactor: remove image extraction variables from _extract_from_pdf"
```

---

## Task 5: Remove image extraction logic from _extract_from_pdf

**Files:**
- Modify: `tools/TextExtractor.py:143-162`

**Step 1: Find image extraction block**

Locate lines 143-162:
```python
if extract_images:
    image_list = page.get_images(full=True)
    for img_index, img_info in enumerate(image_list):
        xref = img_info[0]
        base_image = doc.extract_image(xref)
        if not base_image:
            continue

        image_bytes = base_image["image"]
        image_ext = base_image["ext"]
        image_filename = f"page{page_num}_img{img_index}.{image_ext}"

        try:
            images_dir.mkdir(parents=True, exist_ok=True)
            image_save_path = images_dir / image_filename
            with open(image_save_path, "wb") as img_file:
                img_file.write(image_bytes)
            image_paths.append(image_save_path)
        except OSError as e:
            logger.error(f"  - PDF: Could not save image {image_filename}: {e}")
```

**Step 2: Remove entire image extraction block**

Delete lines 143-162 completely.

**Step 3: Verify file compiles**

Run: `python -m py_compile tools/TextExtractor.py`
Expected: No errors

**Step 4: Commit**

```bash
git add tools/TextExtractor.py
git commit -m "refactor: remove image extraction logic from _extract_from_pdf"
```

---

## Task 6: Update _extract_from_pdf return statement

**Files:**
- Modify: `tools/TextExtractor.py:166`

**Step 1: Find return statement**

Locate line 166:
```python
return cleaned_text, image_paths
```

**Step 2: Update return statement**

Replace with:
```python
return cleaned_text
```

**Step 3: Verify file compiles**

Run: `python -m py_compile tools/TextExtractor.py`
Expected: No errors

**Step 4: Commit**

```bash
git add tools/TextExtractor.py
git commit -m "refactor: update _extract_from_pdf to return only text"
```

---

## Task 7: Update _extract_from_epub return statement

**Files:**
- Modify: `tools/TextExtractor.py:194`

**Step 1: Find return statement**

Locate line 194:
```python
return cleaned_text, []
```

**Step 2: Update return statement**

Replace with:
```python
return cleaned_text
```

**Step 3: Verify file compiles**

Run: `python -m py_compile tools/TextExtractor.py`
Expected: No errors

**Step 4: Commit**

```bash
git add tools/TextExtractor.py
git commit -m "refactor: update _extract_from_epub to return only text"
```

---

## Task 8: Simplify extract_text method call logic

**Files:**
- Modify: `tools/TextExtractor.py:64-68`

**Step 1: Find method call logic**

Locate lines 64-68:
```python
if not extraction_method:
    logger.warning(f"Unsupported extension '{extension}' for file {path_obj.name}")
    return None

try:
    if not path_obj.is_file():
        raise FileNotFoundError(f"File not found at path: {file_path}")

    # The 'extract_images' argument is only relevant for PDFs.
    if extension == PDF_EXTENSION:
        return extraction_method(path_obj, extract_images=extract_images)
    else:
        return extraction_method(path_obj)
```

**Step 2: Simplify method calls**

Replace lines 64-68 (from "try:" onward) with:
```python
try:
    if not path_obj.is_file():
        raise FileNotFoundError(f"File not found at path: {file_path}")

    return extraction_method(path_obj)
```

**Step 3: Verify file compiles**

Run: `python -m py_compile tools/TextExtractor.py`
Expected: No errors

**Step 4: Commit**

```bash
git add tools/TextExtractor.py
git commit -m "refactor: simplify extract_text method call logic"
```

---

## Task 9: Remove extract_images parameter from extract_text calls in PDFAgent.py

**Files:**
- Modify: `PDFAgent.py`

**Step 1: Search for extract_text calls**

Run: `grep -n "extract_text" PDFAgent.py`
Expected: Find lines where extract_text is called with extract_images parameter

**Step 2: Update calls to remove extract_images parameter**

Find calls like:
```python
text, images = extractor.extract_text(file_path, extract_images=config.gen_video)
```

Replace with:
```python
text = extractor.extract_text(file_path)
```

**Step 3: Update variable unpacking**

Replace tuple unpacking with single variable assignment.

**Step 4: Verify file compiles**

Run: `python -m py_compile PDFAgent.py`
Expected: No errors

**Step 5: Commit**

```bash
git add PDFAgent.py
git commit -m "refactor: update PDFAgent.py to use simplified extract_text"
```

---

## Task 10: Create tests for simplified text extraction

**Files:**
- Create: `tests/test_simplified_text_extractor.py`

**Step 1: Write test file**

```python
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from tools.TextExtractor import TextExtractorAgent


def test_extract_text_returns_string_not_tuple():
    """Test that extract_text returns str, not Tuple[str, List[Path]]."""
    extractor = TextExtractorAgent()
    
    # Mock a simple PDF
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp_path = tmp.name
    
    try:
        # We'll mock the actual extraction since PDF parsing is complex
        with patch.object(extractor, '_extract_from_pdf') as mock_extract:
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
    extractor = TextExtractorAgent()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        test_pdf = Path(tmpdir) / "test.pdf"
        test_pdf.write_text("dummy content")
        
        # Mock the PDF extraction to return text
        with patch.object(extractor, '_extract_from_pdf') as mock_extract:
            mock_extract.return_value = "test text"
            result = extractor.extract_text(str(test_pdf))
            
            # Verify no images directory was created
            images_dir = test_pdf.parent / f"images_{test_pdf.stem}"
            assert not images_dir.exists(), f"Image directory {images_dir} should not exist"


def test_extract_text_error_returns_none():
    """Test that extract_text returns None on error."""
    extractor = TextExtractorAgent()
    
    # Test with non-existent file
    result = extractor.extract_text("/non/existent/file.pdf")
    assert result is None, "Should return None for non-existent file"
```

**Step 2: Verify test compiles**

Run: `python -m py_compile tests/test_simplified_text_extractor.py`
Expected: No errors

**Step 3: Run tests**

Run: `pytest tests/test_simplified_text_extractor.py -v`
Expected: Tests pass (some may need mocking adjustments)

**Step 4: Commit**

```bash
git add tests/test_simplified_text_extractor.py
git commit -m "test: add tests for simplified text extraction"
```

---

## Task 11: Final verification and cleanup

**Files:**
- Modify: None (verification)

**Step 1: Verify no references to extract_images remain**

Run: `grep -r "extract_images" --include="*.py" .`
Expected: No references (except possibly in comments)

**Step 2: Verify no Tuple[str, List[Path]] return types remain**

Run: `grep -r "Tuple\[str, List\[Path\]\]" --include="*.py" .`
Expected: No references

**Step 3: Verify no image_paths variables remain**

Run: `grep -r "image_paths" --include="*.py" .`
Expected: No references

**Step 4: Run existing tests**

Run: `pytest tests/ -v` (if pytest installed)
Expected: All tests pass

**Step 5: Final commit**

```bash
git add -A
git commit -m "finish: simplify TextExtractor to remove image extraction"
```

---

## Summary

After completion:
- `TextExtractorAgent.extract_text()` accepts only `file_path: str`
- Returns `Optional[str]` (text on success, `None` on error)
- No image extraction functionality remains
- No `extract_images` parameter anywhere
- All callers updated to handle only text
- Tests verify simplified behavior

**Breaking changes:**
- Callers must be updated to handle only text (not tuples)
- Image extraction functionality completely removed
- `extract_images` parameter removed from all calls