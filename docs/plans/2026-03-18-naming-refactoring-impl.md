# Naming Refactoring Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Refactor all naming (classes, directories, files) to follow Python PEP 8 conventions and remove redundant suffixes throughout the codebase.

**Architecture:** Staged refactor starting with directory names (lowest impact), then module files, then classes (highest impact). Each phase updates imports and verifies with tests.

**Tech Stack:** Python 3+, Git, pytest

---

## Phase 1: Preparation

### Task 1: Create feature branch

**Files:**
- No file changes needed

**Step 1: Create feature branch**

```bash
git checkout -b feature/naming-refactoring
```

**Step 2: Verify branch created**

```bash
git branch
```
Expected: `* feature/naming-refactoring` in output

**Step 3: Document test baseline**

```bash
python -m pytest tests/ -v 2>&1 | tee baseline_test_results.txt
```

**Step 4: Commit branch initialization**

```bash
git add baseline_test_results.txt
git commit -m "chore: initialize naming refactoring branch with baseline"
```

---

## Phase 2: Directory Renaming

### Task 2: Rename LLM directory to llm

**Files:**
- Move: `LLM/` → `llm/`

**Step 1: Rename directory using git mv**

```bash
git mv LLM llm
```

**Step 2: Verify directory renamed**

```bash
ls -la | grep llm
```
Expected: `drwxr-xr-x   llm`

**Step 3: Update all import statements in codebase**

Search for all files importing from LLM:
```bash
grep -r "from LLM" --include="*.py" .
grep -r "import LLM" --include="*.py" .
```

Files to update:
- `PDFAgent.py` (line 11)
- `tests/test_nvidia_ai.py` (line 3)

**Step 4: Update imports in PDFAgent.py**

Read current line 11:
```bash
sed -n '11p' PDFAgent.py
```
Should be: `from tools.Translator import TranslatorAgent`

Actually, find the LLM import:
```bash
grep -n "LLM\." PDFAgent.py
```

**Step 5: Create updated imports**

Edit `PDFAgent.py`:
- Replace: `from LLM.NvidiaAI import NvidiaAI` (if exists)
- With: `from llm.nvidia_llm import NvidiaAI`

**Step 6: Update imports in test files**

Edit `tests/test_nvidia_ai.py`:
- Replace: `from LLM.NvidiaAI import NvidiaAI`
- With: `from llm.nvidia_llm import NvidiaAI`

**Step 7: Verify no old LLM imports remain**

```bash
grep -r "from LLM" --include="*.py" .
```
Expected: No results

**Step 8: Verify compilation**

```bash
python -m py_compile PDFAgent.py tests/test_nvidia_ai.py
```
Expected: No errors

**Step 9: Run tests to verify**

```bash
python -m pytest tests/test_nvidia_ai.py -v
```
Expected: Tests pass (same as baseline)

**Step 10: Commit**

```bash
git add -A
git commit -m "refactor: rename LLM directory to llm for PEP 8 compliance"
```

---

## Phase 3: Module Renaming

### Task 3: Rename llm_service.py to base_llm.py and update class name

**Files:**
- Move: `llm/llm_service.py` → `llm/base_llm.py`
- Modify: `llm/base_llm.py` (rename class)
- Modify: All files importing LLMService

**Step 1: Rename file using git mv**

```bash
git mv llm/llm_service.py llm/base_llm.py
```

**Step 2: Read current base file to find class name**

```bash
grep -n "^class" llm/base_llm.py
```
Expected: `class LLMService(ABC):`

**Step 3: Update class name in base_llm.py**

Edit `llm/base_llm.py`:
- Find: `class LLMService(ABC):`
- Replace with: `class BaseLLM(ABC):`

**Step 4: Find all files importing LLMService**

```bash
grep -r "LLMService" --include="*.py" .
```

Expected matches in:
- `llm/nvidia_llm.py`
- `llm/gemini_llm.py`
- `llm/ollama_llm.py`
- `tests/` (if any)

**Step 5: Update imports and references in nvidia_llm.py**

First read the file:
```bash
head -20 llm/nvidia_llm.py
```

Edit `llm/nvidia_llm.py`:
- Replace: `from LLM.llm_service import LLMService`
- With: `from llm.base_llm import BaseLLM`
- Replace: `class NvidiaAI(LLMService):`
- With: `class NvidiaAI(BaseLLM):`

