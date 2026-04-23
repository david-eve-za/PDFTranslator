# Plan de Refactorización SOLID - PDFTranslator

**Fecha**: 2026-04-22
**Autor**: Arquitecto de Software Senior
**Estado**: Propuesta - Pendiente aprobación

---

## 1. DIAGNÓSTICO

### 1.1 Mapeo SQL → Dominio (Fuente de Verdad)

El schema consolidado (`001_schema.sql`) define **10 tablas**:

| Tabla SQL | Modelo Core/DB | Repositorio | API Route | UI Feature |
|-----------|---------------|-------------|-----------|------------|
| `works` | `Work` (core) | `BookRepository` | `/api/works` | Library |
| `volumes` | `Volume` (core) | `VolumeRepository` | `/api/volumes` | Library |
| `chapters` | `Chapter` (core) | `ChapterRepository` | `/api/chapters` | Library |
| `glossary_terms` | `GlossaryEntry` (core) | `GlossaryRepository` | `/api/glossary` | Glossary |
| `term_contexts` | `TermContext` (core) | `GlossaryRepository` | — | Glossary |
| `context_examples` | `ContextExample` (core) | `GlossaryRepository` | — | Glossary |
| `entity_blacklist` | `EntityBlacklist` (DB) | `EntityBlacklistRepository` | — | Settings |
| `fantasy_terms` | `FantasyTerm` (DB) | `FantasyTermRepository` | — | Settings |
| `uploaded_files` | `UploadedFile` (DB) | `UploadedFileRepository` | `/api/files` | Library |
| `text_substitution_rules` | `SubstitutionRule` (DB) | `SubstitutionRuleRepository` | `/api/substitution-rules` | Settings |
| `glossary_build_progress` | `GlossaryBuildProgress` (DB) | `GlossaryBuildProgressRepository` | — | Glossary |

### 1.2 Violaciones SOLID Identificadas

#### S — Single Responsibility Principle

| ID | Violación | Ubicación | Severidad |
|----|----------|-----------|-----------|
| SRP-1 | `GlossaryManager` (719 líneas): orquesta extracción, validación LLM, embeddings, traducciones, guardado, y resume | `database/services/glossary_manager.py` | CRÍTICA |
| SRP-2 | `translate_chapter.py` (804 líneas): contiene UI, lógica de negocio, selección interactiva, y clase `GlossaryAwareTranslator` | `cli/commands/translate_chapter.py` | CRÍTICA |
| SRP-3 | `VectorStoreService` hace embeddings Y reranking Y similitud coseno Y rerank de documentos | `database/services/vector_store.py` | ALTA |
| SRP-4 | `_work_to_response()` en `works.py` crea repos por obra y consulta capítulos dentro de un loop | `backend/api/routes/works.py:106-149` | ALTA |
| SRP-5 | `FileService` (244 líneas): validación, sanitización, parseo, creación de work/volume, extracción de texto, cleanup | `backend/services/file_service.py` | ALTA |
| SRP-6 | `process.py` inicializa servicios concretos, no acepta inyección | `cli/commands/process.py:211-223` | MEDIA |
| SRP-7 | `AudioGenerator` acopla TTS (macOS `say`) con merge (ffmpeg) con normalización de texto | `tools/AudioGenerator.py` | MEDIA |

#### O — Open/Closed Principle

| ID | Violación | Ubicación | Severidad |
|----|----------|-----------|-----------|
| OCP-1 | `tools/Translator.py` usa `if/elif` para crear LLM client en vez de usar Factory | `tools/Translator.py:31-41` | CRÍTICA |
| OCP-2 | `GlossaryManager._ensure_llm()` hardcodea `NvidiaLLM` — imposible usar otro proveedor | `database/services/glossary_manager.py:45-51` | CRÍTICA |
| OCP-3 | `VectorStoreService` hardcodea `NVIDIAEmbeddings` y `NVIDIARerank` — no extensible a otros proveedores | `database/services/vector_store.py:29-43` | ALTA |
| OCP-4 | `AudioGenerator` hardcodea macOS `say` + `ffmpeg` — no extensible a otros backends TTS | `tools/AudioGenerator.py:56,111,170` | ALTA |
| OCP-5 | `_calculate_validation_batch_size()` accede a `self._llm_client._settings.llm.nvidia.max_output_tokens` — rompe si el proveedor no es NVIDIA | `glossary_manager.py:136` | ALTA |

#### L — Liskov Substitution Principle

| ID | Violación | Ubicación | Severidad |
|----|----------|-----------|-----------|
| LSP-1 | `GlossaryBuildProgressRepository` y `UploadedFileRepository` NO extienden `BaseRepository[T]` — no son sustituibles | `database/repositories/` | ALTA |
| LSP-2 | CLI `GlossaryAwareTranslator` hereda de `tools.Translator` (legacy) pero rompe contrato: redefine `_translate_single_chunk` con recursión infinita potencial (línea 446) | `cli/commands/translate_chapter.py:313,446` | CRÍTICA |
| LSP-3 | `SubstitutionRuleRepository.get_all()` tiene firma diferente (`active_only: bool = False`) vs `BaseRepository.get_all()` | `database/repositories/substitution_rule_repository.py` | MEDIA |

#### I — Interface Segregation Principle

| ID | Violación | Ubicación | Severidad |
|----|----------|-----------|-----------|
| ISP-1 | `LLMClient` Protocol exige 4 métodos pero muchos consumidores solo necesitan `call_model()` | `infrastructure/llm/protocol.py` | ALTA |
| ISP-2 | `BaseRepository[T]` exige CRUD completo pero `GlossaryBuildProgressRepository` solo necesita operaciones de batch | `database/repositories/base.py` | ALTA |
| ISP-3 | `VectorStoreService` expone embedding + reranking + similitud — los repositorios solo necesitan `embed_query/embed_documents` | `database/services/vector_store.py` | MEDIA |

#### D — Dependency Inversion Principle

| ID | Violación | Ubicación | Severidad |
|----|----------|-----------|-----------|
| DIP-1 | `GlossaryManager` depende de `NvidiaLLM` (concreto) en vez de `LLMClient` (abstracción) | `glossary_manager.py:31,43,50` | CRÍTICA |
| DIP-2 | `VectorStoreService` depende de `NVIDIAEmbeddings`/`NVIDIARerank` (concreto) | `vector_store.py:3,29-43` | CRÍTICA |
| DIP-3 | Repositories crean `DatabasePool.get_instance()` internamente — dependen de singleton concreto | Todos los repos | ALTA |
| DIP-4 | CLI commands instancian repos directamente (`BookRepository()`) sin inyección | `cli/commands/translate_chapter.py:681-684` | ALTA |
| DIP-5 | `core/exceptions/__init__.py` importa de `database.exceptions` — core depende de infraestructura (inversión de capas) | `core/exceptions/__init__.py` | ALTA |
| DIP-6 | `services/glossary_translator.py` importa de `cli/services/glossary_post_processor.py` — services depende de CLI (inversión) | `services/glossary_translator.py:9` | CRÍTICA |
| DIP-7 | `FileService` importa `TextExtractor` de tools — backend depende de tools legacy | `backend/services/file_service.py:17` | MEDIA |

