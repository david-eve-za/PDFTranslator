# SOLID Refactoring Design

**Date:** 2026-03-30  
**Status:** Approved  
**Scope:** Full architectural refactoring with SOLID principles

## Executive Summary

This document outlines a comprehensive refactoring of PDFTranslator to follow SOLID principles and modern Python best practices. The refactoring includes:

- Migration from singleton `GlobalConfig` to Pydantic Settings
- Implementation of Factory Pattern for LLM clients
- Dependency Injection throughout the codebase
- Separation of concerns in CLI, services, and repositories
- Removal of legacy/unused code

## Goals

1. **Testability**: Enable easy mocking through dependency injection
2. **Maintainability**: Clear separation of responsibilities
3. **Extensibility**: Easy to add new LLM providers without modifying existing code
4. **Type Safety**: Full type hints with Pydantic validation
5. **Clean Architecture**: Organize code by architectural layers

## New Directory Structure

```
PDFTranslator/
├── config/                    # Pydantic Settings configuration
│   ├── __init__.py
│   ├── settings.py           # Main Settings class with composition
│   ├── llm.py                # LLMSettings (Gemini, Nvidia, Ollama configs)
│   ├── database.py           # DatabaseSettings
│   ├── nlp.py                # NLPSettings (NER, entity extraction)
│   └── paths.py              # PathSettings
├── models/                    # Pydantic models for validation
│   ├── __init__.py
│   ├── work.py               # Work, Volume, Chapter, GlossaryEntry
│   └── schemas/              # DTOs for API boundaries
│       └── __init__.py
├── repositories/              # Data access layer
│   ├── __init__.py
│   ├── base.py               # BaseRepository abstract class
│   ├── work.py               # WorkRepository (renamed from BookRepository)
│   ├── volume.py             # VolumeRepository
│   ├── chapter.py            # ChapterRepository
│   ├── glossary.py           # GlossaryRepository
│   └── entity_blacklist.py   # EntityBlacklistRepository
├── services/                  # Business logic layer
│   ├── __init__.py
│   ├── translator.py         # TranslatorService
│   ├── glossary_translator.py # GlossaryAwareTranslator
│   ├── glossary_post_processor.py
│   ├── glossary_search.py    # Vector search service
│   ├── glossary_context.py   # Context building service
│   ├── entity_extractor.py   # NER extraction
│   ├── audio_generator.py    # Audio generation
│   ├── video_generator.py    # Video creation
│   └── text_extractor.py     # PDF/EPUB extraction
├── infrastructure/            # External integrations
│   ├── __init__.py
│   ├── llm/                  # LLM adapters
│   │   ├── __init__.py
│   │   ├── base.py           # BaseLLM abstract class
│   │   ├── factory.py        # LLMFactory
│   │   ├── protocol.py       # LLMClient Protocol
│   │   ├── gemini.py         # GeminiLLM
│   │   ├── nvidia.py         # NvidiaLLM
│   │   └── ollama.py         # OllamaLLM
│   └── audio/                # Audio/Video adapters
│       ├── __init__.py
│       └── tts.py            # TTS adapter
├── cli/                       # CLI layer
│   ├── app.py
│   ├── commands/
│   │   ├── translate.py      # Refactored from translate_chapter.py
│   │   ├── process.py
│   │   └── ...
│   └── ui/                   # UI components (new)
│       ├── __init__.py
│       ├── selection.py      # Interactive selection functions
│       └── display.py        # Display utilities
└── tests/
```

## File Migration Map