**Step 6: Update imports and references in gemini_llm.py**

Edit `llm/gemini_llm.py`:
- Replace: `from llm.llm_service import LLMService` (after dir rename)
- With: `from llm.base_llm import BaseLLM`
- Replace: `class GeminiAI(LLMService):`
- With: `class GeminiAI(BaseLLM):`

**Step 7: Update imports and references in ollama_llm.py**

Edit `llm/ollama_llm.py`:
- Replace: `from LLM.llm_service import LLMService`
- With: `from llm.base_llm import BaseLLM`
- Replace: `class OllamaAI(LLMService):`
- With: `class OllamaAI(BaseLLM):`

**Step 8: Verify compilation**

```bash
python -m py_compile llm/base_llm.py llm/nvidia_llm.py llm/gemini_llm.py llm/ollama_llm.py
```
Expected: No errors

**Step 9: Run tests**

```bash
python -m pytest tests/ -v
```
Expected: Tests pass

**Step 10: Commit**

```bash
git add -A
git commit -m "refactor: rename llm_service to base_llm and LLMService to BaseLLM"
```

---

### Task 4: Rename NvidiaAI.py to nvidia_llm.py

**Files:**
- Move: `llm/NvidiaAI.py` → `llm/nvidia_llm.py`
- Modify: Files importing from this module

**Step 1: Rename file**

```bash
git mv llm/NvidiaAI.py llm/nvidia_llm.py
```
**Note:** If file was already moved in Task 2, this step may be redundant. Check file exists first.

**Step 2: Find files importing from NvidiaAI module**

```bash
grep -r "from.*NvidiaAI import" --include="*.py" .
grep -r "import.*NvidiaAI" --include="*.py" .
```

**Step 3: Update imports in PDFAgent.py**

If PDFAgent.py imports NvidiaAI:
```bash
grep -n "NvidiaAI" PDFAgent.py
```

Update line like:
- Replace: `from llm.NvidiaAI import NvidiaAI`
- With: `from llm.nvidia_llm import NvidiaAI`

**Step 4: Update imports in test files**

```bash
grep -n "NvidiaAI" tests/*.py
```

Update imports in test files:
- Replace: `from LLM.NvidiaAI import NvidiaAI` (or `from llm.NvidiaAI`)
- With: `from llm.nvidia_llm import NvidiaAI`

**Step 5: Verify compilation**

```bash
python -m py_compile PDFAgent.py tests/test_nvidia_ai.py
```
Expected: No errors

**Step 6: Run tests**

```bash
python -m pytest tests/ -v
```
Expected: Tests pass

**Step 7: Commit**

```bash
git add -A
git commit -m "refactor: rename NvidiaAI module to nvidia_llm"
```

---

### Task 5: Rename GeminiAI.py to gemini_llm.py

**Files:**
- Move: `llm/GeminiAI.py` → `llm/gemini_llm.py`
- Modify: Files importing from this module

**Step 1: Check if file exists**

```bash
ls -l llm/*.py | grep -i gemini
```

**Step 2: Rename file**

```bash
git mv llm/GeminiAI.py llm/gemini_llm.py
```

**Step 3: Find all references to GeminiAI**

```bash
grep -r "from.*GeminiAI import" --include="*.py" .
```

**Step 4: Update imports**

Update any file with:
- Replace: `from llm.GeminiAI import GeminiAI` (or `from LLM.GeminiAI`)
- With: `from llm.gemini_llm import GeminiAI`

**Step 5: Verify compilation**

```bash
python -m py_compile llm/gemini_llm.py
```

**Step 6: Commit**

```bash
git add -A
git commit -m "refactor: rename GeminiAI module to gemini_llm"
```

---

### Task 6: Rename OllamaAI.py to ollama_llm.py

**Files:**
- Move: `llm/OllamaAI.py` → `llm/ollama_llm.py`
- Modify: Files importing from this module

**Step 1: Check if file exists**

```bash
ls -l llm/*.py | grep -i ollama
```

**Step 2: Rename file**

```bash
git mv llm/OllamaAI.py llm/ollama_llm.py
```

**Step 3: Find all references to OllamaAI**

```bash
grep -r "from.*OllamaAI import" --include="*.py" .
```

**Step 4: Update imports**

Update any file with:
- Replace: `from llm.OllamaAI import OllamaAI` (or `from LLM.OllamaAI`)
- With: `from llm.ollama_llm import OllamaAI`

