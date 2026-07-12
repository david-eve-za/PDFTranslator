# PDFTranslator - Technical Runbook

> **PDF/EPUB → Audiobook Translation System**  
> Architecture, Data Flow, and Operations Reference

---

## 📋 Project Overview

**PDFTranslator** is a sophisticated pipeline that converts PDF/EPUB documents into multilingual audiobooks with consistent terminology via a glossary system.

### Key Capabilities
- **Document Processing**: PDF/EPUB extraction via Docling with structure preservation
- **Glossary Building**: NLTK NER + LLM validation → Vector embeddings → Consistent translations
- **Translation**: Chunked LLM processing with overlap handling + Glossary RAG injection
- **Audio Generation**: macOS `say` / Edge TTS with multiple voice options
- **Resumable Operations**: Checkpoint-based recovery for long-running glossary builds
- **Modern Frontend**: Angular 18 dashboard with real-time progress via WebSockets

---

## 🏗️ Architecture Layers

```
┌─────────────────────────────────────────────────────────────────────┐
│                         CLI COMMANDS (Typer)                        │
│  process | build-glossary | translate-chapter | generate-audio ...  │
└─────────────────────────────┬───────────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       CORE SERVICES                                 │
│  TranslationOrchestrator │ GlossaryManager │ PostProcessor │ ...   │
└─────────────────────────────┬───────────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         DATA LAYER (SQLite + WAL)                   │
│  Works/Volumes/Chapters │ Glossary + Progress │ Vector Store (RAG) │
└─────────────────────────────┬───────────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      INFRASTRUCTURE                                 │
│  LLM Clients (NIM/Gemini/Ollama) │ Docling │ TTS (say/Edge)        │
└─────────────────────────────────────────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        FRONTEND (Angular)                           │
│    Library │ Glossary │ Translation View │ Audio Player │ REST API  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🖥️ CLI Commands Reference

| Command | Purpose | Key Options |
|---------|---------|-------------|
| `process` | Full pipeline: PDF → Audio | `--source-lang`, `--target-lang`, `--format`, `--gen-video`, `--agent` |
| `build-glossary` | Extract terms → Build glossary | `--min-frequency`, `--resume`, `--force-restart`, `--dry-run` |
| `translate-chapter` | Translate specific chapters | `--work`, `--volume`, `--chapter`, `--agent` |
| `generate-audio` | TTS from translated text | `--voice`, `--format`, `--rate` |
| `split-text` | Chunk large texts | `--max-tokens`, `--overlap` |
| `add-to-database` | Import documents via Docling | `--input-path`, `--work-title` |
| `reset-database` | Drop & recreate schema | `--confirm` |

### Glossary Build Modes
```bash
# All volumes in a work (concatenated per volume)
pdftranslator build-glossary --resume

# Single volume (all chapters concatenated)
pdftranslator build-glossary  # → select "All Volume"

