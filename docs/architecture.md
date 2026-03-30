# PDFTranslator Architecture Documentation

## Table of Contents

1. [Overview](#overview)
2. [Directory Structure](#directory-structure)
3. [Key Design Decisions](#key-design-decisions)
4. [Module Responsibilities](#module-responsibilities)
5. [Dependency Injection Pattern](#dependency-injection-pattern)
6. [Backward Compatibility Approach](#backward-compatibility-approach)
7. [Future Migration Path](#future-migration-path)

---

## Overview

PDFTranslator is a Python application for translating PDF/EPUB documents using Large Language Models (LLMs). The architecture follows **SOLID principles** with a clear separation of concerns, dependency injection, and protocol-based abstractions.

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              CLI Layer                                   │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                        cli/app.py (Typer)                        │    │
│  │    ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │    │
│  │    │   process    │  │ build_glossary│  │generate_audio│  ...   │    │
│  │    └──────────────┘  └──────────────┘  └──────────────┘        │    │
│  └─────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                            Services Layer                                │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐     │
│  │TranslatorService│  │ GlossaryManager │  │   EntityExtractor   │     │
│  └─────────────────┘  └─────────────────┘  └─────────────────────┘     │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐     │
│  │  AudioService   │  │  VideoService   │  │ GlossaryPostProcessor│    │
│  └─────────────────┘  └─────────────────┘  └─────────────────────┘     │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    ▼                               ▼
┌──────────────────────────────┐   ┌──────────────────────────────────────┐
│     Infrastructure Layer      │   │         Database Layer               │
│  ┌────────────────────────┐  │   │  ┌────────────────────────────────┐  │
│  │      LLMFactory        │  │   │  │       DatabasePool             │  │
│  │  ┌──────────────────┐  │  │   │  │    (Singleton + ConnectionPool)│  │
│  │  │    BaseLLM       │  │  │   │  └────────────────────────────────┘  │
│  │  │ (ABC)            │  │  │   │                                      │
│  │  └──────────────────┘  │  │   │  ┌────────────────────────────────┐  │
│  │         ▲              │  │   │  │      BaseRepository<T>         │  │
│  │         │ implements   │  │   │  │      (Generic ABC)             │  │
│  │  ┌──────┴───────────┐  │  │   │  └────────────────────────────────┘  │
│  │  │                  │  │  │   │                 ▲                    │
│  │  │ GeminiLLM        │  │  │   │                 │ implements         │
│  │  │ NvidiaLLM        │  │  │   │  ┌──────────────┴───────────────┐   │
│  │  │ OllamaLLM        │  │  │   │  │ BookRepository               │   │
│  │  │                  │  │  │   │  │ ChapterRepository            │   │
│  │  └──────────────────┘  │  │   │  │ GlossaryRepository           │   │
│  └────────────────────────┘  │   │  │ EntityBlacklistRepository    │   │
│                              │   │  │ FantasyTermRepository        │   │
│  ┌────────────────────────┐  │   │  │ VolumeRepository             │   │
│  │   LLMClient Protocol   │  │   │  └──────────────────────────────┘   │
│  │   (duck typing)        │  │   │                                      │
│  └────────────────────────┘  │   │  ┌────────────────────────────────┐  │
└──────────────────────────────┘   │  │     VectorStoreService         │  │
                                   │  └────────────────────────────────┘  │
                                   └──────────────────────────────────────┘
                                                    │
                                                    ▼
                                   ┌──────────────────────────────────────┐
                                   │        Configuration Layer           │
                                   │  ┌────────────────────────────────┐  │
                                   │  │          Settings              │  │
                                   │  │  ┌─────────────────────────┐   │  │
                                   │  │  │ LLMSettings             │   │  │
                                   │  │  │ DatabaseSettings        │   │  │
                                   │  │  │ NLPSettings             │   │  │
                                   │  │  │ PathSettings            │   │  │
                                   │  │  └─────────────────────────┘   │  │
                                   │  └────────────────────────────────┘  │
                                   │         (Pydantic Settings)          │
                                   └──────────────────────────────────────┘
```

---

## Directory Structure

```
PDFTranslator/
├── cli/                          # Command-line interface layer
│   ├── __init__.py
│   ├── __main__.py               # Entry point for `python -m cli`
│   ├── app.py                    # Typer application setup
│   ├── commands/                 # CLI command implementations
│   │   ├── __init__.py
│   │   ├── process.py            # Main processing command
│   │   ├── build_glossary.py     # Glossary building command
│   │   ├── translate_chapter.py  # Chapter translation command
│   │   ├── generate_audio.py     # Audio generation command
│   │   ├── generate_video.py     # Video generation command
│   │   ├── add_to_database.py    # Database management command
│   │   ├── reset_database.py     # Database reset command
│   │   └── split_text.py         # Text splitting command
│   ├── services/                 # CLI-specific services
│   │   ├── __init__.py
│   │   ├── audio_service.py      # Audio processing service
│   │   ├── video_service.py      # Video generation service
│   │   ├── image_service.py      # Image processing service
│   │   └── glossary_post_processor.py
│   └── ui/                       # User interface components
│       ├── __init__.py
│       ├── display.py            # Display utilities (Rich)
│       └── selection.py          # User selection components
│
├── config/                       # Configuration module (Pydantic Settings)
│   ├── __init__.py
│   ├── settings.py               # Main Settings class
│   ├── llm.py                    # LLM configuration (providers, languages)
│   ├── database.py               # Database connection settings
│   ├── nlp.py                    # NLP processing settings
│   └── paths.py                  # Path configuration
│
├── infrastructure/               # Infrastructure layer (external integrations)
│   ├── __init__.py
│   └── llm/                      # LLM abstraction
│       ├── __init__.py
│       ├── protocol.py           # LLMClient Protocol (duck typing)
│       ├── base.py               # BaseLLM abstract class
│       ├── factory.py            # LLMFactory (Factory Pattern)
│       ├── gemini.py             # Google Gemini implementation
│       ├── nvidia.py             # NVIDIA NIM implementation
│       └── ollama.py             # Ollama local LLM implementation
│
├── database/                     # Data persistence layer
│   ├── __init__.py
│   ├── connection.py             # Connection pool (Singleton)
│   ├── initializer.py            # Database schema initialization
│   ├── exceptions.py             # Database-specific exceptions
│   ├── models.py                 # SQLAlchemy ORM models
│   ├── schemas/                  # Pydantic schemas
│   │   └── __init__.py
│   ├── repositories/             # Repository Pattern
│   │   ├── __init__.py
│   │   ├── base.py               # BaseRepository<T> (Generic)
│   │   ├── book_repository.py
│   │   ├── chapter_repository.py
│   │   ├── glossary_repository.py
│   │   ├── entity_blacklist_repository.py
│   │   ├── fantasy_term_repository.py
│   │   └── volume_repository.py
│   └── services/                 # Database services
│       ├── __init__.py
│       ├── vector_store.py       # Vector embeddings service
│       ├── entity_extractor.py   # Named entity extraction
│       └── glossary_manager.py   # Glossary management
│
├── services/                     # Application services layer
│   ├── __init__.py
│   ├── translator.py             # Translation orchestration
│   └── glossary_translator.py    # Glossary-aware translation
│
├── models/                       # Domain models
│   ├── __init__.py
│   └── work.py                   # Work domain model
│
├── tools/                        # Legacy tools (preserved for compatibility)
│   ├── AudioGenerator.py
│   ├── VideoGenerator.py
│   ├── Translator.py
│   ├── TextExtractor.py
│   ├── FileFinder.py
│   └── OverlapCleaner.py
│
├── tests/                        # Test suite
│   ├── __init__.py
│   ├── conftest.py               # Pytest fixtures
│   ├── cli/                      # CLI tests
│   └── database/                 # Database tests
│
├── docs/                         # Documentation
│   └── architecture.md           # This file
│
├── conftest.py                   # Root pytest fixtures
├── pytest.ini                    # Pytest configuration
├── GlobalConfig.py               # Legacy config (preserved for compatibility)
└── PDFAgent.py                   # Legacy entry point
```

---

## Key Design Decisions

### 1. Single Responsibility Principle (SRP)

Each module has one reason to change:

| Module | Responsibility |
|--------|----------------|
| `infrastructure/llm/` | LLM client creation and management |
| `config/` | Configuration loading and validation |
| `database/repositories/` | Data persistence operations |
| `database/services/` | Business logic for database operations |
| `services/` | Translation and processing orchestration |
| `cli/commands/` | User command handling |

### 2. Open/Closed Principle (OCP)

The architecture is **open for extension, closed for modification**:

- **Adding a new LLM provider**: Create a new class implementing `LLMClient` protocol, add to `LLMFactory._create_client()`. No changes to existing code.
- **Adding a new repository**: Extend `BaseRepository<T>`, implement abstract methods. No changes to base class.
- **Adding a new CLI command**: Create new file in `cli/commands/`, register in `cli/app.py`.

```python
# Adding a new LLM provider is straightforward:
class NewLLM(BaseLLM):
    def call_model(self, prompt: str) -> str:
        # Implementation
        pass
    
    # ... other methods

# Factory handles the rest
class LLMFactory:
    def _create_client(self, provider: LLMProvider) -> LLMClient:
        if provider == LLMProvider.NEW_PROVIDER:
            from infrastructure.llm.new_llm import NewLLM
            return NewLLM(self._settings)
        # ...
```

### 3. Liskov Substitution Principle (LSP)

All `LLMClient` implementations are interchangeable:

```python
# Any LLM client can be used here
def translate_text(client: LLMClient, text: str) -> str:
    return client.call_model(f"Translate: {text}")

# Works with any provider
gemini_client = GeminiLLM(settings)
nvidia_client = NvidiaLLM(settings)
ollama_client = OllamaLLM(settings)

# All are valid
translate_text(gemini_client, "Hello")
translate_text(nvidia_client, "Hello")
translate_text(ollama_client, "Hello")
```

### 4. Interface Segregation Principle (ISP)

Protocols and abstract classes are minimal:

- `LLMClient` Protocol: Only 4 methods (`call_model`, `get_current_model_name`, `count_tokens`, `split_into_limit`)
- `BaseRepository<T>`: Only 5 CRUD methods
- Clients don't depend on methods they don't use

### 5. Dependency Inversion Principle (DIP)

High-level modules depend on abstractions:

```
┌────────────────────┐         ┌─────────────────┐
│ TranslatorService  │ ──────► │   LLMClient     │
│   (High-level)     │         │   (Protocol)    │
└────────────────────┘         └─────────────────┘
                                       ▲
                                       │
                    ┌──────────────────┼──────────────────┐
                    │                  │                  │
           ┌───────────────┐  ┌───────────────┐  ┌───────────────┐
           │   GeminiLLM   │  │   NvidiaLLM   │  │   OllamaLLM   │
           │  (Low-level)  │  │  (Low-level)  │  │  (Low-level)  │
           └───────────────┘  └───────────────┘  └───────────────┘
```

---

## Module Responsibilities

### Infrastructure Layer (`infrastructure/`)

#### `infrastructure/llm/`

| Component | Purpose |
|-----------|---------|
| `protocol.py` | Defines `LLMClient` Protocol for duck typing |
| `base.py` | Abstract base class with common initialization |
| `factory.py` | Creates LLM clients based on configuration |
| `gemini.py` | Google Gemini API client |
| `nvidia.py` | NVIDIA NIM API client |
| `ollama.py` | Ollama local LLM client |

**Design Pattern**: Factory Pattern + Protocol (structural typing)

```python
# Factory creates the appropriate client
factory = LLMFactory(settings)
client = factory.create()  # Uses settings.llm.agent

# Or specify a provider
client = factory.create(LLMProvider.GEMINI)
```

### Configuration Layer (`config/`)

| Component | Purpose |
|-----------|---------|
| `settings.py` | Main `Settings` class with Pydantic validation |
| `llm.py` | LLM provider configs, language codes |
| `database.py` | Database connection settings |
| `nlp.py` | NLP processing parameters |
| `paths.py` | File system paths |

**Design Pattern**: Composition + Environment Variables

```python
# Settings uses composition
class Settings(BaseSettings):
    llm: LLMSettings
    database: DatabaseSettings
    nlp: NLPSettings
    paths: PathSettings

# Environment variables use nested delimiter
# LLM__AGENT=nvidia
# LLM__NVIDIA__TEMPERATURE=0.5
```

### Database Layer (`database/`)

#### `database/repositories/`

| Repository | Entity |
|------------|--------|
| `BookRepository` | Book metadata |
| `ChapterRepository` | Chapter content |
| `GlossaryRepository` | Translation glossary |
| `EntityBlacklistRepository` | Blacklisted entities |
| `FantasyTermRepository` | Fantasy world terms |
| `VolumeRepository` | Volume organization |

**Design Pattern**: Repository Pattern + Generic Base Class

```python
class BaseRepository(ABC, Generic[T]):
    @abstractmethod
    def get_by_id(self, id: int) -> Optional[T]: ...
    
    @abstractmethod
    def get_all(self) -> List[T]: ...
    
    @abstractmethod
    def create(self, entity: T) -> T: ...
    
    @abstractmethod
    def update(self, entity: T) -> T: ...
    
    @abstractmethod
    def delete(self, id: int) -> bool: ...
```

#### `database/services/`

| Service | Purpose |
|---------|---------|
| `VectorStoreService` | Vector embeddings for semantic search |
| `EntityExtractor` | Named entity recognition |
| `GlossaryManager` | Glossary lifecycle management |

### Services Layer (`services/`)

| Service | Purpose |
|---------|---------|
| `TranslatorService` | Orchestrates translation with chunking |
| `GlossaryTranslatorService` | Translation with glossary context |

**Key Feature**: Dependency Injection

```python
class TranslatorService:
    def __init__(self, llm_factory: LLMFactory, settings: Settings | None = None):
        self._llm_factory = llm_factory
        self._settings = settings or Settings.get()
        self._llm_client = llm_factory.create()
```

### CLI Layer (`cli/`)

| Component | Purpose |
|-----------|---------|
| `app.py` | Typer application, logging setup |
| `commands/` | Individual CLI commands |
| `services/` | CLI-specific business logic |
| `ui/` | User interface components (Rich) |

---

## Dependency Injection Pattern

### Overview

The application uses **constructor injection** for dependency management. Dependencies are passed explicitly rather than created internally.

### LLM Factory Pattern

```
┌─────────────────────────────────────────────────────────────────┐
│                      LLMFactory                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  create(provider=None) ──► LLMClient                     │   │
│  │                                                          │   │
│  │  ┌─────────────────────────────────────────────────┐     │   │
│  │  │ Singleton Instances (Thread-safe)               │     │   │
│  │  │  ┌─────────┐  ┌─────────┐  ┌─────────┐         │     │   │
│  │  │  │ Gemini  │  │ Nvidia  │  │ Ollama  │         │     │   │
│  │  │  │ Client  │  │ Client  │  │ Client  │         │     │   │
│  │  │  └─────────┘  └─────────┘  └─────────┘         │     │   │
│  │  └─────────────────────────────────────────────────┘     │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### Settings Singleton Pattern

```python
# Module-level singleton
_settings_instance: Settings | None = None

def get_settings() -> Settings:
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = Settings()
    return _settings_instance

# Can be reset for testing
def reset_settings() -> None:
    global _settings_instance
    _settings_instance = None
```

### Database Pool Singleton

```python
class DatabasePool:
    _instance: Optional["DatabasePool"] = None
    _sync_pool: Optional[ConnectionPool] = None
    _async_pool: Optional[AsyncConnectionPool] = None
    
    @classmethod
    def get_instance(cls, **kwargs) -> "DatabasePool":
        if cls._instance is None:
            cls._instance = cls(**kwargs)
        return cls._instance
```

### Service Instantiation

```python
# Services receive dependencies, not create them
factory = LLMFactory(settings)
translator = TranslatorService(factory)

# Easy to test with mocks
mock_factory = Mock()
mock_client = Mock(spec=LLMClient)
mock_factory.create.return_value = mock_client

translator = TranslatorService(mock_factory)
```

---

## Backward Compatibility Approach

### Strategy: Facade + Adapter Pattern

Legacy code is preserved while new code uses clean architecture:

```
┌─────────────────────────────────────────────────────────────────┐
│                     Legacy Entry Points                          │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐       │
│  │  PDFAgent.py  │  │ GlobalConfig  │  │   tools/      │       │
│  │  (preserved)  │  │  (preserved)  │  │  (preserved)  │       │
│  └───────────────┘  └───────────────┘  └───────────────┘       │
│         │                  │                  │                 │
│         └──────────────────┼──────────────────┘                 │
│                            │                                     │
│                            ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              Adapter/Facade Layer                         │   │
│  │  - Converts old config to Settings                        │   │
│  │  - Delegates to new services                              │   │
│  └──────────────────────────────────────────────────────────┘   │
│                            │                                     │
│                            ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              New Architecture                             │   │
│  │  - config/  - infrastructure/  - services/                │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### Preserved Components

| Legacy | Status | Notes |
|--------|--------|-------|
| `GlobalConfig.py` | Preserved | Used by `DatabasePool` for backward compatibility |
| `PDFAgent.py` | Preserved | Legacy entry point |
| `tools/*.py` | Preserved | Legacy utilities, gradually being replaced |
| `llm/*.py` | Preserved | Old LLM implementations (new in `infrastructure/llm/`) |

### Migration Helper

```python
# GlobalConfig provides backward compatibility
class GlobalConfig:
    @property
    def db_host(self) -> str:
        return self._settings.database.host
    
    # ... other properties map to Settings

# DatabasePool uses GlobalConfig as fallback
def __init__(self, host=None, ...):
    if host is None:
        from GlobalConfig import GlobalConfig
        config = GlobalConfig()
        host = config.db_host
```

---

## Future Migration Path

### Phase 1: Complete Infrastructure Migration

**Goal**: Remove legacy LLM implementations

```
Current:
├── llm/                     # Legacy (deprecated)
│   ├── base_llm.py
│   ├── gemini_llm.py
│   ├── nvidia_llm.py
│   └── ollama_llm.py
└── infrastructure/llm/      # New
    ├── base.py
    ├── gemini.py
    ├── nvidia.py
    └── ollama.py

Target:
└── infrastructure/llm/      # Single source of truth
    ├── base.py
    ├── gemini.py
    ├── nvidia.py
    └── ollama.py
```

**Steps**:
1. Update all imports from `llm.*` to `infrastructure.llm.*`
2. Add deprecation warnings to `llm/*.py`
3. Remove in next major version

### Phase 2: Service Layer Expansion

**Goal**: Extract business logic from CLI commands

```python
# Current: Business logic in commands
@app.command()
def translate(file: str):
    # ... lots of business logic ...
    
# Target: Thin commands, logic in services
@app.command()
def translate(file: str):
    service = TranslationService(factory)
    result = service.process_file(file)
    display_result(result)
```

**New Services to Create**:
- `TranslationWorkflowService` - Full translation workflow
- `GlossaryWorkflowService` - Glossary building workflow
- `MediaGenerationService` - Audio/video generation

### Phase 3: Domain Models

**Goal**: Rich domain models with validation

```python
# Current: Anemic models
class Work:
    def __init__(self, title: str, author: str):
        self.title = title
        self.author = author

# Target: Rich domain models
class Work:
    def __init__(self, title: str, author: str):
        self._title = Title(title)  # Value object
        self._author = Author(author)  # Value object
        self._chapters: list[Chapter] = []
    
    def add_chapter(self, number: int, content: str) -> Chapter:
        """Business logic in domain"""
        chapter = Chapter(number, content, self)
        self._chapters.append(chapter)
        return chapter
```

### Phase 4: Async Migration

**Goal**: Full async support for I/O operations

```python
# Current: Mixed sync/async
pool = DatabasePool.get_instance()
sync_pool = pool.get_sync_pool()

# Target: Full async
async with get_async_pool() as conn:
    repo = ChapterRepository(conn)
    chapters = await repo.get_all_async()
```

### Migration Compatibility Guarantees

| Version | Guarantee |
|---------|-----------|
| 1.x | All legacy entry points work |
| 2.x | Deprecation warnings for legacy code |
| 3.x | Legacy code removed, new API only |

### Recommended Development Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│                   New Feature Development                        │
│                                                                  │
│  1. Define in domain/       (if new domain concept)            │
│  2. Implement infrastructure/ (if new external dependency)     │
│  3. Add to services/        (business logic)                   │
│  4. Expose via cli/         (user interface)                   │
│                                                                  │
│  DO NOT:                                                         │
│  - Add new code to tools/                                        │
│  - Modify GlobalConfig.py                                        │
│  - Bypass the service layer from CLI                             │
└─────────────────────────────────────────────────────────────────┘
```

---

## Testing Strategy

### Unit Tests

Each layer can be tested in isolation:

```python
# Test LLM client without API calls
def test_gemini_llm_call_model(mocker):
    mock_settings = Mock()
    client = GeminiLLM(mock_settings)
    mocker.patch.object(client, '_call_api', return_value="response")
    
    result = client.call_model("test prompt")
    assert result == "response"

# Test service with mocked dependencies
def test_translator_service():
    mock_factory = Mock()
    mock_client = Mock(spec=LLMClient)
    mock_client.split_into_limit.return_value = ["chunk1"]
    mock_client.call_model.return_value = "translated"
    mock_factory.create.return_value = mock_client
    
    service = TranslatorService(mock_factory)
    result = service.translate("text", "en", "es")
    
    assert result.success
```

### Integration Tests

Located in `tests/database/` for database operations.

### Test Structure

```
tests/
├── conftest.py              # Shared fixtures
├── cli/                     # CLI command tests
│   └── test_glossary_post_processor.py
├── database/                # Database layer tests
│   ├── test_connection.py
│   ├── test_repositories.py
│   └── test_services.py
└── test_*.py                # Other unit tests
```

---

## Conclusion

This architecture provides:

1. **Testability**: Dependency injection enables easy mocking
2. **Extensibility**: Add new providers/repositories without modifying existing code
3. **Maintainability**: Clear separation of concerns
4. **Backward Compatibility**: Legacy code preserved during transition
5. **Type Safety**: Pydantic validation, Protocol checking

For questions or contributions, refer to the project's main documentation.