**Step 5: Verify compilation**

```bash
python -m py_compile llm/ollama_llm.py
```

**Step 6: Commit**

```bash
git add -A
git commit -m "refactor: rename OllamaAI module to ollama_llm"
```

---

## Phase 4: Class Renaming

### Task 7: Rename TextExtractorAgent to TextExtractor

**Files:**
- Modify: `tools/TextExtractor.py` (update class name and references)
- Modify: All files importing TextExtractorAgent

**Step 1: Find class definition**

```bash
grep -n "^class TextExtractorAgent" tools/TextExtractor.py
```
Expected: Line containing class definition

**Step 2: Rename class in definition**

Edit `tools/TextExtractor.py`:
- Find: `class TextExtractorAgent:`
- Replace with: `class TextExtractor:`

**Step 3: Find all files importing TextExtractorAgent**

```bash
grep -r "TextExtractorAgent" --include="*.py" .
```

Expected: `PDFAgent.py` line 13

**Step 4: Update imports in PDFAgent.py**

Edit `PDFAgent.py`:
- Replace: `from tools.TextExtractor import TextExtractorAgent`
- With: `from tools.text_extractor import TextExtractor`

Also update usage:
- Find: `TextExtractorAgent()`
- Replace with: `TextExtractor()`

**Step 5: Update imports in test files**

```bash
grep -r "TextExtractorAgent" tests/ --include="*.py"
```

Update `tests/test_simplified_text_extractor.py`:
- Replace: `from tools.TextExtractor import TextExtractorAgent`
- With: `from tools.text_extractor import TextExtractor`

Update usage:
- Find: `TextExtractorAgent()`
- Replace with: `TextExtractor()`

**Step 6: Verify compilation**

```bash
python -m py_compile tools/TextExtractor.py PDFAgent.py tests/test_simplified_text_extractor.py
```
Expected: No errors

**Step 7: Run tests**

```bash
python -m pytest tests/test_simplified_text_extractor.py -v
```
Expected: Tests pass

**Step 8: Commit**

```bash
git add -A
git commit -m "refactor: rename TextExtractorAgent to TextExtractor"
```

---

### Task 8: Rename TranslatorAgent to Translator

**Files:**
- Modify: `tools/Translator.py` (update class name)
- Modify: All files importing TranslatorAgent

**Step 1: Find class definition**

```bash
grep -n "^class TranslatorAgent" tools/Translator.py
```

**Step 2: Rename class**

Edit `tools/Translator.py`:
- Replace: `class TranslatorAgent:`
- With: `class Translator:`

**Step 3: Find all references**

```bash
grep -r "TranslatorAgent" --include="*.py" .
```

Expected: `PDFAgent.py`

**Step 4: Update imports in PDFAgent.py**

Edit `PDFAgent.py`:
- Replace: `from tools.Translator import TranslatorAgent`
- With: `from tools.translator import Translator`

Update usage:
- Find: `TranslatorAgent()`
- Replace with: `Translator()`

**Step 5: Verify compilation**

```bash
python -m py_compile tools/Translator.py PDFAgent.py
```

**Step 6: Run tests**

```bash
python -m pytest tests/ -v
```

**Step 7: Commit**

```bash
git add -A
git commit -m "refactor: rename TranslatorAgent to Translator"
```

---

### Task 9: Rename FilesFinder to FileFinder

**Files:**
- Modify: `tools/FileFinder.py` (update class name)
- Modify: All files importing FilesFinder

**Step 1: Find class definition**

```bash
grep -n "^class FilesFinder" tools/FileFinder.py
```

**Step 2: Rename class**

Edit `tools/FileFinder.py`:
- Replace: `class FilesFinder:`
- With: `class FileFinder:`

**Step 3: Find all references**

```bash
grep -r "FilesFinder" --include="*.py" .
```

**Step 4: Update imports in PDFAgent.py**

Edit `PDFAgent.py`:
- Replace: `from tools.FileFinder import FilesFinder`
- With: `from tools.file_finder import FileFinder`

Update usage:
- Find: `FilesFinder()`
- Replace with: `FileFinder()`

**Step 5: Verify compilation**

```bash
python -m py_compile tools/FileFinder.py PDFAgent.py
```

**Step 6: Commit**

```bash
git add -A
git commit -m "refactor: rename FilesFinder to FileFinder"
```

