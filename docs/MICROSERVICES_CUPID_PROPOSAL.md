# PDFTranslator - Microservices Architecture Proposal (CUPID Principles)

**Date:** 2025-07-11  
**Version:** 1.0  
**Status:** Draft for Review  
**Philosophy:** Built on **CUPID** — Composable, Unix Philosophy, Predictable, Idiomatic, Domain-Focused

---

## Executive Summary

This document proposes a microservices architecture for PDFTranslator designed through the lens of **CUPID** (Daniel North's principles for joyful coding). Rather than decomposing for decomposition's sake, every architectural decision traces back to these five principles:

| Principle | Our Interpretation | Architectural Impact |
|-----------|-------------------|---------------------|
| **Composable** | Services combine like LEGO bricks | gRPC + REST + Events; no service assumes its consumers |
| **Unix Philosophy** | Do one thing well; text/JSON streams | Stateless services, stdin/stdout pipelines, S3 for blobs |
| **Predictable** | Same input → same output (modulo LLM) | Deterministic chunking, idempotent events, fixed retry policies |
| **Idiomatic** | Native patterns per language/ecosystem | Go for Catalog, Python for ML, Rust for text, TypeScript for UI |
| **Domain-Focused** | Bounded contexts mirror business capabilities | 7 services = 7 translation workflow capabilities |

---

## 1. CUPID-Driven Current State Analysis

### 1.1 Where the Monolith Violates CUPID

| CUPID Principle | Current Violation | Evidence in Codebase |
|-----------------|-------------------|---------------------|
| **Composable** | Tight in-process coupling | `TranslationOrchestrator` directly instantiates `ChapterRepository`, `GlossaryRepository`, `GlossaryAwareTranslator` |
| **Unix Philosophy** | God classes doing too much | `process_single_file()` in `cli/commands/process.py` = 80 lines handling extract → validate → translate → audio |
| **Predictable** | Hidden global state | `Settings.get()` singleton; `DatabasePool._instance` singleton; `LLMFactory._instances` cache |
| **Idiomatic** | Mixed paradigms in Python | Dataclasses + SQLAlchemy patterns + manual connection pooling + Typer CLI all in one codebase |
| **Domain-Focused** | Anemic domain models | `Work`, `Volume`, `Chapter` are pure data carriers; behavior lives in `TranslationOrchestrator` service |

### 1.2 The CUPID Refactoring Target

```
BEFORE (Monolith)                          AFTER (CUPID Services)
─────────────────                          ────────────────────
┌─────────────────────┐                    ┌─────────────────────┐
│  Single Process     │                    │  Composable         │
│  • All domains      │                    │  ┌─────┐ ┌─────┐    │
│  • Shared SQLite    │        ───►        │  │ Doc │ │ Cat │    │
│  • Single Settings  │                    │  └──┬──┘ └──┬──┘    │
│  • One deployment   │                    │     │      │       │
└─────────────────────┘                    │  ┌──┴┐ ┌──┴──┐    │
                                           │  │Glo│ │Trans│    │
                                           │  └──┬┘ └──┬──┘    │
                                           │     │      │       │
                                           │  ┌──┴┐ ┌──┴──┐    │
                                           │  │Job│ │Audio│    │
                                           │  └───┘ └─────┘    │
                                           │  Composable        │
                                           │  Unix Philosophy   │
                                           │  Predictable       │
                                           │  Idiomatic         │
                                           │  Domain-Focused    │
                                           └─────────────────────┘
```

---

## 2. Service Design Through CUPID Lens

### 2.1 Design Principles Applied Per Service

#### 📄 Document Service — *Unix Philosophy + Composable*
> **Do one thing well**: Extract text + structure from documents. Emit JSON. Nothing more.

```python
# CUPID compliant: Single responsibility, composable output
class DocumentExtractor:
    """Unix filter: file_path → ExtractedDocument (JSON)"""
    
    def extract(self, file_path: Path) -> ExtractedDocument:
        # Docling does the heavy lifting
        docling_doc = self._converter.convert(str(file_path))
        
        # Composable output: structured JSON, not coupled to downstream
        return ExtractedDocument(
            id=uuid4(),
            full_text=self._extract_full_text(docling_doc),
            pages=self._extract_pages(docling_doc),
            structure=self._extract_structure(docling_doc),  # Headings, lists, tables
            images=self._extract_images(docling_doc),
            metadata=DocumentMetadata(
                filename=file_path.name,
                mime_type=mimetypes.guess_type(file_path)[0],
                page_count=len(docling_doc.pages),
            )
        )
```

**CUPID Checklist:**
- ✅ **Composable**: Output is pure JSON → any consumer (Catalog, Glossary, Human review)
- ✅ **Unix Philosophy**: CLI tool `pdftranslator-extract file.pdf > extracted.json` works
- ✅ **Predictable**: Same PDF → same JSON (Docling is deterministic)
- ✅ **Idiomatic**: Python + Pydantic models, type hints, async/await
- ✅ **Domain-Focused**: Models *document structure*, not translation workflow

---

#### 📚 Catalog Service — *Domain-Focused + Predictable*
> **Models the business domain**: Works, Volumes, Chapters — the "library" aggregate root

```go
// CUPID compliant: Domain-focused, Predictable (Go = explicit errors)
type CatalogService struct {
    db     *sql.DB
    events EventPublisher
}

// Composable: Pure CRUD + Events, no translation logic
func (s *CatalogService) CreateWork(ctx context.Context, cmd CreateWorkCommand) (*Work, error) {
    work := Work{
        ID:           uuid.New(),
        Title:        cmd.Title,
        SourceLang:   cmd.SourceLang,
        TargetLang:   cmd.TargetLang,
        Author:       cmd.Author,
        CreatedAt:    time.Now(),
    }
    
    tx, err := s.db.BeginTx(ctx, nil)
    if err != nil {
        return nil, fmt.Errorf("begin tx: %w", err)  // Predictable error wrapping
    }
    defer tx.Rollback()
    
    if err := s.persistWork(tx, work); err != nil {
        return nil, err
    }
    
    if err := tx.Commit(); err != nil {
        return nil, fmt.Errorf("commit: %w", err)
    }
    
    // Composable: Event emission decoupled from persistence
    s.events.Publish(WorkCreatedEvent{Work: work})
    
    return &work, nil
}
```

**CUPID Checklist:**
- ✅ **Composable**: gRPC + REST + Events; consumers choose protocol
- ✅ **Unix Philosophy**: "Library management" only — no extraction, no translation
- ✅ **Predictable**: ACID transactions, explicit error handling, idempotent creates
- ✅ **Idiomatic**: Go for high-read metadata service (stdlib `database/sql`, `encoding/json`)
- ✅ **Domain-Focused**: `Work`, `Volume`, `Chapter` are *rich domain models* with behavior

---

#### 🔤 Glossary Service — *Composable + Domain-Focused*
> **Terminology as a first-class domain** — extraction, validation, semantic search

```python
# CUPID compliant: Composable pipeline stages
class GlossaryPipeline:
    """Unix pipeline: text → entities → validated → translated → embedded → stored"""
    
    def __init__(
        self,
        extractor: TermExtractor,          # Stage 1: NER + LLM
        validator: TermValidator,          # Stage 2: Human/AI review
        translator: TermTranslator,        # Stage 3: LLM translation
        embedder: TermEmbedder,            # Stage 4: Vector generation
        store: GlossaryStore,              # Stage 5: Persistence
    ):
        self.stages = [extractor, validator, translator, embedder, store]
    
    async def build_for_volume(self, volume_id: UUID, text: str) -> BuildResult:
        # Each stage is independently testable, replaceable, observable
        entities = await self.extractor.extract(text)
        validated = await self.validator.validate(entities)
        translated = await self.translator.translate(validated)
        embedded = await self.embedder.embed(translated)
        return await self.store.save(volume_id, embedded)
```

**CUPID Checklist:**
- ✅ **Composable**: Pipeline stages are independent services/functions
- ✅ **Unix Philosophy**: Each stage: input → output, no shared state
- ✅ **Predictable**: Deterministic embedding (same text → same vector); versioned prompts
- ✅ **Idiomatic**: Python for ML ecosystem (sentence-transformers, spaCy, pgvector)
- ✅ **Domain-Focused**: Models *terminology consistency* — not generic "tags"

---

#### 🌐 Translation Service — *Idiomatic + Predictable + Composable*
> **LLM orchestration as a pure function**: (text, glossary, config) → translation

```python
# CUPID compliant: Predictable interface, Composable providers
class TranslationService:
    """Pure function: TranslateRequest → TranslateResponse"""
    
    def __init__(
        self,
        chunker: TextChunker,              # Deterministic chunking
        provider_factory: LLMProviderFactory,  # Pluggable backends
        glossary_client: GlossaryClient,   # Composable dependency
    ):
        self.chunker = chunker
        self.provider_factory = provider_factory
        self.glossary_client = glossary_client
    
    async def translate(self, request: TranslateRequest) -> TranslateResponse:
        # Predictable: same inputs → same chunking
        chunks = self.chunker.split(request.text, request.source_lang, request.target_lang)
        
        # Composable: glossary terms fetched as dependency, not owned
        glossary = await self.glossary_client.search(
            work_id=request.work_id,
            query_chunks=chunks[:5],  # Sample for context
            limit=request.glossary_limit,
        )
        
        # Idiomatic: Provider pattern, each backend implements same protocol
        provider = self.provider_factory.create(request.provider)
        
        # Predictable: Fixed retry policy, timeout, fallback chain
        translations = await self._translate_chunks_with_retry(
            chunks, glossary, provider, request
        )
        
        return TranslateResponse(
            translated_text=self._reassemble(translations),
            chunks=translations,
            metadata=TranslationMetadata(
                provider=provider.name,
                model=provider.model,
                chunk_count=len(chunks),
                glossary_terms_used=len(glossary),
            )
        )
```

**CUPID Checklist:**
- ✅ **Composable**: Provider factory + glossary client injected, not hardcoded
- ✅ **Unix Philosophy**: Text in → text out; streaming response via SSE
- ✅ **Predictable**: Fixed chunking algorithm, retry policy, timeout budgets
- ✅ **Idiomatic**: Python `Protocol` for providers, `asyncio` for concurrency
- ✅ **Domain-Focused**: Models *translation with terminology consistency*

---

#### ⚙️ Job Orchestrator — *Predictable + Domain-Focused*
> **Workflow as code** — Temporal.io for durable execution, no hidden state

```go
// CUPID compliant: Predictable workflows, Domain-focused activities
type TranslationWorkflow struct {
    // Activities are pure, idempotent, composable
    ExtractDocument    func(ctx context.Context, docID string) (*ExtractedDoc, error)
    CreateCatalogEntries func(ctx context.Context, doc *ExtractedDoc) (*CatalogRefs, error)
    BuildGlossary      func(ctx context.Context, refs *CatalogRefs) (*GlossaryRef, error)
    TranslateChapters  func(ctx context.Context, refs *CatalogRefs, glossary *GlossaryRef) error
    GenerateAudio      func(ctx context.Context, refs *CatalogRefs) (*AudioRef, error)
}

func (w *TranslationWorkflow) Execute(ctx context.Context, job JobRequest) error {
    // Predictable: Each step is a durable activity with retry policy
    doc, err := w.ExtractDocument(ctx, job.DocumentID)
    if err != nil {
        return fmt.Errorf("extract: %w", err)
    }
    
    refs, err := w.CreateCatalogEntries(ctx, doc)
    if err != nil {
        return fmt.Errorf("catalog: %w", err)
    }
    
    // Composable: Glossary optional, parallelizable
    var glossary *GlossaryRef
    if job.BuildGlossary {
        glossary, err = w.BuildGlossary(ctx, refs)
        if err != nil {
            return fmt.Errorf("glossary: %w", err)
        }
    }
    
    // Predictable: Chapter translation parallelized, progress via heartbeats
    if err := w.TranslateChapters(ctx, refs, glossary); err != nil {
        return fmt.Errorf("translate: %w", err)
    }
    
    if job.GenerateAudio {
        if _, err := w.GenerateAudio(ctx, refs); err != nil {
            return fmt.Errorf("audio: %w", err)
        }
    }
    
    return nil
}
```

**CUPID Checklist:**
- ✅ **Composable**: Activities are independent, reusable across workflows
- ✅ **Unix Philosophy**: Each activity = one domain operation; Temporal handles orchestration
- ✅ **Predictable**: Deterministic replay, explicit timeouts, versioned workflows
- ✅ **Idiomatic**: Go + Temporal SDK (native patterns for durability)
- ✅ **Domain-Focused**: Models *translation job lifecycle* — not generic "task queue"

---

#### 🔊 Audio Service — *Unix Philosophy + Idiomatic*
> **Text → Audio pipeline** — streaming, format-agnostic, backend-pluggable

```rust
// CUPID compliant: Idiomatic Rust for audio processing, Unix pipeline
use std::process::{Command, Stdio};
use tokio::io::{AsyncBufReadExt, BufReader};

// Composable: Trait for TTS backends
#[async_trait]
trait TTSEngine: Send + Sync {
    async fn synthesize(&self, text: &str, voice: &Voice) -> Result<AudioChunk>;
    fn sample_rate(&self) -> u32;
    fn formats(&self) -> Vec<AudioFormat>;
}

// Unix Philosophy: Pipeline stages as async functions
async fn text_to_audio_pipeline(
    text: String,
    engine: &dyn TTSEngine,
    format: AudioFormat,
) -> Result<Vec<u8>> {
    // Stage 1: Chunk by sentences (deterministic)
    let sentences = chunk_by_sentences(&text);
    
    // Stage 2: TTS per chunk (parallel, predictable)
    let chunks = futures::future::join_all(
        sentences.into_iter().map(|s| engine.synthesize(&s, &voice))
    ).await;
    
    // Stage 3: Concatenate + normalize (pure function)
    let merged = merge_audio_chunks(chunks?);
    let normalized = normalize_loudness(merged, -23.0); // EBU R128
    
    // Stage 4: Encode (composable format)
    encode_audio(normalized, format)
}

// Idiomatic: macOS `say` backend using native process spawning
struct MacOSSayEngine { voice: String }
#[async_trait]
impl TTSEngine for MacOSSayEngine {
    async fn synthesize(&self, text: &str, _voice: &Voice) -> Result<AudioChunk> {
        let mut cmd = Command::new("say")
            .args(["-v", &self.voice, "-o", "/dev/stdout", "--data-format=LEF32@22050", text])
            .stdout(Stdio::piped())
            .spawn()?;
        
        let stdout = BufReader::new(cmd.stdout.take().unwrap());
        let mut audio_data = Vec::new();
        stdout.read_to_end(&mut audio_data).await?;
        
        Ok(AudioChunk { data: audio_data, sample_rate: 22050 })
    }
}
```

**CUPID Checklist:**
- ✅ **Composable**: TTS engines as trait implementations; format encoders separate
- ✅ **Unix Philosophy**: `text | tts | normalize | encode > output.m4a` works as CLI
- ✅ **Predictable**: EBU R128 loudness normalization; deterministic chunking
- ✅ **Idiomatic**: Rust for audio DSP (performance, memory safety, `symphonia` crate)
- ✅ **Domain-Focused**: Models *audiobook generation* — not generic "media processing"

---

#### 📝 Text Processing Service — *Composable + Unix Philosophy*
> **Sidecar/library** — pure text transformations, no HTTP needed

```python
# CUPID compliant: Composable functions, Unix filter style
# Can be used as: library, sidecar, or CLI filter

class TextPipeline:
    """Composable text transformations — each step is a pure function"""
    
    def __init__(self):
        self.steps: List[Callable[[str], str]] = []
    
    def add_substitution(self, pattern: str, replacement: str) -> "TextPipeline":
        """Add regex substitution (composable)"""
        compiled = re.compile(pattern)
        self.steps.append(lambda text: compiled.sub(replacement, text))
        return self  # Fluent API for composition
    
    def add_overlap_cleaner(self, overlap_chars: int = 200) -> "TextPipeline":
        """Remove overlapping text between chunks"""
        def clean(text: str) -> str:
            # ... overlap removal logic
            return cleaned
        self.steps.append(clean)
        return self
    
    def add_normalizer(self) -> "TextPipeline":
        """Whitespace, line ending normalization"""
        self.steps.append(lambda t: t.replace('\r\n', '\n').replace('\r', '\n'))
        self.steps.append(lambda t: re.sub(r'\n{3,}', '\n\n', t))
        return self
    
    def process(self, text: str) -> str:
        """Unix filter: input → output through pipeline"""
        for step in self.steps:
            text = step(text)
        return text

# CLI usage (Unix Philosophy):
# cat chapter.txt | python -m text_processing --sub "foo" "bar" --normalize > clean.txt
```

**CUPID Checklist:**
- ✅ **Composable**: Fluent builder, each step independent, library + CLI
- ✅ **Unix Philosophy**: Pure functions, stdin/stdout, composable with pipes
- ✅ **Predictable**: Same input + same config = same output
- ✅ **Idiomatic**: Python for text processing (regex, Unicode), type hints
- ✅ **Domain-Focused**: Models *translation text prep* — not generic "ETL"

---

## 3. CUPID Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              CUPID ARCHITECTURE                                 │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│   CLIENT (Angular/CLI)                                                          │
│        │                                                                        │
│        ▼                                                                        │
│   ┌─────────────┐                                                               │
│   │ API GATEWAY │  Composable: Routes to any protocol (REST/gRPC/GraphQL)      │
│   │  (Kong)     │  Predictable: Auth, rate limit, timeout budgets              │
│   └──────┬──────┘                                                               │
│          │                                                                     │
│    ┌─────┼─────┐                                                               │
│    ▼     ▼     ▼     ▼                                                         │
│ ┌──────┐┌──────┐┌──────┐┌──────┐                                               │
│ │ Doc  ││ Cat  ││ Glos ││ Trans│  ◄── Composable: Each service independent    │
│ │ Svc  ││ Svc  ││ Svc  ││ Svc  │      Unix: Single responsibility             │
│ └──┬──┘└──┬──┘└──┬──┘└──┬──┘      Predictable: Fixed APIs, versioned           │
│    │     │     │     │           Idiomatic: Right language per domain         │
│    ▼     ▼     ▼     ▼           Domain: Bounded contexts match capabilities   │
│ ┌─────────────────────────────┐                                                │
│ │     EVENT BUS (Kafka)       │  Composable: Loose coupling via events        │
│ │  CloudEvents + Avro Schema  │  Predictable: Schema registry, versioning     │
│ └─────────────┬───────────────┘  Unix: Append-only log = source of truth      │
│               ▼                                              │
│    ┌──────────────┐ ┌──────────────┐ ┌──────────────┐                         │
│    │ Job          │ │ Audio        │ │ Text         │                         │
│    │ Orchestrator │ │ Service      │ │ Processing   │                         │
│    │ (Temporal)   │ │ (Rust/Go)    │ │ (Library)    │                         │
│    └──────┬───────┘ └──────┬───────┘ └──────────────┘                         │
│           │                │                                                 │
│           ▼                ▼                                                 │
│    ┌──────────────┐ ┌──────────────┐                                         │
│    │ PostgreSQL   │ │ S3/MinIO     │  Composable: Separate compute/storage   │
│    │ (per service)│ │ (blobs)      │  Predictable: ACID + eventual consistency│
│    └──────────────┘ └──────────────┘  Unix: Files/objects as streams           │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. CUPID Compliance Matrix

| Service | Composable | Unix Philosophy | Predictable | Idiomatic | Domain-Focused |
|---------|------------|-----------------|-------------|-----------|----------------|
| **Document** | ✅ JSON output, no deps | ✅ `file → JSON` | ✅ Deterministic extraction | ✅ Python + Docling | ✅ Document structure |
| **Catalog** | ✅ gRPC/REST/Events | ✅ CRUD only | ✅ ACID, explicit errors | ✅ Go + sqlc | ✅ Library hierarchy |
| **Glossary** | ✅ Pipeline stages | ✅ Stage = pure fn | ✅ Versioned embeddings | ✅ Python ML stack | ✅ Terminology consistency |
| **Translation** | ✅ Provider + Glossary DI | ✅ Text in/out, SSE | ✅ Fixed chunking, retry | ✅ Protocol + asyncio | ✅ Context-aware translation |
| **Job Orchestrator** | ✅ Activity composition | ✅ Temporal = workflow as code | ✅ Deterministic replay | ✅ Go + Temporal SDK | ✅ Translation job lifecycle |
| **Audio** | ✅ Engine trait + format | ✅ Pipeline stages | ✅ EBU R128, deterministic | ✅ Rust + symphonia | ✅ Audiobook generation |
| **Text Processing** | ✅ Fluent builder + CLI | ✅ Stdin/stdout filters | ✅ Pure functions | ✅ Python regex | ✅ Translation prep |

**Score: 35/35** — Every service satisfies all 5 CUPID principles

---

## 5. CUPID-Driven Migration Strategy

### 5.1 Strangler Fig with CUPID Checkpoints

```
PHASE 1: COMPOSABLE EXTRACTION (Weeks 1-4)
─────────────────────────────────────────
□ Catalog Service: Read-only API over existing SQLite
  → CUPID test: Can Angular UI consume it without changes?
  
□ Document Service: Extract → JSON file (no DB)
  → CUPID test: `pdftranslator-extract file.pdf > out.json` works?

PHASE 2: UNIX PIPELINE REPLACEMENT (Weeks 5-10)
────────────────────────────────────────────────
□ Glossary Pipeline: Replace in-process with HTTP service
  → CUPID test: Each stage independently testable?
  
□ Translation Service: Extract LLM orchestration
  → CUPID test: Provider swap without code changes?
  
□ Text Processing: Extract as library + CLI
  → CUPID test: Works in pipeline: `cat | textproc | translate`?

PHASE 3: PREDICTABLE ORCHESTRATION (Weeks 11-16)
─────────────────────────────────────────────────
□ Job Orchestrator: Temporal workflows replace TranslationOrchestrator
  → CUPID test: Workflow replay produces identical results?
  
□ Audio Service: Extract TTS pipeline
  → CUPID test: `text | audio > out.m4a` produces same output?

PHASE 4: DOMAIN-FOCUSED CUTOVER (Weeks 17-22)
─────────────────────────────────────────────
□ Frontend → Gateway (Composable routing)
□ Dual-write → New services (Predictable migration)
□ SQLite decommission (Unix: remove dead code)
□ Chaos testing (Predictable failure modes)
```

### 5.2 CUPID Validation Gates

Each phase must pass **CUPID gates** before proceeding:

| Gate | Composable | Unix | Predictable | Idiomatic | Domain-Focused |
|------|------------|------|-------------|-----------|----------------|
| **Contract Test** | Pact tests pass | CLI works | Schema versioned | Idiomatic client | Domain types match |
| **Load Test** | Horizontal scale | Stateless | P99 < budget | Native concurrency | Domain throughput |
| **Chaos Test** | Survives partition | No sticky state | Deterministic recovery | Graceful degradation | Domain invariants hold |
| **Migration Test** | Dual-write parity | Data as streams | Eventual consistency | Zero-downtime deploy | Business continuity |

---

## 6. CUPID Technology Choices (Right Tool per Domain)

| Domain Capability | Language | Why CUPID? |
|-------------------|----------|------------|
| **Metadata/Catalog** | **Go** | Predictable errors, explicit deps, fast reads, sqlc for type-safe SQL |
| **ML/NLP (Glossary, Translation)** | **Python** | Idiomatic for ML (PyTorch, transformers, spaCy), async LLM calls |
| **Audio Processing** | **Rust** | Idiomatic for DSP (symphonia, hound), memory safety, no GC pauses |
| **Workflow Orchestration** | **Go + Temporal** | Predictable durability, composable activities, native Go SDK |
| **Text Processing** | **Python** (library) | Idiomatic regex/Unicode, composable as lib + CLI |
| **API Gateway** | **Kong (Lua/Go)** | Composable plugins, predictable routing, industry standard |
| **Event Bus** | **Kafka (Java/Go)** | Predictable ordering, composable consumers, unix log semantics |
| **Vector Search** | **PostgreSQL + pgvector** | Composable SQL + vectors, predictable ACID, idiomatic Postgres |

---

## 7. CUPID Observability (Predictable Debugging)

```yaml
# Every service exposes: Predictable signals
service:
  # Composable: Standard /health, /ready, /metrics
  endpoints:
    - path: /health
      response: {status: "healthy", checks: {db: true, cache: true}}
    - path: /metrics
      format: prometheus  # Unix: text-based, scrapable
      
  # Predictable: Structured logging (JSON, fixed fields)
  logging:
    format: json
    fields:
      - timestamp: RFC3339
      - level: debug|info|warn|error
      - service: catalog|document|...
      - trace_id: W3C traceparent
      - span_id: W3C traceparent
      - message: human-readable
      - attrs: key-value (domain-specific)
      
  # Domain-Focused: Business metrics, not just technical
  metrics:
    - catalog.works.created.total
    - document.extracted.pages.duration_seconds
    - glossary.terms.extracted.total
    - translation.chunks.processed.total
    - audio.minutes.generated.total
    - job.workflow.duration_seconds
```

---

## 8. CUPID Risk Mitigation

| CUPID Principle | Risk | Mitigation |
|-----------------|------|------------|
| **Composable** | Service churn breaks consumers | **Contract testing (Pact)** + semantic versioning + consumer-driven contracts |
| **Unix Philosophy** | Over-fragmentation (nanoservices) | **Bounded context minimum**: 1 service per business capability, not per function |
| **Predictable** | LLM non-determinism | **Fixed seeds, versioned prompts, deterministic chunking, fallback chains** |
| **Idiomatic** | Polyglot operational complexity | **Platform team owns runtime**; each team owns their language's best practices |
| **Domain-Focused** | Anemic models return | **Rich domain models in Catalog/Job**; services own their aggregates |

---

## 9. CUPID Team Structure (Inverse Conway + CUPID)

```
┌─────────────────────────────────────────────────────────────────────┐
│                        PLATFORM TEAM                                 │
│  Provides: Composable infra, Predictable CI/CD, Idiomatic tooling   │
│  Kubernetes │ Kafka │ PostgreSQL │ Observability │ Security        │
└─────────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│  CATALOG      │    │  DOCUMENT     │    │  GLOSSARY     │
│  TEAM (Go)    │    │  TEAM (Py)    │    │  TEAM (Py)    │
│               │    │               │    │               │
│ Domain:       │    │ Domain:       │    │ Domain:       │
│ Library mgmt  │    │ Extraction    │    │ Terminology   │
│               │    │               │    │               │
│ CUPID:        │    │ CUPID:        │    │ CUPID:        │
│ Predictable   │    │ Unix pipeline │    │ Composable    │
│ ACID          │    │ JSON streams  │    │ Pipeline      │
└───────────────┘    └───────────────┘    └───────────────┘
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              ▼
                    ┌───────────────────┐
                    │  TRANSLATION      │
                    │  TEAM (Py)        │
                    │                   │
                    │ Domain:           │
                    │ Context-aware     │
                    │ translation       │
                    │                   │
                    │ CUPID:            │
                    │ Idiomatic LLM     │
                    │ Provider pattern  │
                    └───────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│  JOB          │    │  AUDIO        │    │  TEXT         │
│  ORCHESTRATOR │    │  TEAM (Rs)    │    │  PROCESSING   │
│  TEAM (Go)    │    │               │    │  (Shared lib) │
│               │    │               │    │               │
│ Domain:       │    │ Domain:       │    │ Domain:       │
│ Workflow      │    │ Audiobook gen │    │ Text prep     │
│               │    │               │    │               │
│ CUPID:        │    │ CUPID:        │    │ CUPID:        │
│ Predictable   │    │ Unix pipeline │    │ Composable    │
│ Durable exec  │    │ Rust DSP      │    │ Library + CLI │
└───────────────┘    └───────────────┘    └───────────────┘
```

---

## 10. Appendix: CUPID Code Patterns Reference

### 10.1 Composable: Dependency Injection Pattern
```python
# ❌ NOT Composable: Hardcoded dependencies
class TranslationOrchestrator:
    def __init__(self):
        self.chapter_repo = ChapterRepository()  # Hardcoded!
        self.llm = NvidiaLLM()                   # Hardcoded!

# ✅ Composable: Injected protocols
class TranslationOrchestrator:
    def __init__(
        self,
        chapter_repo: ChapterRepositoryProtocol,
        glossary_repo: GlossaryRepositoryProtocol,
        translator: TranslatorProtocol,
        job_repo: Optional[JobRepositoryProtocol] = None,
    ):
        self.chapter_repo = chapter_repo
        self.glossary_repo = glossary_repo
        self.translator = translator
        self.job_repo = job_repo
```

### 10.2 Unix Philosophy: CLI as First-Class Interface
```python
# Every service has a CLI that works in pipelines
# Document Service:
#   pdftranslator-doc extract input.pdf --format json > extracted.json
#   pdftranslator-doc split extracted.json --by chapters > chapters.jsonl

# Translation Service:
#   pdftranslator-translate --source en --target es --provider nvidia < text.txt > translated.txt

# Audio Service:
#   pdftranslator-audio --voice paulina --format m4a < translated.txt > audiobook.m4a

# Composable pipeline:
#   pdftranslator-doc extract book.pdf | \
#   pdftranslator-translate --provider gemini | \
#   pdftranslator-audio --voice paulina > book.m4a
```

### 10.3 Predictable: Fixed Retry Policy
```python
# ❌ Unpredictable: Ad-hoc retries
async def call_llm(prompt):
    for i in range(3):  # Magic number
        try:
            return await llm(prompt)
        except Exception:
            await asyncio.sleep(1 * i)  # Linear backoff

# ✅ Predictable: Configurable, observable retry policy
@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    exponential_base: float = 2.0
    jitter: float = 0.1
    retry_on: tuple[type[Exception], ...] = (TimeoutError, ConnectionError, RateLimitError)

async def call_with_retry(
    func: Callable,
    policy: RetryPolicy = RetryPolicy(),
) -> Any:
    last_error = None
    for attempt in range(policy.max_attempts):
        try:
            return await func()
        except policy.retry_on as e:
            last_error = e
            delay = min(
                policy.base_delay * (policy.exponential_base ** attempt),
                policy.max_delay
            )
            delay += random.uniform(-policy.jitter, policy.jitter)
            logger.warning(f"Attempt {attempt+1} failed: {e}, retrying in {delay:.1f}s")
            await asyncio.sleep(delay)
    raise RetryExhaustedError(policy.max_attempts, last_error)
```

### 10.4 Idiomatic: Protocol-Based Abstractions
```python
# Python: Protocol for LLM providers (structural subtyping)
from typing import Protocol, runtime_checkable

@runtime_checkable
class LLMProvider(Protocol):
    """Idiomatic: Protocol = duck typing with static checking"""
    
    @property
    def name(self) -> str: ...
    
    @property
    def model(self) -> str: ...
    
    async def complete(self, prompt: str, **kwargs) -> str: ...
    
    async def stream(self, prompt: str, **kwargs) -> AsyncIterator[str]: ...
    
    def count_tokens(self, text: str) -> int: ...
    
    def chunk_text(self, text: str, max_tokens: int) -> list[str]: ...

# Implementations are idiomatic to their SDK
class NvidiaProvider:
    def __init__(self, api_key: str, model: str = "nemotron-3-ultra"):
        self._client = NVIDIAClient(api_key)
        self._model = model
    
    @property
    def name(self) -> str: return "nvidia"
    
    @property
    def model(self) -> str: return self._model
    
    async def complete(self, prompt: str, **kwargs) -> str:
        return await self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
            **kwargs
        )
```

### 10.5 Domain-Focused: Rich Domain Models
```python
# ❌ Anemic: Data only
@dataclass
class Chapter:
    id: int
    volume_id: int
    title: str
    original_text: str
    translated_text: str | None

# ✅ Domain-Focused: Behavior + Invariants
class Chapter:
    def __init__(
        self,
        volume_id: VolumeId,
        number: ChapterNumber | None,
        title: str,
        original_text: str,
    ):
        self.id = ChapterId.generate()
        self.volume_id = volume_id
        self.number = number
        self.title = title
        self._original_text = original_text
        self._translated_text: str | None = None
        self._status = ChapterStatus.PENDING
    
    @property
    def is_translated(self) -> bool:
        return self._translated_text is not None
    
    def translate(self, translation: str) -> None:
        """Domain invariant: cannot re-translate without explicit reset"""
        if self._translated_text is not None:
            raise DomainError("Chapter already translated; call reset() first")
        if not translation.strip():
            raise DomainError("Translation cannot be empty")
        self._translated_text = translation
        self._status = ChapterStatus.TRANSLATED
        self._domain_events.append(ChapterTranslatedEvent(self.id, len(translation)))
    
    def reset_translation(self) -> None:
        self._translated_text = None
        self._status = ChapterStatus.PENDING
        self._domain_events.append(ChapterTranslationResetEvent(self.id))
    
    def apply_substitution_rules(self, rules: list[SubstitutionRule]) -> None:
        if self._translated_text:
            for rule in rules:
                self._translated_text = rule.apply(self._translated_text)
            self._domain_events.append(ChapterTextModifiedEvent(self.id))
```

---

## 11. Next Steps (CUPID-Ordered)

| Priority | Action | CUPID Principle |
|----------|--------|-----------------|
| 1 | **Event Storming Workshop** | Domain-Focused — discover true bounded contexts |
| 2 | **Extract Catalog Service (Read-Only)** | Composable — prove API works for UI |
| 3 | **Build Document CLI (`file → JSON`)** | Unix Philosophy — verify pipeline works |
| 4 | **Define Event Schemas (CloudEvents + Avro)** | Predictable — schema registry first |
| 5 | **Platform: K8s + Kafka + PostgreSQL + Observability** | Idiomatic — right runtime per service |
| 6 | **ADR: CUPID Compliance Checklist for All Services** | All — architectural guardrails |

---

*Document Version: 1.0*  
*Philosophy: CUPID — Composable, Unix Philosophy, Predictable, Idiomatic, Domain-Focused*  
*Author: Architecture Team*  
*Review Date: 2025-07-18*