### 1.3 Problemas Estructurales Adicionales

| ID | Problema | Detalle |
|----|---------|---------|
| DUP-1 | Dos `GlossaryAwareTranslator` independientes | `cli/commands/translate_chapter.py:313` vs `services/glossary_translator.py:14` |
| DUP-2 | Dos `TermContext` con campos diferentes | `core/models/work.py` (sin `examples`) vs `database/models.py` (con `examples`) |
| DUP-3 | Dos `ContextExample` | `core/models/work.py` vs `database/models.py` |
| DUP-4 | `_get_chapter_sort_key`, `_format_chapter_display`, `_select_work_interactive` duplicados en múltiples comandos CLI | `translate_chapter.py`, `build_glossary.py`, `generate_audio.py` |
| DUP-5 | `BookRepository.find_all()` idéntico a `get_all()` | `database/repositories/book_repository.py` |
| DUP-6 | Schema SQL duplicado en `src/` y `Docker/` | `database/schemas/001_schema.sql` vs `Docker/database/init/001_schema.sql` |
| MOD-1 | `GlossaryEntry` no mapea columnas SQL: `notes`, `do_not_translate`, `is_verified`, `confidence` faltan | `core/models/work.py` vs SQL |
| MOD-2 | `VolumeRepository.create/update` no retorna campos glossary en RETURNING | `database/repositories/volume_repository.py` |
| MOD-3 | `GlossaryRepository._row_to_glossary_entry` no mapea `notes` | `database/repositories/glossary_repository.py` |
| SHD-1 | `ConnectionError` en `database/exceptions.py` oculta el builtin Python | `database/exceptions.py` |
| SIN-1 | Dos patrones singleton inconsistentes: Settings (función) vs DatabasePool (classmethod) | `config/settings.py` vs `database/connection.py` |
| FRG-1 | `_row_to_*` usan index posicional `row[0]`, `row[1]` en vez de named columns | Todos los repos |
| N+1-1 | `_work_to_response()` crea repos dentro de loops anidados | `backend/api/routes/works.py:108-118` |

### 1.4 Código Legacy / Muerto

| Archivo | Estado | Acción |
|---------|--------|--------|
| `tools/Translator.py` | LEGACY — reemplazado por `services/translator.py` | Eliminar tras migración |
| `tools/TextExtractor.py` | LEGACY — reemplazado por `infrastructure/document/docling_extractor.py` | Eliminar tras migración |
| `tools/VideoGenerator.py` | Funcionalidad marginal | Evaluar |
| `tools/OverlapCleaner.py` | Singleton metaclass innecesario | Simplificar |
| `PDFAgent.py` | DEPRECATED — delega a `__main__.py` | Mantiene compatibilidad |

---

## 2. BRAINSTORMING DE SOLUCIONES

### 2.1 Enfoque A: Refactorización Incremental Estranguladora (Recomendado)

**Principio**: Crear nuevas abstracciones al lado del código legacy, migrar consumidores gradualmente, eliminar legacy cuando cero consumidores.

| Dimensión | Evaluación |
|-----------|------------|
| Complejidad | **Baja-Media** — cada paso es pequeño y reversible |
| Mantenibilidad | **Alta** — no rompe nada en producción |
| Riesgo | **Bajo** — código viejo sigue funcionando hasta eliminación |
| Impacto en performance | **Nulo** — sin cambios en hot paths hasta migración completa |
| Timeline | **8-12 semanas** |

**Ventajas**:
- Zero downtime garantizado
- Cada PR es atomico y testeable
- Rollback trivial por phase
- Compatible con desarrollo continuo

**Desventajas**:
- Período de coexistencia código viejo/nuevo
- Requiere disciplina para no posponer eliminación

### 2.2 Enfoque B: Reescritura por Capas (Big Bang por Capa)

**Principio**: Reescribir una capa completa a la vez (domain → infrastructure → services → presentation).

| Dimensión | Evaluación |
|-----------|------------|
| Complejidad | **Alta** — cambios masivos por capa |
| Mantenibilidad | **Media-Alta** — resultado limpio |
| Riesgo | **Alto** — cada capa completa debe funcionar antes de pasar a la siguiente |
| Impacto en performance | **Medio** — posible degradación durante transición |
| Timeline | **4-6 semanas** (pero con riesgo de rollback masivo) |

**Ventajas**:
- Resultado limpio más rápido
- No hay coexistencia de código viejo/nuevo

**Desventajas**:
- Riesgo de ruptura alta
- Difícil rollback parcial
- Bloquea desarrollo de features durante refactoring

### 2.3 Enfoque C: Strangler Fig con Facade (Híbrido)

**Principio**: Crear facades/ports que deleguen al código legacy, reemplazar implementaciones detrás de las facades una por una.

| Dimensión | Evaluación |
|-----------|------------|
| Complejidad | **Media** — facades adicionales pero aislamiento completo |
| Mantenibilidad | **Alta** — aislamiento perfecto |
| Riesgo | **Bajo-Medio** — cada implementación se reemplaza independientemente |
| Impacto en performance | **Mínimo** — overhead de facade despreciable |
| Timeline | **6-8 semanas** |

**Ventajas**:
- Aislamiento completo del legacy
- Permite testing de contratos antes de reemplazar
- Cada facade es un contrato que sobrevive al legacy

**Desventajas**:
- Capa adicional de indirección
- Más archivos inicialmente

### 2.4 Decisión: Enfoque A (Incremental Estrangulador)

**Justificación**:
1. El proyecto está en producción activa con CLI y backend funcionales
2. No hay CI/CD automatizado que garantice regresiones → minimizar riesgo
3. Los tests actuales cubren parcialmente — necesitamos seguridad incremental
4. El Enfoque C es excelente pero añade complejidad de facades que no justifica el overhead para este tamaño de proyecto
5. El Enfoque B es inaceptable por riesgo de ruptura

**Adaptación**: Usaremos patrones del Enfoque C (Protocol como contrato) pero con la cadencia del Enfoque A (un módulo por vez, tests primero).

---

## 3. DECISIÓN ARQUITECTÓNICA

### 3.1 Arquitectura Objetivo: Clean Architecture con 4 Capas