---

### Task 10: Rename NvidiaAI to NvidiaLLM

**Files:**
- Modify: `llm/nvidia_llm.py` (update class name)
- Modify: All files using NvidiaAI class

**Step 1: Find class definition**

```bash
grep -n "^class NvidiaAI" llm/nvidia_llm.py
```

**Step 2: Rename class**

Edit `llm/nvidia_llm.py`:
- Replace: `class NvidiaAI(BaseLLM):`
- With: `class NvidiaLLM(BaseLLM):`

**Step 3: Update docstring**

Find class docstring and update if it references old name:
- Replace: `"""NVIDIA NIM cloud API connector (NvidiaAI)."""`
- With: `"""NVIDIA NIM cloud API connector (NvidiaLLM)."""`

**Step 4: Update logger reference**

Find logger initialization:
```bash
grep -n "NvidiaAI initialized" llm/nvidia_llm.py
```
Update log message if needed.

**Step 5: Find all references in codebase**

```bash
grep -r "NvidiaAI" --include="*.py" . | grep -v "nvidia_llm"
```

Should find references in:
- `PDFAgent.py`
- `GlobalConfig.py` (agent selector)
- Tests

**Step 6: Update agent selector in GlobalConfig.py**

Read `GlobalConfig.py`:
```bash
grep -n "agent" GlobalConfig.py | grep -i "nvidia"
```

Update agent references:
- Replace: `self.agent = "nvidia"` (if checking for nvidia)
 This may need logic update: check if code does `if config.agent == "nvidia"`

**Step 7: Update PDFAgent.py instantiation**

Find instantiation:
```bash
grep -n "NvidiaAI" PDFAgent.py
```

Update:
- Replace: `NvidiaAI()`
- With: `NvidiaLLM()`

Update import:
- Replace: `from llm.nvidia_llm import NvidiaAI`
- With: `from llm.nvidia_llm import NvidiaLLM`

**Step 8: Update test files**

```bash
grep -r "NvidiaAI" tests/ --include="*.py"
```

Update test imports and usages.

**Step 9: Verify compilation**

```bash
python -m py_compile llm/nvidia_llm.py PDFAgent.py GlobalConfig.py
```

**Step 10: Run tests**

```bash
python -m pytest tests/ -v
```

**Step 11: Commit**

```bash
git add -A
git commit -m "refactor: rename NvidiaAI to NvidiaLLM"
```

---

### Task 11: Rename GeminiAI to GeminiLLM

**Files:**
- Modify: `llm/gemini_llm.py`
- Modify: Files using GeminiAI

**Step 1: Find class definition**

```bash
grep -n "^class GeminiAI" llm/gemini_llm.py
```

**Step 2: Rename class**

Edit `llm/gemini_llm.py`:
- Replace: `class GeminiAI(BaseLLM):`
- With: `class GeminiLLM(BaseLLM):`

**Step 3: Update docstring and logging**

Find and update any references in docstrings or log messages.

**Step 4: Find references**

```bash
grep -r "GeminiAI" --include="*.py" .
```

**Step 5: Update PDFAgent.py if applicable**

Update instantiation and imports.

**Step 6: Update GlobalConfig.py**

Update agent selector logic.

**Step 7: Verify compilation**

```bash
python -m py_compile llm/gemini_llm.py
```

**Step 8: Commit**

```bash
git add -A
git commit -m "refactor: rename GeminiAI to GeminiLLM"
```

---

### Task 12: Rename OllamaAI to OllamaLLM

**Files:**
- Modify: `llm/ollama_llm.py`
- Modify: Files using OllamaAI

**Step 1: Find class definition**

```bash
grep -n "^class OllamaAI" llm/ollama_llm.py
```

**Step 2: Rename class**

Edit `llm/ollama_llm.py`:
- Replace: `class OllamaAI(BaseLLM):`
- With: `class OllamaLLM(BaseLLM):`

**Step 3: Find references**

```bash
grep -r "OllamaAI" --include="*.py" .
```

**Step 4: Update all references**

Update imports and instantiations across codebase.

**Step 5: Verify compilation**

```bash
python -m py_compile llm/ollama_llm.py
```

**Step 6: Commit**

```bash
git add -A
git commit -m "refactor: rename OllamaAI to OllamaLLM"
```

---

## Phase 5: Code Modernization

### Task 13: Translate Spanish comments to English