# Single chapter
pdftranslator build-glossary  # → select "Single Chapter"
```

---

## ⚙️ Core Services Detail

### TranslationOrchestrator (`services/translation_orchestrator.py`)
**Main pipeline coordinator** - `execute_job()`
- Chunks text with 500-token overlap for context preservation
- Manages translation → post-processing → merge workflow
- Handles glossary-aware post-processing via `GlossaryPostProcessor`
- Tracks job progress in `TranslationJobRepository`

### GlossaryManager (`database/services/glossary_manager.py`)
**Term extraction & validation pipeline** - `build_from_text()`
1. **Extract**: NLTK NER → `EntityCandidate` list
2. **Dedupe**: Filter against existing glossary (`GlossaryRepository`)
3. **Persist Progress**: Save to `GlossaryBuildProgress` (enables resume)
4. **Validate**: Batched LLM validation (type classification + initial translation)
5. **Embed**: NVIDIA embeddings via `VectorStoreService`
6. **Translate**: Batched LLM translation with glossary context
6. **Save**: `batch_create_with_embeddings()` to SQLite + Vector Store
7. **Cleanup**: Mark progress records as `saved`

**Resume Capability**: Tracks phase (`extracted`/`validated`/`translated`) and batch number per volume.

### GlossaryPostProcessor (`cli/services/glossary_post_processor.py`)
**Post-translation fixes** - `process()` / `_validate_and_fix()`
- Fixes mistranslations using LLM with context
- Removes false positives from glossary
- Enforces consistency across volumes

### GlossaryTranslator (`services/glossary_translator.py`)
**Batch term translation** - `translate_glossary()`
- Translates glossary terms in batches (auto-sized by token limits)
- Uses embeddings for context-aware translation

### EntityExtractor (`database/services/entity_extractor.py`)
**NLTK-based NER** - `extract(text, lang)`
- Fantasy-term dictionary augmentation
- Context extraction (surrounding sentences)
- Frequency counting

---

## 💾 Data Layer (SQLite + WAL)

### Connection Management
- `DatabasePool` singleton with connection pooling
- WAL mode enabled for concurrent reads/writes
- Foreign keys enforced
- `DATABASE_PATH` env var support (default: `data/translator.db`)

### Core Schema (11 Repositories)

| Repository | Tables | Purpose |
|------------|--------|---------|
| `BookRepository` | `works`, `volumes` | Work/volume metadata |
| `VolumeRepository` | `volumes` | Chapter linking, build status (`pending`/`in_progress`/`completed`/`failed`) |
| `ChapterRepository` | `chapters` | Original/translated text, order |
| `GlossaryRepository` | `glossary_entries` | Terms, translations, embeddings (BLOB) |
| `GlossaryBuildProgressRepository` | `glossary_build_progress` | Resume checkpoints (phase, batch, entity) |
| `EntityBlacklistRepository` | `entity_blacklist` | False positive suppression |
| `SubstitutionRuleRepository` | `substitution_rules` | Custom term mappings |
| `TranslationJobRepository` | `translation_jobs` | Async job tracking |
| `FantasyTermRepository` | `fantasy_terms` | Domain dictionary for NER |
| `UploadedFileRepository` | `uploaded_files` | File import tracking |
| `VectorStore` | (in-memory + SQLite) | Embeddings cache for RAG |

### Vector Store (`database/services/vector_store.py`)
- **Model**: NVIDIA NV-Embed-QA (via NIM)
- **Storage**: In-memory `dict` + SQLite persistence (`embeddings` table)
- **Search**: Cosine similarity, top-k retrieval
- **Integration**: Injected into translation prompts for glossary-aware consistency

---

## 🔌 Infrastructure Integrations

### LLM Clients (Pluggable Protocol)
```python
# Base protocol in infrastructure/llm/base.py
class BaseLLMClient:
    def call_model(self, prompt: str) -> str: ...