```
┌─────────────────────────────────────────────────────────┐
│                    PRESENTATION                         │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │  CLI (Typer) │  │ Backend API  │  │  Angular SPA  │  │
│  │  commands/   │  │  routes/     │  │  frontend/    │  │
│  └──────┬───────┘  └──────┬───────┘  └───────┬───────┘  │
│         │                 │                  │          │
├─────────┼─────────────────┼──────────────────┼──────────┤
│         │         APPLICATION (Use Cases)     │          │
│  ┌──────▼──────────────────▼──────────────────▼───────┐  │
│  │  Application Services                              │  │
│  │  - TranslationService (orquesta traducción)        │  │
│  │  - GlossaryBuildService (orquesta build pipeline)  │  │
│  │  - AudioGenerationService (orquesta TTS)           │  │
│  │  - DocumentProcessingService (orquesta extracción) │  │
│  │  - FileUploadService (orquesta uploads)            │  │
│  └────────────────────┬───────────────────────────────┘  │
│                       │                                  │
├───────────────────────┼──────────────────────────────────┤
│                       │         DOMAIN                    │
│  ┌────────────────────▼───────────────────────────────┐  │
│  │  Domain Models           │  Domain Protocols        │  │
│  │  - Work, Volume, Chapter │  - LLMClient             │  │
│  │  - GlossaryEntry         │  - EmbeddingProvider     │  │
│  │  - EntityCandidate       │  - RerankingProvider     │  │
│  │  - TranslationResult     │  - TextExtractor         │  │
│  │  - SubstitutionRule      │  - AudioSynthesizer      │  │
│  │                          │  - DocumentParser         │  │
│  │  Domain Services         │  - GlossaryValidator     │  │
│  │  - GlossaryPostProcessor │  - TranslationPrompter   │  │
│  └────────────────────────┬───────────────────────────┘  │
│                           │                              │
├───────────────────────────┼──────────────────────────────┤
│                    INFRASTRUCTURE                        │
│  ┌────────────────────────▼───────────────────────────┐  │
│  │  LLM Implementations    │  Database Repositories    │  │
│  │  - NvidiaLLM            │  - BookRepository         │  │
│  │  - GeminiLLM            │  - VolumeRepository       │  │
│  │  - OllamaLLM            │  - ChapterRepository      │  │
│  │                         │  - GlossaryRepository     │  │
│  │  Embedding Providers    │  - ...                     │  │
│  │  - NvidiaEmbeddingProvider                          │  │
│  │                         │  Document Parsers          │  │
│  │  Audio Synthesizers     │  - DoclingParser           │  │
│  │  - MacSaySynthesizer    │  - PyMuPdfParser (legacy)  │  │
│  │  - FishSpeechSynthesizer│                            │  │
│  │  - MlxAudioSynthesizer  │  TTS Prompt Builder        │  │
│  └─────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### 3.2 Regla de Dependencia

**Las flechas de dependencia SOLO apuntan hacia adentro** (hacia Domain):

```
Presentation → Application → Domain ← Infrastructure
```

- **Domain** NO depende de nada (0 imports de infraestructura, 0 imports de application)
- **Application** depende de Domain (importa modelos y protocols)
- **Infrastructure** depende de Domain (implementa protocols)
- **Presentation** depende de Application (invoca use cases)

### 3.3 Cambios Arquitectónicos Clave

#### 3.3.1 Domain Protocols (nuevos)

```python
# domain/protocols/embedding.py
class EmbeddingProvider(Protocol):
    def embed_query(self, text: str) -> list[float]: ...
    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

# domain/protocols/reranking.py
class RerankingProvider(Protocol):
    def rerank(self, query: str, documents: list[Document], top_n: int) -> list[Document]: ...

# domain/protocols/audio_synthesizer.py
class AudioSynthesizer(Protocol):
    def synthesize(self, text: str, output_path: Path, voice: str) -> bool: ...
    def merge_audio(self, audio_files: list[Path], output_path: Path) -> bool: ...
    @property
    def is_available(self) -> bool: ...

# domain/protocols/document_parser.py
class DocumentParser(Protocol):
    def parse(self, file_path: str) -> str: ...
    @property
    def supported_extensions(self) -> set[str]: ...
```

#### 3.3.2 LLMClient Protocol Segregado (ISP)

```python
# domain/protocols/llm.py
class TextGenerator(Protocol):
    """Interfaz mínima para generación de texto."""
    def generate(self, prompt: str) -> str: ...

class TokenCounter(Protocol):
    """Interfaz para conteo de tokens."""
    def count_tokens(self, text: str) -> int: ...

class TextSplitter(Protocol):
    """Interfaz para división de texto."""
    def split_into_limit(self, text: str, language: BCP47Language = ...) -> list[str]: ...

# LLMClient combina las tres (para quienes necesitan todo)
class LLMClient(TextGenerator, TokenCounter, TextSplitter, Protocol):
    """LLM client completo — compuesto de interfaces segregadas."""
    ...
```

#### 3.3.3 Repository Interfaces Segregadas (ISP)

```python
# domain/protocols/repositories.py
class ReadRepository(Protocol[T]):
    def get_by_id(self, id: int) -> T | None: ...
    def get_all(self) -> list[T]: ...

class WriteRepository(Protocol[T]):
    def create(self, entity: T) -> T: ...
    def update(self, entity: T) -> T: ...
    def delete(self, id: int) -> bool: ...

class Repository(ReadRepository[T], WriteRepository[T], Protocol):
    """Full CRUD repository — compuesto de read + write."""
    ...

# Interfaces específicas para repos que no son CRUD
class GlossaryProgressTracker(Protocol):
    def save_extracted(self, work_id: int, volume_id: int, entities: list) -> list: ...
    def get_pending_for_phase(self, work_id: int, volume_id: int, phase: str) -> list: ...
    def batch_update_phase(self, ids: list[int], phase: str, batch_num: int | None = None) -> None: ...
    def get_resume_point(self, work_id: int, volume_id: int) -> tuple[str, int | None]: ...
    def cleanup_completed(self, volume_id: int) -> None: ...
```

#### 3.3.4 Inyección de Dependencias (sin framework)

Se usará **inyección por constructor** (patrón ya parcialmente presente). No se introduce `dependency-injector` para evitar over-engineering — el proyecto no es lo suficientemente grande para justificar un contenedor DI.

```python
# ANTES (DIP violation):
class GlossaryManager:
    def _ensure_llm(self):
        settings = Settings.get()
        self._llm_client = NvidiaLLM(settings)  # Concreto!

# DESPUÉS (DIP compliant):
class GlossaryManager:
    def __init__(
        self,
        llm_client: LLMClient,       # Abstracción
        embedder: EmbeddingProvider,   # Abstracción
        extractor: EntityExtractor,
        glossary_repo: GlossaryRepository,
        progress_tracker: GlossaryProgressTracker,
    ):
        self._llm_client = llm_client
        self._embedder = embedder
        ...
```

#### 3.3.5 Eliminación de Singleton Acoplado

```python
# ANTES: Repos crea pool internamente
class BookRepository(BaseRepository[Work]):
    def __init__(self, pool=None):
        self._pool = pool or DatabasePool.get_instance()  # Acoplado!

# DESPUÉS: Pool inyectado por Application Service
class BookRepository:
    def __init__(self, pool: ConnectionPool):
        self._pool = pool  # Inyectado
