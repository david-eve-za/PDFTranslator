# Naming Refactoring Design Document

**Date:** 2026-03-18

## Overview

Full refactoring to align codebase naming with Python PEP 8 conventions and English standards.

**Scope:** All naming elements - classes, methods, files, directories, variables
**Type:** Breaking changes (requires updating all imports and references)
**Approach:** Staged implementation with thorough testing

## Motivation

**Current Issues:**
1. Mixed case directory name: `LLM/` (should be `llm/`)
2. Redundant class suffixes: `TextExtractorAgent`, `TranslatorAgent`
3. Unclear class names: `NvidiaAI` doesn't clarify it's an LLM service
4. Spanish comments in some files
5. Inconsistent naming patterns

**Goals:**
1. Follow PEP 8 naming conventions
2. Improve code clarity and maintainability
3. Modernize codebase while maintaining functionality
4. Standardize naming across all modules

## Architecture Changes

### 1. Directory Structure

**Before:**
```
LLM/
  NvidiaAI.py
  GeminiAI.py
  OllamaAI.py
  llm_service.py
```

**After:**
```
llm/
  nvidia_llm.py
  gemini_llm.py
  ollama_llm.py
  base_llm.py
```

**Changes:**
- `LLM/` → `llm/` (PEP 8: lowercase module names)
- `NvidiaAI.py` → `nvidia_llm.py` (clarify it's an LLM service)
- `GeminiAI.py` → `gemini_llm.py`
- `OllamaAI.py` → `ollama_llm.py`
- `llm_service.py` → `base_llm.py` (base class naming)

### 2. Class Renaming

| Current Class | New Class | File Path | Reason |
|---------------|-----------|-----------|--------|
| `TextExtractorAgent` | `TextExtractor` | `tools/TextExtractor.py` | Remove redundant "Agent" suffix |
| `TranslatorAgent` | `Translator` | `tools/Translator.py` | Remove redundant "Agent" suffix |
| `NvidiaAI` | `NvidiaLLM` | `llm/nvidia_llm.py` | Clarify it's an LLM service |
| `GeminiAI` | `GeminiLLM` | `llm/gemini_llm.py` | Clarify it's an LLM service |
| `OllamaAI` | `OllamaLLM` | `llm/ollama_llm.py` | Clarify it's an LLM service |
| `FilesFinder` | `FileFinder` | `tools/FileFinder.py` | Remove plural, standardize |
| `VideoGenerator` | `VideoGenerator` | `tools/VideoGenerator.py` | ✓ Already correct |
| `AudioGenerator` | `AudioGenerator` | `tools/AudioGenerator.py` | ✓ Already correct |
| `GlobalConfig` | `GlobalConfig` | `GlobalConfig.py` | ✓ Already correct |

### 3. Base Class Renaming

**Before:**
```python
from LLM.llm_service import LLMService

class NvidiaAI(LLMService):
    pass
```

**After:**
```python
from llm.base_llm import BaseLLM

class NvidiaLLM(BaseLLM):
    pass
```

### 4. Method/Function Naming

**Status:** ✓ Already follow PEP 8 snake_case
**No changes needed** to method names like:
- `extract_text()`
- `_clean_extracted_text()`
- `_extract_from_pdf()`
- `process_texts()`

### 5. Variable Naming

**Standardize configuration variables:**
- Already well-named: `nvidia_model_name`, `gemini_temperature`, etc.
- Keep existing pattern (already consistent)

### 6. Import Updates

**Files requiring import updates:**

1. `PDFAgent.py`
   - `from tools.TextExtractor import TextExtractorAgent` → `from tools.text_extractor import TextExtractor`
   - `from tools.Translator import TranslatorAgent` → `from tools.translator import Translator`
   - `from LLM.NvidiaAI import NvidiaAI` → `from llm.nvidia_llm import NvidiaLLM`

2. All tests in `tests/`
   - Update imports for renamed classes

3. Internal imports in `llm/` modules
   - Update base class imports

## Implementation Phases

### Phase 1: Preparation
**Goal:** Setup staging environment

**Tasks:**
1. Create feature branch: `feature/naming-refactoring`
2. Create git worktree (if using worktrees)
3. Document current test coverage
4. Backup current state

**Verification:** Branch created, tests baseline established

### Phase 2: Directory Renaming
**Goal:** Rename LLM/ to llm/

**Tasks:**
1. Rename directory: `git mv LLM llm`
2. Update all imports from `LLM.*` to `llm.*`
3. Search and replace import statements across codebase
4. Run tests to verify

**Files affected:**
- `PDFAgent.py`
- All files in `llm/` directory
- All test files

**Verification:** All tests pass

### Phase 3: Module Renaming
**Goal:** Rename LLM service files

**Tasks:**
1. Rename files in `llm/`:
   - `llm_service.py` → `base_llm.py`
   - `NvidiaAI.py` → `nvidia_llm.py` (after directory move)
   - `GeminiAI.py` → `gemini_llm.py`
   - `OllamaAI.py` → `ollama_llm.py`
2. Update imports to new filenames
3. Update base class name: `LLMService` → `BaseLLM`
4. Run tests after each file rename

**Verification:** All tests pass

### Phase 4: Class Renaming
**Goal:** Rename classes to remove suffixes and improve clarity

**Tasks:**
1. Rename in `tools/TextExtractor.py`: `TextExtractorAgent` → `TextExtractor`
2. Rename in `tools/Translator.py`: `TranslatorAgent` → `Translator`
3. Rename in `tools/FileFinder.py`: `FilesFinder` → `FileFinder`
4. Rename in `llm/nvidia_llm.py`: `NvidiaAI` → `NvidiaLLM`
5. Rename in `llm/gemini_llm.py`: `GeminiAI` → `GeminiLLM`
6. Rename in `llm/ollama_llm.py`: `OllamaAI` → `OllamaLLM`
7. Update all class references across codebase
8. Run comprehensive tests

**Verification:** All tests pass

### Phase 5: Code Modernization
**Goal:** Improve code quality while renaming

**Tasks:**
1. Translate Spanish comments to English
2. Remove redundant comments
3. Add missing type hints where appropriate
4. Update docstrings for renamed classes
5. Remove dead code if any

**Files affected:**
- `tools/VideoGenerator.py` (has Spanish comments)
- All files with renamed classes (update docstrings)

**Verification:** Code compiles, tests pass

### Phase 6: Final Verification
**Goal:** Comprehensive testing

**Tasks:**
1. Run full test suite
2. Check for any remaining old imports
3. Verify all files compile
4. Check for hardcoded references
5. Update documentation if needed

**Verification:** All tests pass, no old references remain

## Testing Strategy

**After each phase:**
1. Run `python -m pytest tests/ -v` to verify tests
2. Run `python -m py_compile` on modified files
3. Search for old import names: `grep -r "LLM\." --include="*.py"`
4. Search for old class names

**Final verification:**
1. All existing tests pass
2. No import errors
3. No AttributeError from renamed classes
4. Code runs successfully end-to-end

## Breaking Changes

**API Breaking Changes:**
1. Import paths for LLM modules: `LLM.NvidiaAI` → `llm.nvidia_llm.NvidiaLLM`
2. Class names: `TextExtractorAgent` → `TextExtractor`
3. Base class: `LLMService` → `BaseLLM`

**Impact:**
- Any external scripts importing these classes must update imports
- No behavior changes, only naming changes
- All internal code updated as part of refactoring

## Rollback Plan

**If critical issues arise:**
1. Git revert to commit before Phase 2
2. All changes are reversible (only renames, no functional changes)
3. Each phase is atomic with commits

**Commit strategy:**
- One commit per phase
- One commit per file rename (within phase)
- Clear commit messages describing changes

## Deliverables

1. Refactored codebase with PEP 8 compliant naming
2. All imports updated
3. All tests passing
4. Code modernized (English comments, type hints)
5. Updated documentation (if any)

## Timeline Estimate

- Phase 1: 15 minutes (setup)
- Phase 2: 20 minutes (directory rename, imports)
- Phase 3: 30 minutes (module renames)
- Phase 4: 30 minutes (class renames)
- Phase 5: 20 minutes (modernization)
- Phase 6: 15 minutes (verification)

**Total:** ~2 hours

## Questions for Review

1. Should `FilesFinder` be renamed to `FileDiscovery` or `FileLocator` instead of `FileFinder`?
2. Should `BaseLLM` instead be `LLMProvider` or `LLMService` (keep service)?
3. Should we lowercase all Python files (`TextExtractor.py` → `text_extractor.py`)?

## Success Criteria

- ✓ All file/folder names follow PEP 8 (snake_case, lowercase)
- ✓ All classes use descriptive names without redundant suffixes
- ✓ All imports updated
- ✓ All existing tests pass
- ✓ No regression in functionality
- ✓ Code is more readable and maintainable
