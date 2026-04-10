# Design: Python Modern Structure Refactoring

**Date:** 2025-04-10
**Branch:** `refactor/python-modern-structure`
**Priority:** High
**Estimated Time:** 3-4 hours

## Objective

Refactor the project to follow Python 2025 best practices with modern structure, integrating frontend into src/, eliminating duplicate directories, and creating a professional, maintainable codebase.

## Current Problems

### 1. Duplicate Directories
- `backend/` in root (duplicate of `src/backend/`)
- `config/` in root (duplicate of `src/core/config/`)
- `infrastructure/` in root (duplicate of `src/infrastructure/`)

### 2. Missing Modern Standards
- No `pyproject.toml` (essential for modern Python)
- No `LICENSE` file
- No proper package structure under `src/`
- Mixed structure (frontend in root, backend in src)

### 3. Entry Point Confusion
- `PDFAgent.py` in root instead of proper entry point
- No `__main__.py` for package execution

## Proposed Structure

### Final Directory Layout

```
PDFTranslator/
├── src/
│   └── pdftranslator/           # Main package
│       ├── __init__.py          # Package version and metadata
│       ├── __main__.py          # Entry point: python -m pdftranslator
│       ├── backend/             # FastAPI backend
│       │   ├── __init__.py
│       │   ├── api/
│       │   │   ├── __init__.py
│       │   │   ├── models/
│       │   │   └── routes/
│       │   └── main.py
│       ├── cli/                 # CLI interface
│       │   ├── __init__.py
│       │   ├── commands/
│       │   ├── services/
│       │   └── ui/
│       ├── core/                # Core functionality
│       │   ├── __init__.py
│       │   ├── config/
│       │   ├── exceptions/
│       │   └── models/
│       ├── database/            # Database layer
│       │   ├── __init__.py
│       │   ├── repositories/
│       │   ├── services/
│       │   └── connection.py
│       ├── infrastructure/      # External integrations
│       │   ├── __init__.py
│       │   ├── llm/
│       │   └── document/
│       ├── services/            # Business logic
│       │   └── __init__.py
│       ├── tools/               # Utility tools
│       │   └── __init__.py
│       └── frontend/            # React frontend (NEW)
│           ├── src/
│           ├── public/
│           ├── package.json
│           └── vite.config.ts
├── tests/                       # Test suite
│   ├── __init__.py
│   ├── backend/
│   ├── cli/
│   ├── core/
│   ├── database/
│   └── infrastructure/
├── docs/                        # Documentation
│   └── plans/
├── pyproject.toml               # Modern Python config (NEW)
├── README.md
├── CHANGELOG.md
├── LICENSE                      # MIT License (NEW)
├── AGENTS.md
├── environment.yml              # Conda environment
├── .env                         # Environment variables
├── .gitignore
└── .python-version              # Python version pin (NEW)
```

## Implementation Plan

### Phase 1: Create Package Structure (Commits 1-3)

#### Commit 1: Create pdftranslator package base
- Create `src/pdftranslator/` directory
- Create `src/pdftranslator/__init__.py` with version and metadata
- Create `src/pdftranslator/__main__.py` as entry point

#### Commit 2: Move backend modules
- Move `src/backend/` → `src/pdftranslator/backend/`
- Update all imports: `src.backend` → `src.pdftranslator.backend`
- Update `__init__.py` files

#### Commit 3: Move core modules
- Move `src/core/` → `src/pdftranslator/core/`
- Update imports: `src.core` → `src.pdftranslator.core`

### Phase 2: Move Remaining Modules (Commits 4-7)

#### Commit 4: Move CLI modules
- Move `src/cli/` → `src/pdftranslator/cli/`
- Update imports: `src.cli` → `src.pdftranslator.cli`

#### Commit 5: Move database modules
- Move `src/database/` → `src/pdftranslator/database/`
- Update imports: `src.database` → `src.pdftranslator.database`

#### Commit 6: Move infrastructure modules
- Move `src/infrastructure/` → `src/pdftranslator/infrastructure/`
- Update imports: `src.infrastructure` → `src.pdftranslator.infrastructure`

#### Commit 7: Move services and tools
- Move `src/services/` → `src/pdftranslator/services/`
- Move `src/tools/` → `src/pdftranslator/tools/`
- Update imports

### Phase 3: Integrate Frontend (Commit 8)

#### Commit 8: Move frontend into src
- Move `frontend/` → `src/pdftranslator/frontend/`
- Update `vite.config.ts` paths
- Update `package.json` name to `@pdftranslator/frontend`
- Update frontend README

### Phase 4: Clean Up Root (Commits 9-10)

#### Commit 9: Remove duplicate directories
- Remove `backend/` from root
- Remove `config/` from root
- Remove `infrastructure/` from root

#### Commit 10: Clean up obsolete files
- Remove `mistral-large-3-675b-instruct-2512/` (tokenizer cache, should be in .gitignore)
- Remove `PDFAgent.log` (should be in .gitignore)
- Remove `__pycache__` from root

### Phase 5: Modern Configuration (Commits 11-13)

#### Commit 11: Create pyproject.toml
- Add project metadata (name, version, description)
- Add dependencies
- Add dev dependencies
- Configure build system (setuptools, hatch, or poetry)
- Configure tools (ruff, mypy, pytest)
- Add scripts entry point