| Current Location | New Location | Notes |
|-----------------|--------------|-------|
| `GlobalConfig.py` | `config/settings.py` | Split into multiple config classes |
| `llm/base_llm.py` | `infrastructure/llm/base.py` | Updated with Settings injection |
| `llm/nvidia_llm.py` | `infrastructure/llm/nvidia.py` | Refactored with DI |
| `llm/gemini_llm.py` | `infrastructure/llm/gemini.py` | Refactored with DI |
| `llm/ollama_llm.py` | `infrastructure/llm/ollama.py` | Refactored with DI |
| `database/models.py` | `models/work.py` | Convert to Pydantic models |
| `database/repositories/*.py` | `repositories/*.py` | Refactored |
| `database/services/entity_extractor.py` | `services/entity_extractor.py` | Moved |
| `database/services/glossary_manager.py` | `services/glossary_manager.py` | Moved |
| `tools/Translator.py` | `services/translator.py` | Refactored |
| `tools/AudioGenerator.py` | `services/audio_generator.py` | Fixed duplicates |
| `tools/VideoGenerator.py` | `services/video_generator.py` | Moved |
| `tools/TextExtractor.py` | `services/text_extractor.py` | Moved |
| `tools/OverlapCleaner.py` | `services/overlap_cleaner.py` | Moved |
| `cli/commands/translate_chapter.py` | `cli/commands/translate.py` | Split UI/logic |

## Configuration System (Pydantic Settings)

### Main Settings Class

```python
# config/settings.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from config.llm import LLMSettings, LLMProvider
from config.database import DatabaseSettings
from config.nlp import NLPSettings
from config.paths import PathSettings

class Settings(BaseSettings):
    """Main application settings with nested configuration."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore"
    )
    
    # Nested configurations
    llm: LLMSettings = Field(default_factory=LLMSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    nlp: NLPSettings = Field(default_factory=NLPSettings)
    paths: PathSettings = Field(default_factory=PathSettings)
    
    # Singleton access
    _instance: "Settings | None" = None
    
    @classmethod
    def get(cls) -> "Settings":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    @classmethod
    def reset(cls):
        """Reset singleton for testing."""
        cls._instance = None
```

### LLM Settings

```python
# config/llm.py
from pydantic import BaseModel, Field
from enum import Enum

class LLMProvider(str, Enum):
    GEMINI = "gemini"
    NVIDIA = "nvidia"
    OLLAMA = "ollama"

class BCP47Language(str, Enum):
    """BCP 47 language codes for text splitting."""
    ENGLISH = "en"
    SPANISH = "es"
    CHINESE = "zh"
    JAPANESE = "ja"
    KOREAN = "ko"
    FRENCH = "fr"
    GERMAN = "de"
    ITALIAN = "it"
    PORTUGUESE = "pt"
    RUSSIAN = "ru"
    ARABIC = "ar"
    HINDI = "hi"

class GeminiConfig(BaseModel):
    model_names: list[str] = ["gemini-2.0-flash"]
    temperature: float = Field(default=0.3, ge=0.0, le=2.0)
    top_p: float = Field(default=0.95, ge=0.0, le=1.0)
    context_size: int = Field(default=1000000, gt=0)
    rate_limit: int = Field(default=15, gt=0)

class NvidiaConfig(BaseModel):
    model_name: str = "meta/llama-3.1-8b-instruct"
    temperature: float = Field(default=0.3, ge=0.0, le=2.0)
    max_output_tokens: int = Field(default=4096, gt=0)
    rate_limit: int = Field(default=30, gt=0)

class OllamaConfig(BaseModel):
    model_name: str = "llama3.2"
    temperature: float = Field(default=0.3, ge=0.0, le=2.0)
    context_size: int = Field(default=4096, gt=0)

class LLMSettings(BaseModel):
    agent: LLMProvider = LLMProvider.NVIDIA
    gemini: GeminiConfig = Field(default_factory=GeminiConfig)
    nvidia: NvidiaConfig = Field(default_factory=NvidiaConfig)
    ollama: OllamaConfig = Field(default_factory=OllamaConfig)
    
    def get_config_for_provider(self, provider: LLMProvider) -> BaseModel:
        configs = {
            LLMProvider.GEMINI: self.gemini,
            LLMProvider.NVIDIA: self.nvidia,
            LLMProvider.OLLAMA: self.ollama,
        }
        return configs[provider]
```

## LLM Factory Pattern

### Protocol Definition