```

| Backend | Class | Models | Use Case |
|---------|-------|--------|----------|
| **NVIDIA NIM** | `NvidiaLLM` | Nemotron-3-Ultra, Llama-3.1 | Primary (quality + function calling) |
| **Google Gemini** | `GeminiLLM` | gemini-1.5-pro/flash | Large context fallback |
| **Ollama** | `OllamaLLM` | Any local model | Offline / privacy mode |

**Selection**: `--agent nvidia|gemini|ollama` CLI flag

### Document Extraction
- **Primary**: [Docling](https://github.com/DS4SD/docling) - Layout analysis, tables, images, TOC
- **Fallback**: PyMuPDF (fitz) for simple PDFs
- **Output**: Structured text + chapter detection + image paths

### Audio Generation (TTS)
| Engine | Voices | Formats | Notes |
|--------|--------|---------|-------|
| macOS `say` | Paulina, Jorge, Mónica, etc. | AIFF → m4a/mp3 (ffmpeg) | Default, offline |
| Edge TTS | es-MX, es-ES, en-US neural | mp3 | Cloud, SSML support |

---

## 🌐 Frontend (Angular 18 + Material)

### Structure
```
frontend/src/app/
├── core/services/        # API + WebSocket services
├── features/
│   ├── dashboard/        # Library overview
│   ├── glossary/         # Term management + build progress
│   ├── library/          # Work/Volume/Chapter browser
│   └── translation/      # Side-by-side compare
└── shared/components/    # Reusable UI
```

### Real-time Features
- **WebSocket** (`/ws/progress`) for glossary build progress
- **Server-Sent Events** alternative for simpler deployments
- **MatTree** with drag-drop for library reorganization

### API Endpoints (FastAPI)
```
GET    /api/works                    # List works
GET    /api/works/{id}               # Work detail + volumes
GET    /api/volumes/{id}/chapters    # Chapter list
POST   /api/glossary/build           # Trigger glossary build
WS     /ws/progress/{volume_id}      # Live progress
GET    /api/glossary/terms           # Search/paginate terms
PUT    /api/glossary/terms/{id}      # Edit term
POST   /api/translate/chapter        # Translate chapter
GET    /api/audio/{chapter_id}       # Audio file
```

---

## 🔄 End-to-End Data Flow

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  INPUT   │───▶│ EXTRACT  │───▶│  SPLIT   │───▶│ GLOSSARY │───▶│ EMBED    │
│ PDF/EPUB │    │ Docling  │    │ Chapters │    │ NLTK NER │    │ Vectors  │
└──────────┘    └──────────┘    └──────────┘    └────┬─────┘    └────┬─────┘
                                                      │             │
                                               ┌──────▼─────┐  ┌─────▼──────┐
                                               │ LLM Valid  │  │ Vector DB  │
                                               │ (batched)  │  │ (RAG cache)│
                                               └─────┬──────┘  └────────────┘
                                                     │
                    ┌─────────────┐    ┌─────────────┘
                    │             ▼             ▼
                    │    ┌──────────────┐   ┌──────────────┐
                    │    │  TRANSLATE   │   │  POST-PROCESS│
                    │    │ Chunked LLM  │   │  Fix glossary│
                    │    │ + Glossary   │   │  consistency │
                    │    │   RAG Inject │   └──────┬───────┘
                    │    └──────┬───────┘          │
                    │           │                  │
                    │    ┌──────▼───────┐   ┌──────▼───────┐
                    │    │   MERGE      │   │   AUDIO TTS  │
                    │    │ Chapters →   │   │ say / Edge   │
                    │    │ Full Book    │   │   → m4a/mp3  │
                    │    └──────────────┘   └──────────────┘
                    │
                    ▼
             ┌──────────────┐
             │   OUTPUT     │
             │ Audio files  │
             │ + Glossary   │
             │ + Metadata   │
             └──────────────┘
```

### Key Processing Details