#### Commit 12: Create LICENSE
- Add MIT License file

#### Commit 13: Create .python-version
- Pin Python version (3.11)

### Phase 6: Update Entry Points (Commits 14-15)

#### Commit 14: Update PDFAgent.py
- Convert to simple entry point that calls `pdftranslator.cli.main()`
- Or deprecate and create new entry point

#### Commit 15: Update tests
- Update all test imports to `src.pdftranslator.*`
- Update test paths
- Ensure pytest configuration works

### Phase 7: Final Validation (Commits 16-17)

#### Commit 16: Update .gitignore
- Add frontend build artifacts
- Add Python package artifacts
- Add IDE-specific files
- Add tokenizer cache directories

#### Commit 17: Update CHANGELOG
- Document all changes
- Add migration guide for users
- Add rollback instructions

## pyproject.toml Structure

```toml
[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "pdftranslator"
version = "0.2.0"
description = "PDF/EPUB document translation with AI-powered glossary management"
readme = "README.md"
license = {text = "MIT"}
requires-python = ">=3.11"
authors = [
    {name = "David Gonzalez", email = "david@example.com"}
]
keywords = ["pdf", "translation", "llm", "nvidia", "glossary"]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
]

dependencies = [
    "typer[all]>=0.9.0",
    "rich>=13.0.0",
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
    "psycopg[binary,pool]>=3.1.0",
    "pgvector>=0.2.0",
    "langchain-nvidia-ai-endpoints>=0.3.0",
    "langchain-core>=0.3.0",
    "langchain-text-splitters>=0.3.0",
    "transformers>=4.40.0",
    "nltk>=3.8.0",
    "fastapi>=0.110.0",
    "uvicorn[standard]>=0.27.0",
    "python-multipart>=0.0.9",
    "questionary>=2.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-cov>=4.1.0",
    "ruff>=0.3.0",
    "mypy>=1.9.0",
    "python-dotenv>=1.0.0",
]
gemini = [
    "google-generativeai>=0.5.0",
]
ollama = [
    "ollama>=0.1.0",
]
docling = [
    "docling>=2.0.0",
]

[project.scripts]
pdftranslator = "pdftranslator.cli.app:main"
pdfagent = "pdftranslator.cli.app:main"

[project.urls]
Homepage = "https://github.com/david-eve-za/PDFTranslator"
Repository = "https://github.com/david-eve-za/PDFTranslator.git"
Issues = "https://github.com/david-eve-za/PDFTranslator/issues"

[tool.setuptools.packages.find]
where = ["src"]

[tool.ruff]
line-length = 88
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP"]
ignore = ["E501"]

[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = "-v --tb=short"
```

## Migration Guide for Users

### Before (Old Structure)
```python
from src.backend.main import app
from src.core.config.settings import Settings
from src.database.models import Work
```

### After (New Structure)
```python
from pdftranslator.backend.main import app
from pdftranslator.core.config.settings import Settings
from pdftranslator.database.models import Work
```

### Running the Application

#### Before:
```bash
python PDFAgent.py cli translate document.pdf
python PDFAgent.py backend
```

#### After:
```bash
# Option 1: Using entry point script
pdftranslator cli translate document.pdf
pdftranslator backend

# Option 2: Using module execution
python -m pdftranslator cli translate document.pdf
python -m pdftranslator backend

# Option 3: Backward compatible (deprecated)
python PDFAgent.py cli translate document.pdf
```

## Testing Strategy

### Pre-Migration Tests
1. Run all existing tests to establish baseline
2. Document current test results
3. Identify any flaky tests

### During Migration
1. Run tests after each commit
2. Fix imports as needed
3. Ensure no regression

### Post-Migration Tests
1. Run full test suite
2. Test CLI commands
3. Test backend startup
4. Test frontend build
5. Test entry points

## Rollback Plan

If issues arise, rollback using:

```bash
# Rollback to main before merge
git checkout main

# Or revert specific commits
git revert <commit-hash>

# Or reset to before refactoring
git reset --hard main
```

All changes documented in CHANGELOG with branch index for easy rollback.

## Benefits of This Refactoring

1. **Standards Compliance**: Follows Python 2025 best practices
2. **Professional Structure**: Ready for PyPI distribution
3. **Better IDE Support**: Proper package structure
4. **Easier Testing**: Clear import paths
5. **Maintainability**: Consistent with modern Python projects
6. **CI/CD Ready**: Works with modern build tools
7. **Clear Entry Points**: Standard `__main__.py` and scripts
8. **Frontend Integration**: All code in one place

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Import errors | Test after each commit, fix immediately |
| Breaking existing code | Maintain backward compatible entry point |
| Test failures | Comprehensive testing before merge |
| User confusion | Clear migration guide in CHANGELOG |
| Merge conflicts | Clean branch, systematic commits |

## Success Criteria

- [ ] All tests pass
- [ ] No duplicate directories in root
- [ ] Frontend builds successfully
- [ ] Backend starts correctly
- [ ] CLI commands work
- [ ] pyproject.toml valid
- [ ] Can install with `pip install -e .`
- [ ] Can run with `python -m pdftranslator`
- [ ] CHANGELOG updated
- [ ] Documentation updated