```python
# infrastructure/llm/protocol.py
from typing import Protocol, runtime_checkable

@runtime_checkable
class LLMClient(Protocol):
    """Protocol defining LLM client interface."""
    
    def call_model(self, prompt: str) -> str: ...
    def get_current_model_name(self) -> str: ...
    def count_tokens(self, text: str) -> int: ...
    def split_into_limit(
        self, text: str, language: "BCP47Language" = None
    ) -> list[str]: ...
```

### Factory Implementation

```python
# infrastructure/llm/factory.py
from config.settings import Settings
from config.llm import LLMProvider
from infrastructure.llm.protocol import LLMClient

class LLMFactory:
    """Factory for creating LLM clients based on configuration."""
    
    def __init__(self, settings: Settings):
        self._settings = settings
        self._instances: dict[LLMProvider, LLMClient] = {}
    
    def create(self, provider: LLMProvider | None = None) -> LLMClient:
        provider = provider or self._settings.llm.agent
        
        # Singleton per provider
        if provider in self._instances:
            return self._instances[provider]
        
        client = self._create_client(provider)
        self._instances[provider] = client
        return client
    
    def _create_client(self, provider: LLMProvider) -> LLMClient:
        if provider == LLMProvider.GEMINI:
            from infrastructure.llm.gemini import GeminiLLM
            return GeminiLLM(self._settings)
        elif provider == LLMProvider.NVIDIA:
            from infrastructure.llm.nvidia import NvidiaLLM
            return NvidiaLLM(self._settings)
        elif provider == LLMProvider.OLLAMA:
            from infrastructure.llm.ollama import OllamaLLM
            return OllamaLLM(self._settings)
        
        raise ValueError(f"Unsupported LLM provider: {provider}")
```

## Services Layer

### TranslatorService

```python
# services/translator.py
from dataclasses import dataclass
from typing import List
from infrastructure.llm.factory import LLMFactory
from infrastructure.llm.protocol import LLMClient
from config.llm import BCP47Language

@dataclass
class TranslationResult:
    original_chunks: int
    translated_chunks: int
    text: str
    errors: List[str]

class TranslatorService:
    """Service for translating text using LLM backends."""
    
    def __init__(self, llm_factory: LLMFactory):
        self._llm_factory = llm_factory
        self._llm_client: LLMClient = llm_factory.create()
    
    def translate(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        language: BCP47Language = BCP47Language.ENGLISH,
    ) -> TranslationResult:
        chunks = self._llm_client.split_into_limit(text, language)
        translated_parts = []
        errors = []
        
        for i, chunk in enumerate(chunks):
            try:
                result = self._translate_chunk(chunk, source_lang, target_lang)
                translated_parts.append(result)
            except Exception as e:
                errors.append(f"Chunk {i+1}: {e}")
                translated_parts.append(f"[ERROR_CHUNK_{i+1}]")
        
        return TranslationResult(
            original_chunks=len(chunks),
            translated_chunks=len(translated_parts),
            text="\n\n".join(translated_parts),
            errors=errors,
        )
```

### GlossaryAwareTranslator

```python
# services/glossary_translator.py
from services.translator import TranslatorService, TranslationResult
from models.work import GlossaryEntry
from services.glossary_post_processor import GlossaryPostProcessor
from config.llm import BCP47Language

class GlossaryAwareTranslator:
    """Translator with glossary consistency through post-processing."""
    
    def __init__(
        self,
        translator: TranslatorService,
        glossary_entries: list[GlossaryEntry],
    ):
        self._translator = translator
        self._glossary_entries = glossary_entries
    
    def translate(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        target_lang_code: str,
        language: BCP47Language = BCP47Language.ENGLISH,
    ) -> TranslationResult:
        result = self._translator.translate(text, source_lang, target_lang, language)
        
        if self._glossary_entries:
            processor = GlossaryPostProcessor(self._glossary_entries, target_lang_code)
            result.text = processor.process(result.text)
        
        return result
```

## Repository Refactoring (SRP)

### GlossaryRepository - Separated Responsibilities