**Chunking Strategy** (`TranslationOrchestrator`):
- Target: ~4000 tokens/chunk (configurable)
- Overlap: 500 tokens (preserves context across boundaries)
- Sentence-aware splitting (doesn't cut mid-sentence)

**Glossary RAG Injection**:
```python
# In translation prompt
similar_terms = vector_store.search(query_text, top_k=5)
context = "\n".join([f"{t.source} → {t.target}" for t in similar_terms])
prompt = f"Glossary:\n{context}\n\nTranslate: {chunk}"
```

**Progress Tracking** (Rich + Logging dual-mode):
- TTY detected → Rich `Progress` with live bars
- Non-TTY (CI/server) → Structured logging with ASCII bars
- Nested contexts fixed: parent creates, child reuses `Progress` instance

---

## ✨ Key Features & Patterns

| Feature | Implementation |
|---------|---------------|
| **Resumable Glossary** | `GlossaryBuildProgress` table tracks phase/batch per volume |
| **Glossary-Aware Translation** | Vector similarity search → inject top-k terms into LLM prompt |
| **Token-Chunked Processing** | 500-token overlap, sentence-boundary aware |
| **Pluggable LLM Backends** | Protocol-based (`BaseLLMClient`), CLI-switchable |
| **SQLite + WAL** | Connection pool, FK enforcement, JSON columns for contexts |
| **Rich Progress (TTY-aware)** | Nested `Progress` fixed; logs to file in CI |
| **Entity Extraction** | NLTK NER + Fantasy dictionary + LLM validation (batched) |
| **Angular Frontend** | Material Design, WebSocket progress, real-time editing |

---

## 🚀 Operations

### Environment Variables
```bash
# Database
DATABASE_PATH=data/translator.db

# NVIDIA NIM (primary LLM)
NVIDIA_API_KEY=your_key
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1

# Google Gemini (fallback)
GOOGLE_API_KEY=your_key

# Ollama (local)
OLLAMA_BASE_URL=http://localhost:11434
```

### Run Commands
```bash
# Install
pip install -e .

# Process directory
pdftranslator process ./books --target-lang es --agent nvidia

# Build glossary (interactive)
pdftranslator build-glossary --resume

# Translate specific chapter
pdftranslator translate-chapter --work 1 --volume 1 --chapter 5

# Generate audio
pdftranslator generate-audio --work 1 --format m4a
```

### Database Management
```bash
# Reset (drops all tables)
pdftranslator reset-database --confirm

# Or via Python
python -m pdftranslator.cli.commands.reset_database
```

---

## 📁 Project Structure

```
PDFTranslator/
├── src/pdftranslator/
│   ├── cli/
│   │   ├── app.py                    # Typer app + Rich console
│   │   ├── commands/
│   │   │   ├── process.py            # Main pipeline
│   │   │   ├── build_glossary.py     # Interactive glossary builder
│   │   │   ├── translate_chapter.py  # Chapter translation
│   │   │   ├── generate_audio.py     # TTS
│   │   │   ├── split_text.py         # Token chunking
│   │   │   ├── add_to_database.py    # Docling import
│   │   │   └── reset_database.py     # Schema reset
│   │   └── services/
│   │       └── glossary_post_processor.py
│   ├── database/
│   │   ├── connection.py             # DatabasePool (singleton)
│   │   ├── models.py                 # SQLAlchemy models
│   │   ├── repositories/             # 11 repository classes
│   │   ├── schemas/                  # Pydantic models
│   │   └── services/
│   │       ├── entity_extractor.py   # NLTK NER
│   │       ├── glossary_manager.py   # Main pipeline
│   │       └── vector_store.py       # Embeddings + RAG
│   ├── infrastructure/
│   │   ├── llm/                      # NIM, Gemini, Ollama clients
│   │   └── document/                 # Docling extractor
│   ├── services/
│   │   ├── translation_orchestrator.py
│   │   ├── glossary_translator.py
│   │   └── translator.py
│   ├── backend/
│   │   └── api/routes/               # FastAPI endpoints
│   └── frontend/                     # Angular 18 app
├── tests/                            # Pytest suite
└── docs/
    └── runbook.svg                   # This architecture diagram
```

---

## 🛠️ Development

### Running Tests
```bash
pytest tests/ -v
# Or specific
pytest tests/database/services/test_glossary_manager.py -v
```

### Adding New LLM Backend
1. Implement `BaseLLMClient` in `infrastructure/llm/`
2. Register in `infrastructure/llm/__init__.py`
3. Add CLI option in `cli/commands/process.py`

### Database Migrations
```bash
# Auto-create on first run (dev)
# For production: versioned migration scripts in /migrations
```

---

## 🔗 Related Documentation

- [Architecture Diagram](runbook.svg) - Visual layer overview
- [CLI Help] `pdftranslator --help`
- [API Docs] `http://localhost:8000/docs` (when backend running)

---

*Generated: 2026-07-11 | PDFTranslator v1.0*