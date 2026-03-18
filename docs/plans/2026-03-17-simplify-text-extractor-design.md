# Design: Simplify TextExtractor to Remove Image Extraction

**Date:** 2026-03-17
**Status:** Approved

## Overview

Simplify `TextExtractorAgent.extract_text()` method to remove image extraction functionality. The method will now accept only a file path and return only text (not a tuple with image paths).

## Architecture

**Simplified architecture:**
- `TextExtractorAgent.extract_text()` accepts only `file_path: str`
- Returns `Optional[str]` (text on success, `None` on error)
- Removes all image extraction code from `_extract_from_pdf` method
- Removes `extract_images` parameter completely
- Unifies method calls for PDF and EPUB extraction (same signature)

**Simplified flow:**
```
Call -> extract_text(file_path)
  ↓
Determine extension (PDF/EPUB)
  ↓
Extract only text (no images)
  ↓
Clean text (_clean_extracted_text)
  ↓
Return str (or None on error)
```

## Components and Changes

### Changes in TextExtractor.py

1. **Change `extract_text` method signature:**
   ```python
   # Before:
   def extract_text(self, file_path: str, extract_images: bool = True) -> Optional[Tuple[str, List[Path]]]:
   
   # After:
   def extract_text(self, file_path: str) -> Optional[str]:
   ```

2. **Remove `extract_images` parameter from `_extract_from_pdf`:**
   ```python
   # Before:
   def _extract_from_pdf(self, pdf_path: Path, extract_images: bool) -> Tuple[str, List[Path]]:
   
   # After:
   def _extract_from_pdf(self, pdf_path: Path) -> str:
   ```

3. **Change `_extract_from_epub` return type:**
   ```python
   # Before:
   def _extract_from_epub(self, epub_path: Path) -> Tuple[str, List[Path]]:
   
   # After:
   def _extract_from_epub(self, epub_path: Path) -> str:
   ```

4. **Remove image extraction code from `_extract_from_pdf`:**
   - Remove variables: `image_paths: List[Path] = []`, `images_dir = pdf_path.parent / f"images_{pdf_path.stem}"`
   - Remove `if extract_images:` block (lines 143-162)
   - Remove `image_list = page.get_images(full=True)` loop
   - Remove `doc.extract_image(xref)` and image saving logic
   - Change return from `return cleaned_text, image_paths` to `return cleaned_text`

5. **Remove image list from `_extract_from_epub`:**
   - Change return from `return cleaned_text, []` to `return cleaned_text`

6. **Simplify method calls in `extract_text`:**
   ```python
   # Before:
   if extension == PDF_EXTENSION:
       return extraction_method(path_obj, extract_images=extract_images)
   else:
       return extraction_method(path_obj)
   
   # After:
   return extraction_method(path_obj)
   ```

### Code to Remove

**From `_extract_from_pdf`:**
- Lines 126-127: `image_paths` and `images_dir` variables
- Lines 144-162: Entire image extraction block
- Line 166: Return `cleaned_text` (no `image_paths`)

**From `_extract_from_epub`:**
- Line 194: Remove empty list from return

**From `extract_text`:**
- Parameter `extract_images: bool = True`
- Conditional logic for PDF with `extract_images` parameter

## Error Handling

**No changes to error handling:**
- Maintain existing try/catch blocks
- Maintain logging of errors
- Return `None` on errors (same behavior)
- Same exceptions: `FileNotFoundError`, `epub.EpubException`, `zipfile.BadZipFile`, `fitz.fitz.PyMuPDFError`, `Exception`

**Caller impact:**
- Callers must now handle only text (not tuples)
- Callers must not expect image paths
- Error handling remains identical (`None` on error)

## Compatibility Impact

**Files that use `extract_text()`:**
- `PDFAgent.py` - Needs updating to handle only text
- Other potential callers - Need verification

**Required caller updates:**
1. Extract only text from return value (no tuple unpacking)
2. Remove references to image paths
3. Update any logic that depends on image extraction

## Testing

1. **Text extraction without images:**
   - Verify `extract_text()` returns `str` (not `Tuple`)
   - Verify no image directories created
   - Verify no image-related logging

2. **Error handling:**
   - Maintain existing error tests
   - Verify `None` returned on errors

3. **PDF/EPUB compatibility:**
   - Both formats still work
   - Text cleaning still functional

4. **Caller updates:**
   - Update any tests using `extract_text()` with tuples
   - Test updated callers

**No testing needed for image extraction** (removed completely)

## Benefits

- Simpler interface (single parameter, single return value)
- Less code to maintain
- No file system side effects (no image directories created)
- Clearer responsibility (text extraction only)
- Reduced bug surface area

## Trade-offs

- Loss of image extraction functionality
- Callers need updates
- Cannot extract images without alternative implementation
- May break existing workflows that depend on images