```python
# repositories/glossary.py
class GlossaryRepository(BaseRepository[GlossaryEntry]):
    """Basic CRUD operations for glossary entries."""
    
    def get_by_work(self, work_id: int) -> list[GlossaryEntry]: ...
    def get_by_volume(self, volume_id: int) -> list[GlossaryEntry]: ...

# services/glossary_search.py
class GlossarySearchService:
    """Handles vector similarity search."""
    
    def __init__(self, vector_store, embedding_service): ...
    def find_similar(self, term: str, limit: int = 10) -> list[tuple]: ...

# services/glossary_context.py
class GlossaryContextService:
    """Manages glossary context for translation."""
    
    def build_context_for_chapter(self, text: str, work_id: int) -> dict: ...
```

## CLI Refactoring

### Separated UI Components

```python
# cli/ui/selection.py
def select_work(repo: WorkRepository) -> Optional[Work]: ...
def select_volume(work: Work, repo: VolumeRepository) -> Optional[Volume]: ...
def select_chapter(volume: Volume, repo: ChapterRepository) -> Optional[Chapter]: ...
def select_scope() -> Optional[str]: ...

# cli/ui/display.py
def display_work_structure(work, volume_repo, chapter_repo): ...
def print_summary(success: int, failure: int, dry_run: bool): ...
```

### Clean Command Implementation

```python
# cli/commands/translate.py
@app.command("translate")
def translate(
    source_lang: str = typer.Option("en", "--source-lang", "-s"),
    target_lang: str = typer.Option("es", "--target-lang", "-t"),
):
    # Composition Root - setup dependencies
    settings = Settings.get()
    llm_factory = LLMFactory(settings)
    translator_service = TranslatorService(llm_factory)
    
    # Repositories
    work_repo = WorkRepository()
    glossary_repo = GlossaryRepository()
    
    # UI: Select work
    work = select_work(work_repo)
    if not work:
        raise typer.Exit(0)
    
    # Load glossary and create translator
    entries = glossary_repo.get_by_work(work.id)
    translator = GlossaryAwareTranslator(translator_service, entries) if entries else translator_service
    
    # Execute translation
    result = translator.translate(text, source_lang, target_lang)
    print_summary(result.translated_chunks, len(result.errors), dry_run)
```

## Legacy Code Removal

### Files to Delete

| File | Reason |
|------|--------|
| `tools/GeminiTextToSpeech.py` | Not integrated in workflow |
| `tools/DocumentTextExtractor.py` | Duplicates TextExtractor.py |
| `reviewer/` directory | Empty, use tempfile instead |
| `database/schemas/` | Empty, create `models/schemas/` |

### Code to Fix

| Location | Issue | Fix |
|----------|-------|-----|
| `AudioGenerator.py` lines 13-41, 62-92 | Duplicate `_ensure_nltk_punkt` | Keep one definition |
| `translate_chapter.py` line 696-697 | Duplicate `raise typer.Exit(0)` | Remove duplicate |

## Implementation Phases

| Phase | Description | Duration |
|-------|-------------|----------|
| 1 | Configuration (Pydantic Settings) | 1-2 days |
| 2 | LLM Factory Pattern | 1 day |
| 3 | Services refactoring | 2-3 days |
| 4 | Repositories refactoring | 1-2 days |
| 5 | CLI refactoring | 1-2 days |
| 6 | Legacy code removal | 1 day |
| 7 | Tests and validation | 1-2 days |

## Dependencies to Add

```toml
pydantic>=2.0.0
pydantic-settings>=2.0.0
```

## Benefits Summary

- **Testability**: DI enables easy mocking
- **Maintainability**: Clear responsibilities, organized code
- **Extensibility**: New LLM = new class + Factory registration
- **Validation**: Pydantic auto-validates configuration
- **Type Safety**: Full type hints throughout
- **Documentation**: Structure is self-documenting

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Breaking existing functionality | Incremental implementation, commit per phase |
| Tests failing during refactor | Fix at end with new structure |
| Broken imports from file moves | Use relative imports, update all references |