```

### 3.4 Estructura de Directorios Objetivo

```
src/pdftranslator/
├── domain/                          # NUEVO — Capa de dominio pura
│   ├── __init__.py
│   ├── models/                      # Modelos de dominio (desde core/models)
│   │   ├── __init__.py
│   │   ├── work.py                  # Work, Volume, Chapter
│   │   ├── glossary.py              # GlossaryEntry, TermContext, ContextExample
│   │   ├── entity.py                # EntityCandidate, BuildResult, GlossaryBuildProgress
│   │   ├── file.py                  # UploadedFile
│   │   └── substitution.py          # SubstitutionRule
│   ├── protocols/                   # NUEVO — Interfaces de dominio
│   │   ├── __init__.py
│   │   ├── llm.py                   # TextGenerator, TokenCounter, TextSplitter, LLMClient
│   │   ├── embedding.py             # EmbeddingProvider
│   │   ├── reranking.py             # RerankingProvider
│   │   ├── audio_synthesizer.py     # AudioSynthesizer
│   │   ├── document_parser.py       # DocumentParser
│   │   └── repositories.py          # ReadRepository, WriteRepository, GlossaryProgressTracker
│   ├── services/                    # NUEVO — Servicios de dominio puro
│   │   ├── __init__.py
│   │   └── glossary_post_processor.py  # Movido desde cli/services
│   └── exceptions/                  # NUEVO — Excepciones de dominio
│       ├── __init__.py
│       └── errors.py                # DatabaseError, EntityNotFoundError, etc.
│
├── application/                     # NUEVO — Casos de uso
│   ├── __init__.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── translation_service.py   # Orquesta traducción
│   │   ├── glossary_build_service.py # Orquesta build pipeline
│   │   ├── audio_service.py         # Orquesta TTS
│   │   ├── document_service.py      # Orquesta extracción + parseo
│   │   └── file_upload_service.py   # Orquesta uploads
│   └── dto/                         # Data Transfer Objects (API schemas)
│       ├── __init__.py
│       └── schemas.py               # Desde backend/api/models/schemas.py
│
├── infrastructure/                  # Implementaciones concretas
│   ├── __init__.py
│   ├── llm/                         # SIN CAMBIOS (ya bien estructurado)
│   │   ├── protocol.py → MOVIDO a domain/protocols/llm.py
│   │   ├── base.py
│   │   ├── factory.py
│   │   ├── nvidia.py
│   │   ├── gemini.py
│   │   └── ollama.py
│   ├── embedding/                   # NUEVO — desde database/services/vector_store.py
│   │   ├── __init__.py
│   │   ├── nvidia_embedding.py      # Implementa EmbeddingProvider
│   │   └── nvidia_reranking.py      # Implementa RerankingProvider
│   ├── audio/                       # NUEVO — desde tools/AudioGenerator.py
│   │   ├── __init__.py
│   │   ├── mac_say_synthesizer.py   # Implementa AudioSynthesizer (macOS say)
│   │   ├── mlx_audio_synthesizer.py # Implementa AudioSynthesizer (MLX-Audio)
│   │   └── ffmpeg_merger.py         # Merge de audio files
│   ├── document/                    # SIN CAMBIOS mayores
│   │   ├── docling_extractor.py
│   │   └── section_grouper.py
│   └── database/                    # DESDE database/
│       ├── __init__.py
│       ├── connection.py
│       ├── initializer.py
│       ├── schemas/
│       └── repositories/
│           ├── base.py
│           ├── book_repository.py
│           ├── chapter_repository.py
│           ├── volume_repository.py
│           ├── glossary_repository.py
│           ├── glossary_build_progress_repository.py
│           ├── entity_blacklist_repository.py
│           ├── fantasy_term_repository.py
│           ├── substitution_rule_repository.py
│           └── uploaded_file_repository.py
│
├── presentation/                    # Capa de presentación
│   ├── __init__.py
│   ├── cli/                         # DESDE cli/
│   │   ├── app.py
│   │   ├── commands/
│   │   │   ├── process.py
│   │   │   ├── add_to_database.py
│   │   │   ├── split_text.py
│   │   │   ├── translate_chapter.py
│   │   │   ├── build_glossary.py
│   │   │   ├── generate_audio.py
│   │   │   └── reset_database.py
│   │   └── ui/
│   │       ├── display.py
│   │       └── selection.py
│   └── backend/                     # DESDE backend/
│       ├── main.py
│       └── api/
│           └── routes/
│
├── core/                            # DEPRECATED — migrar a domain/
│   └── config/                      # MANTENER — configuración es cross-cutting
│       ├── settings.py
│       ├── llm.py
│       ├── database.py
│       ├── paths.py
│       ├── processing.py
│       ├── nlp.py
│       └── document.py
│
└── tools/                           # DEPRECATED — migrar a infrastructure/
    ├── Translator.py → ELIMINAR (reemplazado por application/services/translation_service.py)
    ├── TextExtractor.py → ELIMINAR (reemplazado por infrastructure/document/)
    ├── AudioGenerator.py → MIGRAR a infrastructure/audio/mac_say_synthesizer.py
    ├── VideoGenerator.py → EVALUAR
    ├── FileFinder.py → MANTENER (patrón Strategy correcto)
    └── OverlapCleaner.py → SIMPLIFICAR