**Files:**
- Modify: `tools/VideoGenerator.py` (has Spanish comments)

**Step 1: Find Spanish comments**

```bash
grep -n "^[[:space:]]*#.*[áéíóúñ]" tools/VideoGenerator.py
```

**Step 2: Update Spanish comments**

Edit `tools/VideoGenerator.py`:
```python
# --- Inicio del Monkey-Patch → # --- Start of Monkey-Patch ---
# Intentar parchear PIL.Image.ANTIALIAS si falta → # Try to patch PIL.Image.ANTIALIAS if missing
# ANTIALIAS era un alias de LANCZOS → # ANTIALIAS was an alias of LANCZOS
```

**Step 3: Verify all comments are in English**

```bash
grep -r "^[[:space:]]*#.*[áéíóúñ]" tools/ --include="*.py"
```
Expected: No results

**Step 4: Commit**

```bash
git add tools/VideoGenerator.py
git commit -m "style: translate Spanish comments to English"
```

---

### Task 14: Update docstrings for renamed classes

**Files:**
- Modify: All files with renamed classes

**Step 1: Update TextExtractor docstring**

Edit `tools/TextExtractor.py`:
```python
class TextExtractor:
    """
    An agent responsible for extracting and cleaning text from PDF and EPUB files.
    """
```

**Step 2: Update Translator docstring**

Edit `tools/Translator.py`:
```python
class Translator:
    """
    An agent responsible for translating text using LLM services.
    """
```

**Step 3: Update NvidiaLLM docstring**

Edit `llm/nvidia_llm.py`:
```python
class NvidiaLLM(BaseLLM):
    """NVIDIA NIM cloud API connector using langchain-nvidia-ai-endpoints."""
```

**Step 4: Update other LLM classes**

Update `GeminiLLM` and `OllamaLLM` docstrings similarly.

**Step 5: Verify compilation**

```bash
python -m py_compile tools/TextExtractor.py tools/Translator.py llm/*.py
```

**Step 6: Commit**

```bash
git add -A
git commit -m "docs: update docstrings for renamed classes"
```

---

## Phase 6: Final Verification

### Task 15: Comprehensive search for old naming

**Step 1: Search for LLM. imports (old directory)**

```bash
grep -r "from LLM" --include="*.py" .
```
Expected: No results

**Step 2: Search for Agent suffix classes**

```bash
grep -r "Agent\[" --include="*.py" .
```
Expected: No results

**Step 3: Search for AI suffix classes**

```bash
grep -r "class.*AI(" --include="*.py" .
```
Expected: No results (only in docstrings or comments)

**Step 4: Search for old class names**

```bash
grep -r "TextExtractorAgent\|TranslatorAgent\|FilesFinder" --include="*.py" .
```
Expected: No results (only in tests for backward compatibility if desired)

**Step 5: Search for old module names**

```bash
grep -r "NvidiaAI\|GeminiAI\|OllamaAI" --include="*.py" .
```
Expected: No results

**Step 6: Run full test suite**

```bash
python -m pytest tests/ -v
```
Expected: All tests pass

**Step 7: Verify all Python files compile**

```bash
find . -name "*.py" -path "*/tools/*" -o -name "*.py" -path "*/llm/*" | xargs python -m py_compile
```
Expected: No errors

**Step 8: Check for import errors**

```bash
python -c "from tools.text_extractor import TextExtractor; from tools.translator import Translator; from llm.nvidia_llm import NvidiaLLM"
```
Expected: No import errors

**Step 9: Commit final verification**

```bash
git add baseline_test_results.txt
git commit -m "finish: naming refactoring complete"
```

---

## Summary

After completion:
- ✓ Directory `LLM/` → `llm/`
- ✓ Modules renamed: `NvidiaAI.py` → `nvidia_llm.py`, etc.
- ✓ Classes renamed: `TextExtractorAgent` → `TextExtractor`, `NvidiaAI` → `NvidiaLLM`
- ✓ Base class: `LLMService` → `BaseLLM`
- ✓ All imports updated across codebase
- ✓ Spanish comments translated to English
- ✓ Docstrings updated
- ✓ All tests passing

**Breaking changes:**
- Import paths: `LLM.NvidiaAI` → `llm.nvidia_llm.NvidiaLLM`
- Class names require updates in external code

**Total estimated time:** ~2 hours across 15 tasks
