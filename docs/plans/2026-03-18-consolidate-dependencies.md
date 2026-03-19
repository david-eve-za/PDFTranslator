# Consolidate Dependencies Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Consolidate dependencies into environment.yml only, remove unused packages, and eliminate gradio dependency.

**Architecture:** Remove requirements.txt, keep only environment.yml with consolidated dependencies. Remove gradio from AudioGenerator.py and Translator.py.

**Tech Stack:** conda, pip, environment.yml

---

## Task 1: Remove gradio from AudioGenerator.py

**Files:**
- Modify: `tools/AudioGenerator.py`

**Step 1: Remove gradio import**
Remove line 46:
```python
import gradio as gr
```

**Step 2: Change progress type**
Replace line 103:
```python
def __init__(self, progress: gr.Progress = None):
```
With:
```python
def __init__(self, progress=None):
```

**Step 3: Update progress usage in process_texts**
Replace lines 266-270:
```python
iterator = self._progress.tqdm(enumerate(chunks), desc="Generating Audio Chunks",
unit="chunk") if self._progress else tqdm(enumerate(chunks, start=1),
total=len(chunks),
desc="Generating Audio Chunks", unit="chunk")
```
With:
```python
if self._progress:
    iterator = self._progress(enumerate(chunks), desc="Generating Audio Chunks", unit="chunk")
else:
    iterator = tqdm(enumerate(chunks, start=1), total=len(chunks), desc="Generating Audio Chunks", unit="chunk")
```

**Step 4: Commit**
```bash
git add tools/AudioGenerator.py
git commit -m "refactor: remove gradio dependency from AudioGenerator"
```

---

## Task 2: Remove gradio from Translator.py

**Files:**
- Modify: `tools/Translator.py`

**Step 1: Remove gradio import**
Remove line 3:
```python
import gradio as gr
```

**Step 2: Commit**
```bash
git add tools/Translator.py
git commit -m "refactor: remove unused gradio import from Translator"
```

---

## Task 3: Update environment.yml with consolidated dependencies

**Files:**
- Modify: `environment.yml`

**Step 1: Replace entire file content**
```yaml
name: PDFTranslator
channels:
  - conda-forge
  - defaults
dependencies:
  - python=3.9
  - pip
  - pip:
    # CLI
    - typer>=0.9.0
    - rich>=13.0.0
    # Text extraction
    - beautifulsoup4
    - ebooklib
    PyMuPDF
    - pdfplumber
    - docling
    - docling-core
    # LLM
    - langchain-core
    - langchain-ollama
    - langchain-google-genai
    - langchain-text-splitters
    - langchain-nvidia-ai-endpoints
    - google-genai
    - google-api-core
    # Audio/Video
    - moviepy
    - pillow
    - pydub
    # NLP
    - nltk
    - sentencepiece
    - transformers
    - rapidfuzz
    - tqdm
    # Testing
    - pytest
    - pytest-cov
```

**Step 2: Commit**
```bash
git add environment.yml
git commit -m "refactor: consolidate dependencies in environment.yml"
```

---

## Task 4: Remove requirements.txt

**Files:**
- Delete: `requirements.txt`

**Step 1: Delete file**
```bash
rm requirements.txt
git add requirements.txt
git commit -m "chore: remove requirements.txt, use environment.yml only"
```

---

## Task 5: Verify imports work

**Step 1: Test imports**
Run: `python -c "from tools.AudioGenerator import AudioGenerator; print('OK')"`
Expected: OK (without gradio errors)

**Step 2: Test CLI**
Run: `python PDFAgent.py --help`
Expected: Show help correctly

---

## Summary of Changes

| File | Change |
|------|--------|
| `tools/AudioGenerator.py` | Remove gradio import and dependency |
| `tools/Translator.py` | Remove unused gradio import |
| `environment.yml` | Consolidated dependencies, removed gradio and google-generativeai |
| `requirements.txt` | DELETED |

## Removed Packages
- `gradio` - Not essential for CLI
- `google-generativeai` - Replaced by `google-genai`