```

---

## 4. PLAN PASO A PASO

### Fase 0: Preparación (Semana 1)

**Objetivo**: Crear punto de restauración, baseline de tests, infraestructura de validación.

| # | Tarea | Archivos | Principio |
|---|-------|----------|-----------|
| 0.1 | Crear tag `refactor-safe-point` en git | — | Seguridad |
| 0.2 | Crear branch `refactor/solid-phase-0` | — | Seguridad |
| 0.3 | Ejecutar tests existentes y registrar baseline | `pytest --cov --tb=short > baseline_coverage.txt` | Métrica |
| 0.4 | Medir complejidad ciclomática baseline | `ruff check --select C901 . > baseline_complexity.txt` | Métrica |
| 0.5 | Crear script `scripts/refactor_metrics.sh` que ejecuta tests + coverage + complexity | NUEVO | Validación |
| 0.6 | Añadir `pytest-cov` y `ruff` como deps dev si no existen | `pyproject.toml` | Tooling |
| 0.7 | Documentar baseline en `docs/plans/refactor-baseline.md` | NUEVO | Documentación |

**Criterio de salida**: Tag creado, baseline documentado, script de métricas funcional.

### Fase 1: Domain Layer — Modelos y Protocolos (Semana 2-3)

**Objetivo**: Crear la capa de dominio pura sin romper nada existente.

| # | Tarea | Archivos | Principio | Tests |
|---|-------|----------|-----------|-------|
| 1.1 | Crear `domain/models/` y mover modelos desde `core/models/` y `database/models/` | `domain/models/*.py` | SRP | Unit tests de modelos |
| 1.2 | Consolidar `TermContext` y `ContextExample` — versión única con `examples` | `domain/models/glossary.py` | SRP-DUP | Tests existentes |
| 1.3 | Completar `GlossaryEntry` con `notes`, `do_not_translate`, `is_verified`, `confidence` | `domain/models/glossary.py` | MOD-1 | Test campos nuevos |
| 1.4 | Crear `domain/exceptions/` — mover excepciones desde `database/exceptions.py`, renombrar `ConnectionError` → `DBConnectionError` | `domain/exceptions/errors.py` | DIP-5, SHD-1 | Tests existentes |
| 1.5 | Crear `domain/protocols/llm.py` — segregar `LLMClient` en `TextGenerator`, `TokenCounter`, `TextSplitter` | `domain/protocols/llm.py` | ISP-1 | Protocol compliance tests |
| 1.6 | Crear `domain/protocols/embedding.py` — `EmbeddingProvider` | `domain/protocols/embedding.py` | OCP-3, ISP-3 | Protocol compliance |
| 1.7 | Crear `domain/protocols/reranking.py` — `RerankingProvider` | `domain/protocols/reranking.py` | OCP-3, ISP-3 | Protocol compliance |
| 1.8 | Crear `domain/protocols/audio_synthesizer.py` — `AudioSynthesizer` | `domain/protocols/audio_synthesizer.py` | OCP-4 | Protocol compliance |
| 1.9 | Crear `domain/protocols/document_parser.py` — `DocumentParser` | `domain/protocols/document_parser.py` | DIP-7 | Protocol compliance |
| 1.10 | Crear `domain/protocols/repositories.py` — segregar en `ReadRepository`, `WriteRepository`, `GlossaryProgressTracker` | `domain/protocols/repositories.py` | ISP-2, LSP-1 | Protocol compliance |
| 1.11 | Mover `GlossaryPostProcessor` a `domain/services/` | `domain/services/glossary_post_processor.py` | DIP-6 | Tests existentes |
| 1.12 | Crear `domain/models/entity.py` — mover `EntityCandidate`, `BuildResult`, `GlossaryBuildProgress`, `EntityBlacklist`, `FantasyTerm` | `domain/models/entity.py` | SRP-1 parcial | Tests existentes |
| 1.13 | Actualizar imports en `core/models/__init__.py` y `database/models.py` para re-exportar desde `domain/` | Compatibilidad | — | Tests existentes pasan |

**Criterio de salida**:
- `domain/` existe con modelos, protocols, services, exceptions
- Todos los imports existentes siguen funcionando (re-exports)
- Tests existentes pasan 100%
- Nuevos protocol compliance tests pasan

### Fase 2: Infrastructure Layer — Implementar Protocols (Semana 3-4)

**Objetivo**: Hacer que las implementaciones concretas cumplan los protocols de domain.

| # | Tarea | Archivos | Principio | Tests |
|---|-------|----------|-----------|-------|
| 2.1 | `NvidiaLLM`, `GeminiLLM`, `OllamaLLM` implementan `LLMClient` (ya lo hacen — verificar) | `infrastructure/llm/*.py` | LSP | Protocol isinstance tests |
| 2.2 | Crear `infrastructure/embedding/nvidia_embedding.py` — implementa `EmbeddingProvider` | NUEVO | OCP-3, DIP-2 | Unit tests con mock |
| 2.3 | Crear `infrastructure/embedding/nvidia_reranking.py` — implementa `RerankingProvider` | NUEVO | OCP-3, DIP-2 | Unit tests con mock |
| 2.4 | Adaptar `VectorStoreService` para usar `EmbeddingProvider` y `RerankingProvider` inyectados | `database/services/vector_store.py` | DIP-2 | Tests existentes |
| 2.5 | Crear `infrastructure/audio/mac_say_synthesizer.py` — implementa `AudioSynthesizer` | NUEVO | OCP-4, SRP-7 | Unit tests con mock subprocess |
| 2.6 | Crear `infrastructure/audio/ffmpeg_merger.py` — extraer lógica de merge | NUEVO | SRP-7 | Unit tests con mock subprocess |
| 2.7 | Hacer que `GlossaryBuildProgressRepository` implemente `GlossaryProgressTracker` | `database/repositories/` | LSP-1 | Protocol isinstance test |
| 2.8 | Hacer que `UploadedFileRepository` implemente `ReadRepository` + `WriteRepository` | `database/repositories/` | LSP-1 | Protocol isinstance test |
| 2.9 | `DoclingExtractor` implementa `DocumentParser` | `infrastructure/document/` | DIP-7 | Protocol isinstance test |
| 2.10 | Eliminar `infrastructure/llm/protocol.py` — reemplazado por `domain/protocols/llm.py` | MOVER | ISP-1 | Import tests |
| 2.11 | Repositories: aceptar `ConnectionPool` por inyección en vez de `DatabasePool.get_instance()` | Todos los repos | DIP-3 | Tests con mock pool |

**Criterio de salida**:
- Todas las implementaciones concretas satisfacen protocols de domain
- `isinstance(obj, Protocol)` pasa para todas las implementaciones
- VectorStoreService no importa directamente NVIDIA
- Tests existentes pasan

### Fase 3: Application Layer — Servicios de Caso de Uso (Semana 4-6)

**Objetivo**: Crear servicios de aplicación que orquesten casos de uso sin depender de implementaciones concretas.

| # | Tarea | Archivos | Principio | Tests |
|---|-------|----------|-----------|-------|
| 3.1 | Crear `application/services/translation_service.py` — orquesta traducción con DI | NUEVO | SRP-2 parcial | Integration tests |
| 3.2 | Crear `application/services/glossary_build_service.py` — descompone `GlossaryManager` en pipeline con steps inyectables | NUEVO | SRP-1 | Tests de pipeline |
| 3.3 | Crear `application/services/audio_service.py` — orquesta TTS con `AudioSynthesizer` inyectado | NUEVO | SRP-7 | Unit tests |
| 3.4 | Crear `application/services/document_service.py` — orquesta extracción con `DocumentParser` inyectado | NUEVO | DIP-7 | Unit tests |
| 3.5 | Crear `application/services/file_upload_service.py` — refactor de `FileService` con DI | NUEVO | SRP-5 | Tests existentes adaptados |
| 3.6 | Mover API schemas a `application/dto/schemas.py` | MOVER | SRP | Tests existentes |
| 3.7 | Mover `ParsedFilename`, `ProcessingResult` a `application/dto/` | MOVER | SRP-5 | — |
| 3.8 | `GlossaryBuildService` acepta `LLMClient` (no `NvidiaLLM`) — elimina DIP-1 | `application/services/glossary_build_service.py` | DIP-1 | Unit tests |
| 3.9 | `GlossaryBuildService` usa `_calculate_batch_size()` sin acceder a `_settings.llm.nvidia` — elimina OCP-5 | Ídem | OCP-5 | Unit tests |
| 3.10 | Eliminar clase `GlossaryAwareTranslator` duplicada en `cli/commands/translate_chapter.py` — usar `application/services/translation_service.py` | `cli/commands/translate_chapter.py` | DUP-1, LSP-2 | Tests de integración |

**Criterio de salida**:
- 5 application services creados con DI
- `GlossaryManager` puede ser deprecado (nuevo `GlossaryBuildService` lo reemplaza)
- `tools/Translator.py` puede ser deprecado
- DIP-1 resuelto (GlossaryManager ya no depende de NvidiaLLM)
- OCP-5 resuelto

### Fase 4: Presentation Layer — Adaptar CLI y Backend (Semana 6-8)

**Objetivo**: CLI y Backend usan Application Services en vez de acceder directamente a repos/infraestructura.

| # | Tarea | Archivos | Principio | Tests |
|---|-------|----------|-----------|-------|
| 4.1 | Refactor `cli/commands/translate_chapter.py` — usar `TranslationService`, eliminar funciones duplicadas, usar `cli/ui/selection.py` y `cli/ui/display.py` | `cli/commands/translate_chapter.py` | SRP-2, DUP-4 | Integration tests |
| 4.2 | Refactor `cli/commands/process.py` — usar `TranslationService`, `AudioService`, `DocumentService` inyectados | `cli/commands/process.py` | SRP-6, OCP-1 | Integration tests |
| 4.3 | Refactor `cli/commands/build_glossary.py` — usar `GlossaryBuildService` | `cli/commands/build_glossary.py` | — | Integration tests |
| 4.4 | Refactor `cli/commands/generate_audio.py` — usar `AudioService` con `AudioSynthesizer` inyectado | `cli/commands/generate_audio.py` | — | Integration tests |
| 4.5 | Refactor `cli/commands/add_to_database.py` — usar `DocumentService` | `cli/commands/add_to_database.py` | — | Integration tests |
| 4.6 | Refactor `backend/api/routes/works.py` — eliminar N+1 con query de agregación | `backend/api/routes/works.py` | SRP-4, N+1-1 | API tests |
| 4.7 | Refactor `backend/api/routes/` — usar Application Services en vez de repos directos | Todas las routes | DIP-4 | API tests |
| 4.8 | Refactor `backend/services/file_service.py` — usar `FileUploadService` | `backend/services/file_service.py` | SRP-5, DIP-7 | Tests existentes |
| 4.9 | Eliminar funciones duplicadas en CLI commands — usar `cli/ui/selection.py` y `cli/ui/display.py` | Múltiples commands | DUP-4 | — |

**Criterio de salida**:
- CLI commands no instancian repos directamente
- Backend routes no instancian repos directamente (usan DI FastAPI)
- N+1 query resuelto
- DUP-4 resuelto
- Tests de integración CLI pasan

### Fase 5: Limpieza y Eliminación de Legacy (Semana 8-10)

**Objetivo**: Eliminar código legacy/muerto, consolidar modelos, deduplicar schema SQL.

| # | Tarea | Archivos | Principio | Tests |
|---|-------|----------|-----------|-------|
| 5.1 | Eliminar `tools/Translator.py` (legacy) | ELIMINAR | DUP-1 | Verificar 0 imports |
| 5.2 | Eliminar `tools/TextExtractor.py` (legacy) | ELIMINAR | — | Verificar 0 imports |
| 5.3 | Eliminar `services/translator.py` (reemplazado por application) | MOVER/ELIMINAR | — | — |
| 5.4 | Eliminar `services/glossary_translator.py` (reemplazado por application) | ELIMINAR | DUP-1 | — |
| 5.5 | Eliminar `database/models.py` (bridge) — todos los modelos ahora en `domain/models/` | ELIMINAR | DUP-2, DUP-3 | — |
| 5.6 | Eliminar `database/services/glossary_manager.py` (reemplazado por application) | ELIMINAR | SRP-1 | — |
| 5.7 | Eliminar `database/services/vector_store.py` (reemplazado por infrastructure/embedding/) | ELIMINAR | OCP-3 | — |
| 5.8 | Eliminar `database/services/entity_extractor.py` — mover a `domain/services/` o `application/` | MOVER | — | — |
| 5.9 | Eliminar `core/models/` — todo en `domain/models/` | ELIMINAR | — | — |
| 5.10 | Eliminar `core/exceptions/` — todo en `domain/exceptions/` | ELIMINAR | DIP-5 | — |
| 5.11 | Eliminar `infrastructure/llm/protocol.py` — en `domain/protocols/` | ELIMINAR | — | — |
| 5.12 | Deduplicar schema SQL: symlink o script de copiado desde `src/` a `Docker/` | DUP-6 | — | — |
| 5.13 | Eliminar `BookRepository.find_all()` (duplicado de `get_all()`) | DUP-5 | — | — |
| 5.14 | Repositories: usar named columns en `_row_to_*` en vez de index posicional | Todos los repos | FRG-1 | Tests existentes |
| 5.15 | `VolumeRepository.create/update` incluir glossary columns en RETURNING | MOD-2 | — | Tests |
| 5.16 | `GlossaryRepository._row_to_glossary_entry` mapear `notes` | MOD-3 | — | Tests |

**Criterio de salida**:
- 0 imports a módulos eliminados (verificar con `grep`)
- Código legacy eliminado
- Todos los tests pasan
- Coverage >= baseline

### Fase 6: Módulo TTS Opcional (Semana 10-11)

**Objetivo**: Implementar soporte opcional para TTS local con MLX-Audio / Fish Speech.

| # | Tarea | Archivos | Principio | Tests |
|---|-------|----------|-----------|-------|
| 6.1 | Añadir `[tts]` optional dependency group en `pyproject.toml` | `pyproject.toml` | OCP | — |
| 6.2 | Crear `infrastructure/audio/mlx_audio_synthesizer.py` — implementa `AudioSynthesizer` usando MLX-Audio (Apple Silicon) | NUEVO | OCP-4 | Unit tests |
| 6.3 | Crear `infrastructure/audio/fish_speech_synthesizer.py` — implementa `AudioSynthesizer` usando Fish Speech | NUEVO | OCP-4 | Unit tests |
| 6.4 | Añadir feature flag `tts.engine` en `Settings` (valores: `mac_say`, `mlx_audio`, `fish_speech`) | `core/config/` | OCP | — |
| 6.5 | Crear `AudioSynthesizerFactory` — selecciona implementación según config | `infrastructure/audio/` | OCP, DIP | Tests |
| 6.6 | Mover lógica de normalización de texto a `domain/services/text_normalizer.py` (compartida) | NUEVO | SRP-7 | Unit tests |
| 6.7 | Adaptar `AudioService` para usar `AudioSynthesizerFactory` | `application/services/` | DIP | Tests |
| 6.8 | CLI: `generate-audio` acepta `--engine` flag | `cli/commands/` | OCP | Integration test |
| 6.9 | Backend: endpoint `/api/settings` muestra engine TTS configurable | `backend/api/routes/` | OCP | API test |
| 6.10 | Documentar setup de MLX-Audio y Fish Speech en README | `README.md` | — | — |

**Criterio de salida**:
- `mac_say` funciona como antes (default)
- `mlx_audio` funciona si está instalado (feature flag)
- `fish_speech` funciona si está instalado (feature flag)
- Si engine no disponible → fallback a `mac_say` con warning
- Zero impacto en flujo principal si no habilitado

### Fase 7: Validación Final (Semana 11-12)

**Objetivo**: Verificar que el comportamiento externo no cambió y la calidad interna mejoró.

| # | Tarea | Archivos | Principio | Tests |
|---|-------|----------|-----------|-------|
| 7.1 | Ejecutar full test suite — comparar con baseline | — | Seguridad | 100% pass |
| 7.2 | Medir coverage — comparar con baseline | — | Métrica | >= baseline |
| 7.3 | Medir complejidad ciclomática — comparar con baseline | — | Métrica | Reducida |
| 7.4 | Verificar 0 imports circulares | — | Arquitectura | `python -c "import pdftranslator"` |
| 7.5 | Verificar SOLID compliance — audit manual | — | SOLID | Checklist |
| 7.6 | Verificar behavior parity CLI — smoke tests manuales | — | Seguridad | — |
| 7.7 | Verificar behavior parity API — smoke tests con httpx | — | Seguridad | — |
| 7.8 | Actualizar `AGENTS.md` con nueva estructura | `AGENTS.md` | Documentación | — |
| 7.9 | Actualizar `pyproject.toml` con nueva estructura de packages | `pyproject.toml` | Build | — |
| 7.10 | Tag final `refactor-solid-complete` | — | Seguridad | — |

---

## 5. VALIDACIÓN Y TESTING

### 5.1 Estrategia de Testing por Fase

| Fase | Tests Unitarios | Tests de Integración | Tests E2E |
|------|----------------|---------------------|-----------|
| Fase 0 | — | Baseline registro | — |
| Fase 1 | Protocol compliance tests | Tests existentes sin cambios | — |
| Fase 2 | Implementation compliance tests | Tests de DI con mock pool | — |
| Fase 3 | Application service unit tests | Pipeline integration tests | — |
| Fase 4 | — | CLI command integration | API endpoint tests |
| Fase 5 | — | Full test suite | — |
| Fase 6 | TTS synthesizer unit tests | Audio generation integration | — |
| Fase 7 | — | Full regression | Smoke tests |

### 5.2 Métricas de Control

| Métrica | Baseline (actual) | Target | Herramienta |
|---------|-------------------|--------|-------------|
| Coverage | ~40-50% (estimado) | >= 60% | pytest-cov |
| Complejidad ciclomática | No medida | < 10 por función | ruff C901 |
| Imports circulares | Presentes (DIP-5, DIP-6) | 0 | python import |
| Protocol compliance | N/A | 100% | isinstance checks |
| Líneas en GlossaryManager | 719 | < 200 por servicio | wc -l |
| Líneas en translate_chapter | 804 | < 300 | wc -l |
| N+1 queries | 1 en works | 0 | Manual/API test |
| Código legacy | 3 archivos | 0 | grep imports |

### 5.3 Validaciones Automáticas por Checkpoint

Después de cada fase, ejecutar:

```bash
# 1. Tests pasan
pytest --tb=short -q

# 2. Coverage no regresa
pytest --cov=src/pdftranslator --cov-report=term-missing | tail -1

# 3. No imports circulares
python -c "import pdftranslator"

# 4. Ruff lint
ruff check src/

# 5. Type check (si está configurado)
mypy src/ --ignore-missing-imports
```

---

## 6. ROLLBACK

### 6.1 Punto de Restauración

```bash
# Crear tag de seguridad antes de iniciar
git tag -a refactor-safe-point -m "Estado estable pre-refactorización SOLID"
git push origin refactor-safe-point
```

### 6.2 Procedimiento de Rollback por Fase

| Fase | Rollback | Comando |
|------|----------|---------|
| Cualquiera | Revert a tag de inicio de fase | `git checkout refactor-safe-point -- .` |
| Fase 1 | Los re-exports mantienen compatibilidad → solo eliminar `domain/` | `git revert HEAD~N` |
| Fase 2 | Las implementaciones nuevas son aditivas → eliminar archivos nuevos | `git revert HEAD~N` |
| Fase 3 | Application services son aditivos → eliminar | `git revert HEAD~N` |
| Fase 4 | **Riesgo mayor** — cambios en CLI y backend | Revert + re-test completo |
| Fase 5 | **Irreversible** — código eliminado | `git checkout refactor-safe-point` |
| Fase 6 | Módulo opcional → simplemente no usar | Feature flag off |

### 6.3 Criterios para Abortar la Refactorización

| Criterio | Umbral | Acción |
|----------|--------|--------|
| Tests fallan > 3 veces seguidas en una fase | — | Abortar fase, rollback |
| Coverage regresa > 5% del baseline | — | Investigar antes de continuar |
| Comportamiento funcional cambia (smoke test falla) | — | Abortar fase, rollback |
| Tiempo de fase excede 2x estimación | — | Re-evaluar enfoque |
| Nuevo import circular detectado | — | Corregir antes de continuar |

### 6.4 Estrategia: Refactorización Incremental

- **NUNCA** modificar más de 3 módulos por PR
- **SIEMPRE** tener tests pasando antes de commit
- **SIEMPRE** crear branch por fase: `refactor/solid-phase-N`
- **SIEMPRE** squash-merge a main solo cuando fase completa pasa validación
- **NUNCA** eliminar código legacy hasta Fase 5 (cuando 0 consumidores)

---

## 7. EXTENSIÓN TTS OPCIONAL

### 7.1 Arquitectura Plugin/Adapter

```
domain/protocols/audio_synthesizer.py
    └── AudioSynthesizer (Protocol)
            ├── MacSaySynthesizer     (default, macOS only)
            ├── MlxAudioSynthesizer   (optional, Apple Silicon)
            └── FishSpeechSynthesizer (optional, CUDA/MPS)
```

### 7.2 AudioSynthesizer Protocol

```python
from pathlib import Path
from typing import Protocol

class AudioSynthesizer(Protocol):
    """Abstracción para síntesis de texto a audio."""

    def synthesize(
        self,
        text: str,
        output_path: Path,
        voice: str = "default",
        speed: float = 1.0,
        language: str = "es",
    ) -> bool:
        """Sintetizar texto a audio. Retorna True si exitoso."""
        ...

    def merge_audio(
        self,
        audio_files: list[Path],
        output_path: Path,
    ) -> bool:
        """Merge múltiples archivos de audio en uno."""
        ...

    @property
    def is_available(self) -> bool:
        """Verificar si el engine está disponible en este sistema."""
        ...

    @property
    def name(self) -> str:
        """Nombre del engine (para logging y config)."""
        ...
```

### 7.3 MLX-Audio Synthesizer (Apple Silicon)

```python
# infrastructure/audio/mlx_audio_synthesizer.py
class MlxAudioSynthesizer:
    """TTS usando MLX-Audio — optimizado para Apple Silicon."""

    def __init__(self, model: str = "mlx-community/Kokoro-82M-bf16"):
        self._model_name = model
        self._model = None  # Lazy load

    @property
    def is_available(self) -> bool:
        try:
            import mlx_audio  # noqa: F401
            import mlx.core as mx
            return mx.metal.is_available()
        except ImportError:
            return False

    @property
    def name(self) -> str:
        return "mlx_audio"

    def synthesize(self, text: str, output_path: Path, voice: str = "af_heart",
                    speed: float = 1.0, language: str = "a") -> bool:
        from mlx_audio.tts.utils import load_model
        from mlx_audio.audio_io import write as audio_write
        import numpy as np

        if self._model is None:
            self._model = load_model(self._model_name)

        for result in self._model.generate(text=text, voice=voice, speed=speed, lang_code=language):
            audio_write(str(output_path), np.array(result.audio), result.sample_rate)
            return True
        return False

    def merge_audio(self, audio_files: list[Path], output_path: Path) -> bool:
        # Delegar a ffmpeg_merger (compartido)
        from pdftranslator.infrastructure.audio.ffmpeg_merger import merge_audio_files
        return merge_audio_files(audio_files, output_path)
```

### 7.4 Fish Speech Synthesizer

```python
# infrastructure/audio/fish_speech_synthesizer.py
class FishSpeechSynthesizer:
    """TTS usando Fish Speech — soporta CUDA y MPS."""

    def __init__(self, llama_checkpoint: str, decoder_checkpoint: str, device: str = "auto"):
        self._llama_checkpoint = llama_checkpoint
        self._decoder_checkpoint = decoder_checkpoint
        self._device = self._resolve_device(device)
        self._engine = None  # Lazy load

    @property
    def is_available(self) -> bool:
        try:
            import fish_speech  # noqa: F401
            import torch
            return torch.cuda.is_available() or hasattr(torch.backends, "mps")
        except ImportError:
            return False

    @staticmethod
    def _resolve_device(device: str) -> str:
        import torch
        if device == "auto":
            if torch.cuda.is_available():
                return "cuda"
            elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                return "mps"
            return "cpu"
        return device
```

### 7.5 Feature Flag Configuration

```python
# En core/config/processing.py (o nuevo core/config/tts.py)
class TTSConfig(BaseModel):
    engine: Literal["mac_say", "mlx_audio", "fish_speech"] = Field(default="mac_say")
    mlx_model: str = Field(default="mlx-community/Kokoro-82M-bf16")
    mlx_voice: str = Field(default="af_heart")
    fish_llama_checkpoint: str = Field(default="checkpoints/openaudio-s1-mini")
    fish_decoder_checkpoint: str = Field(default="checkpoints/openaudio-s1-mini/codec.pth")
    fish_device: Literal["auto", "cuda", "mps", "cpu"] = Field(default="auto")
```

### 7.6 AudioSynthesizerFactory

```python
# infrastructure/audio/factory.py
class AudioSynthesizerFactory:
    def __init__(self, config: TTSConfig):
        self._config = config

    def create(self) -> AudioSynthesizer:
        engine = self._config.engine
        if engine == "mlx_audio":
            synth = MlxAudioSynthesizer(model=self._config.mlx_model)
            if synth.is_available:
                return synth
            logger.warning("MLX-Audio not available, falling back to mac_say")

        elif engine == "fish_speech":
            synth = FishSpeechSynthesizer(
                llama_checkpoint=self._config.fish_llama_checkpoint,
                decoder_checkpoint=self._config.fish_decoder_checkpoint,
                device=self._config.fish_device,
            )
            if synth.is_available:
                return synth
            logger.warning("Fish Speech not available, falling back to mac_say")

        return MacSaySynthesizer()  # Default fallback
```

### 7.7 Dependencias Opcionales

```toml
# pyproject.toml
[project.optional-dependencies]
tts-mlx = [
    "mlx-audio>=0.1.0",
    "mlx>=0.20.0",
]
tts-fish = [
    "fish-speech>=1.5.0",
    "torch>=2.2.0",
]
tts-all = [
    "pdftranslator[tts-mlx,tts-fish]",
]
```

---

## 8. CONCLUSIÓN TÉCNICA

### 8.1 Resumen de Violaciones → Soluciones

| Violación | Fase | Solución |
|-----------|------|----------|
| SRP-1: GlossaryManager monolítico | 3 | Descomponer en `GlossaryBuildService` con steps inyectables |
| SRP-2: translate_chapter.py monolítico | 4 | Usar `TranslationService`, mover UI a `cli/ui/` |
| SRP-4: N+1 en works API | 4 | Query de agregación o batch loading |
| SRP-5: FileService monolítico | 3 | Descomponer en `FileUploadService` con DI |
| SRP-7: AudioGenerator acoplado | 2,6 | Separar en `AudioSynthesizer` Protocol + implementaciones |
| OCP-1: Translator.py if/elif | 4 | Eliminar, usar `LLMFactory` |
| OCP-2: GlossaryManager hardcodea NvidiaLLM | 3 | Inyectar `LLMClient` |
| OCP-3: VectorStoreService hardcodea NVIDIA | 2 | Inyectar `EmbeddingProvider`/`RerankingProvider` |
| OCP-4: AudioGenerator hardcodea say/ffmpeg | 2,6 | `AudioSynthesizer` Protocol + Factory |
| OCP-5: Batch size accede a nvidia config | 3 | Pasar max_tokens como parámetro |
| LSP-1: Repos no implementan BaseRepository | 2 | Implementar protocols segregados |
| LSP-2: CLI GlossaryAwareTranslator rompe contrato | 3,4 | Eliminar, usar `TranslationService` |
| LSP-3: SubstitutionRuleRepository firma diferente | 1 | Interface segregada |
| ISP-1: LLMClient Protocol demasiado grande | 1 | Segregar en TextGenerator/TokenCounter/TextSplitter |
| ISP-2: BaseRepository exige CRUD completo | 1 | Segregar en ReadRepository/WriteRepository |
| ISP-3: VectorStoreService expone todo | 1 | Segregar EmbeddingProvider/RerankingProvider |
| DIP-1: GlossaryManager → NvidiaLLM | 3 | Inyectar `LLMClient` |
| DIP-2: VectorStoreService → NVIDIAEmbeddings | 2 | Inyectar `EmbeddingProvider` |
| DIP-3: Repos → DatabasePool.get_instance() | 2 | Inyectar ConnectionPool |
| DIP-4: CLI instancía repos directamente | 4 | Usar Application Services |
| DIP-5: core/exceptions → database.exceptions | 1 | Mover exceptions a domain |
| DIP-6: services → cli/services | 1,11 | Mover GlossaryPostProcessor a domain |
| DIP-7: FileService → TextExtractor | 3 | Inyectar `DocumentParser` |

### 8.2 Riesgos y Mitigaciones

| Riesgo | Probabilidad | Mitigación |
|--------|-------------|------------|
| Tests existentes insuficientes para detectar regresiones | Alta | Añadir tests de integración antes de cada fase |
| Coexistencia de código viejo/nuevo genera confusión | Media | Re-exports claros, deprecation warnings |
| Fase 5 (eliminación) rompe algo inesperado | Media | grep exhaustivo de imports antes de eliminar |
| MLX-Audio / Fish Speech no funcionan en el entorno | Media | Feature flag + fallback a mac_say |
| Complejidad del plan excede timeline | Baja | Cada fase es independiente y pausable |

### 8.3 Checklist Final de Verificación

- [ ] Tag `refactor-safe-point` creado
- [ ] Todos los tests pasan (baseline)
- [ ] Coverage >= baseline
- [ ] 0 imports circulares
- [ ] 0 imports a módulos eliminados
- [ ] Domain layer NO importa infrastructure
- [ ] Application layer NO importa infrastructure directamente
- [ ] Presentation layer USA application services
- [ ] Infrastructure IMPLEMENTA domain protocols
- [ ] Todos los protocols tienen compliance tests
- [ ] `GlossaryManager` eliminado (reemplazado por `GlossaryBuildService`)
- [ ] `tools/Translator.py` eliminado
- [ ] N+1 query resuelto
- [ ] Feature flag TTS funciona
- [ ] `AGENTS.md` actualizado
- [ ] Documentación completa (antes/después)
- [ ] Tag `refactor-solid-complete` creado

### 8.4 Principios SOLID — Verificación Final

| Principio | Verificación |
|-----------|-------------|
| **S** — Single Responsibility | Cada clase < 200 líneas, 1 razón para cambiar |
| **O** — Open/Closed | Nuevo LLM/embedding/TTS engine = nueva clase, 0 cambios en existentes |
| **L** — Liskov Substitution | Cualquier `AudioSynthesizer` puede reemplazar a otro; cualquier `LLMClient` a otro |
| **I** — Interface Segregation | Consumer solo depende del protocol que usa (ej: `TextGenerator` no exige `count_tokens`) |
| **D** — Dependency Inversion | Application depende de abstracciones (protocols), no de implementaciones |
