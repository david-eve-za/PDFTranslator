# PDFTranslator - Microservices Architecture Proposal

**Date:** 2025-07-11  
**Version:** 1.0  
**Status:** Draft for Review

---

## Executive Summary

This document proposes a microservices architecture for the PDFTranslator monolithic application. The current architecture is a single FastAPI + SQLite + Angular application that handles document extraction, translation, glossary management, chapter splitting, audiobook generation, and job orchestration.

The proposed architecture decomposes the system into **7 core domain services** with clear bounded contexts, enabling independent deployability, scalability, and technology diversity.

---

## 1. Current Architecture Analysis

### 1.1 System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                      MONOLITH (FastAPI)                         │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐ ┌──────────┐ ┌────────────┐ ┌──────────────┐  │
│  │  Document   │ │   LLM    │ │  Glossary  │ │ Translation  │  │
│  │ Extraction  │ │ Factory  │ │  System    │ │ Orchestrator │  │
│  └──────┬──────┘ └────┬─────┘ └─────┬──────┘ └──────┬───────┘  │
│         │             │             │                │         │
│  ┌──────┴─────┐ ┌─────┴─────┐ ┌─────┴──────┐ ┌───────┴───────┐  │
│  │   Docling  │ │ NVIDIA/   │ │ SQLite +   │ │ SQLite DB     │  │
│  │  Extractor │ │ Gemini/   │ │ pgvector   │ │ (Monolithic)  │  │
│  └────────────┘ │ Ollama    │ └────────────┘ └───────────────┘  │
│                 └───────────┘                                    │
│  ┌─────────────┐ ┌─────────────┐ ┌──────────────┐               │
│  │  Audio Gen  │ │  Chapter    │ │ Substitution │               │
│  │ (macOS say) │ │  Splitter   │ │   Rules      │               │
│  └──────┬──────┘ └──────┬──────┘ └──────┬───────┘               │
│         │               │               │                         │
└─────────┼───────────────┼───────────────┼────────────────────────┘
          │               │               │
    ┌─────┴─────┐   ┌─────┴─────┐   ┌─────┴─────┐
    │  SQLite │   │  SQLite   │   │  Files    │
    │(single DB)│   │(single DB)│   │ (uploads) │
    └───────────┘   └───────────┘   └───────────┘
```

### 1.2 Identified Bounded Contexts

| Context | Domain | Key Entities | Current Location |
|---------|--------|-------------|------------------|
| **Document Processing** | Extract text/structure from PDF/EPUB/DOCX | `DoclingDocument`, pages, elements | `infrastructure/document/` |
| **LLM Translation** | Multi-provider LLM orchestration | `LLMClient`, `Translator`, chunks | `infrastructure/llm/`, `tools/Translator.py` |
| **Glossary Management** | Terminology consistency across translations | `GlossaryEntry`, `TermContext`, embeddings | `database/`, `services/glossary_translator.py` |
| **Chapter Management** | Work/Volume/Chapter hierarchy & splitting | `Work`, `Volume`, `Chapter` | `core/models/work.py`, `database/repositories/` |
| **Translation Orchestration** | Job scheduling, progress tracking, retry logic | `TranslationJob`, `TranslationProgress` | `services/translation_orchestrator.py` |
| **Audio Generation** | TTS synthesis from translated text | Audio files, voice config | `tools/AudioGenerator.py` |
| **Text Processing** | Substitution rules, overlap cleaning | `SubstitutionRule`, `OverlapCleaner` | `tools/`, `services/text_substitution_service.py` |

### 1.3 Current Coupling Points

1. **Database Coupling**: All services share a single SQLite database
2. **In-Process Calls**: Orchestrator directly instantiates repositories and LLM clients
3. **Shared Models**: Domain models (`Work`, `Volume`, `Chapter`) used across all contexts
4. **Configuration Coupling**: Single `Settings` object passed everywhere
5. **Temporal Coupling**: CLI commands execute entire pipelines synchronously

---

## 2. Target Microservices Architecture

### 2.1 Service Decomposition

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            API GATEWAY (Kong/Traefik)                        │
│                         Rate Limiting │ Auth │ Routing                       │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
        ┌────────────────────────────┼────────────────────────────┐
        ▼                            ▼                            ▼
┌───────────────┐            ┌───────────────┐            ┌───────────────┐
│  DOCUMENT     │            │  CATALOG      │            │  TRANSLATION  │
│  SERVICE      │            │  SERVICE      │            │  SERVICE      │
│               │            │               │            │               │
│ • Docling     │            │ • Works       │            │ • LLM Factory │
│ • Extraction  │◄──────────►│ • Volumes     │◄──────────►│ • Translation │
│ • OCR         │   Events   │ • Chapters    │   Events   │ • Chunking    │
│ • Chunking    │            │ • Metadata    │            │ • Overlap     │
└───────┬───────┘            └───────┬───────┘            └───────┬───────┘
        │                            │                            │
        │                            │                            │
        ▼                            ▼                            ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           MESSAGE BUS (Kafka/RabbitMQ/NATS)                  │
│  Events: DocumentExtracted │ VolumeCreated │ ChapterCreated │ TranslationRequested │
└─────────────────────────────────────────────────────────────────────────────┘
        │                            │                            │
        ▼                            ▼                            ▼
┌───────────────┐            ┌───────────────┐            ┌───────────────┐
│  GLOSSARY     │            │  JOB          │            │  AUDIO        │
│  SERVICE      │            │  ORCHESTRATOR │            │  SERVICE      │
│               │            │               │            │               │
│ • Term Extract│            │ • Job Queue   │            │ • TTS (multi) │
│ • Embeddings  │            │ • Progress    │            │ • Audio Merge │
│ • Validation  │            │ • Retry/DLQ   │            │ • Formats     │
│ • Search      │            │ • Scheduling  │            │ • Streaming   │
└───────┬───────┘            └───────┬───────┘            └───────┬───────┘
        │                            │                            │
        ▼                            ▼                            ▼
┌───────────────┐            ┌───────────────┐            ┌───────────────┐
│  Glossary DB  │            │  Job State DB │            │  Object Store │
│  (PostgreSQL  │            │  (PostgreSQL) │            │  (S3/MinIO)   │
│  + pgvector)  │            │               │            │               │
└───────────────┘            └───────────────┘            └───────────────┘
```

### 2.2 Service Definitions

#### 2.2.1 Document Service
**Responsibility**: Document ingestion, text extraction, structure analysis

| Aspect | Details |
|--------|---------|
| **Technology** | Python/FastAPI, Docling, PyMuPDF (fallback) |
| **Database** | Metadata in Catalog Service; extracted content in Object Store |
| **API** | `POST /documents/upload`, `GET /documents/{id}/text`, `GET /documents/{id}/structure` |
| **Events Emitted** | `DocumentUploaded`, `DocumentExtracted`, `DocumentExtractionFailed` |
| **Scaling** | Horizontal (stateless), GPU workers for OCR |
| **Storage** | S3/MinIO for raw files + extracted text (JSON) |

**Data Model:**
```protobuf
message Document {
  string id = 1;
  string original_filename = 2;
  string mime_type = 3;
  int64 file_size = 4;
  DocumentStatus status = 5;
  ExtractedContent content = 6;
  DocumentMetadata metadata = 7;
  repeated ChapterBoundary chapters = 8;
  google.protobuf.Timestamp created_at = 9;
}

message ExtractedContent {
  string full_text = 1;
  repeated Page pages = 2;
  repeated Image images = 3;
  map<string, string> structure = 4;  // JSON serialized
}
```

#### 2.2.2 Catalog Service
**Responsibility**: Work/Volume/Chapter metadata management, hierarchy

| Aspect | Details |
|--------|---------|
| **Technology** | Go or Rust (high read throughput), gRPC + REST |
| **Database** | PostgreSQL (ACID for metadata) |
| **API** | `CRUD /works`, `CRUD /works/{id}/volumes`, `CRUD /volumes/{id}/chapters` |
| **Events Consumed** | `DocumentExtracted` → creates Work/Volume/Chapter |
| **Events Emitted** | `WorkCreated`, `VolumeCreated`, `ChapterCreated`, `ChapterUpdated` |
| **Key Feature** | Full-text search on titles, hierarchical queries |

**Data Model:**
```sql
-- PostgreSQL
CREATE TABLE works (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(500) NOT NULL,
    title_translated VARCHAR(500),
    source_lang CHAR(2),
    target_lang CHAR(2),
    author VARCHAR(300),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE volumes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    work_id UUID REFERENCES works(id) ON DELETE CASCADE,
    volume_number INT NOT NULL,
    title VARCHAR(500),
    full_text_path TEXT,  -- S3 path
    translated_text_path TEXT,
    glossary_status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(work_id, volume_number)
);

CREATE TABLE chapters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    volume_id UUID REFERENCES volumes(id) ON DELETE CASCADE,
    chapter_number INT,
    title VARCHAR(500),
    start_position INT,
    end_position INT,
    original_text_path TEXT,  -- S3 path
    translated_text_path TEXT,
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

#### 2.2.3 Glossary Service
**Responsibility**: Terminology extraction, validation, translation, semantic search

| Aspect | Details |
|--------|---------|
| **Technology** | Python/FastAPI, sentence-transformers, pgvector |
| **Database** | PostgreSQL + pgvector (HNSW index) |
| **API** | `POST /works/{id}/glossary/extract`, `POST /glossary/search`, `CRUD /terms` |
| **Events Consumed** | `ChapterCreated`, `VolumeCreated`, `TranslationCompleted` |
| **Events Emitted** | `GlossaryTermExtracted`, `GlossaryTermValidated`, `GlossaryBuilt` |
| **Scaling** | Read replicas for search; write leader for embeddings |
| **Artifact Storage** | Embeddings in pgvector; raw contexts in PostgreSQL |

**Data Model:**
```sql
CREATE TABLE glossary_terms (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    work_id UUID NOT NULL,  -- references Catalog Service
    term VARCHAR(200) NOT NULL,
    translation VARCHAR(500),
    entity_type VARCHAR(50) DEFAULT 'other',
    is_proper_noun BOOLEAN DEFAULT false,
    do_not_translate BOOLEAN DEFAULT false,
    confidence REAL DEFAULT 0.0,
    frequency INT DEFAULT 0,
    source_lang CHAR(2) DEFAULT 'en',
    target_lang CHAR(2) DEFAULT 'es',
    embedding vector(768),  -- pgvector
    contexts JSONB,  -- [{"hint": "...", "translation": "...", "examples": [...]}]
    is_verified BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX ON glossary_terms USING hnsw (embedding vector_cosine_ops);
CREATE INDEX ON glossary_terms (work_id, term);
```

**Key Algorithm**: 
- Entity extraction via NER (spaCy) + LLM validation
- Embedding generation: `text-embedding-3-small` (1536 dim) or `nv-embed-v1` (768 dim)
- Semantic search: `SELECT * FROM glossary_terms WHERE work_id = ? ORDER BY embedding <-> query_embedding LIMIT 20`

#### 2.2.4 Translation Service
**Responsibility**: Core translation logic, chunking, LLM orchestration, glossary application

| Aspect | Details |
|--------|---------|
| **Technology** | Python/FastAPI, LLM SDKs (NVIDIA, Gemini, Ollama) |
| **Database** | None (stateless); cache in Redis |
| **API** | `POST /translate`, `POST /translate/batch`, `GET /models` |
| **Events Consumed** | `TranslationRequested` (from Job Orchestrator) |
| **Events Emitted** | `TranslationCompleted`, `TranslationFailed`, `TranslationProgress` |
| **Scaling** | Horizontal; LLM calls are stateless |
| **Configuration** | Provider selection per request; model params |

**Request/Response:**
```protobuf
message TranslateRequest {
  string text = 1;
  string source_lang = 2;
  string target_lang = 3;
  repeated GlossaryTerm glossary = 4;  // top-k from Glossary Service
  LLMConfig llm_config = 5;
}

message TranslateResponse {
  string translated_text = 1;
  repeated ChunkTranslation chunks = 2;
  TranslationMetadata metadata = 3;
}
```

**Chunking Strategy**: Adaptive token-based with overlap (current `TokenChunkCalculator` moved here)

#### 2.2.5 Job Orchestrator Service
**Responsibility**: Workflow orchestration, job queue, progress tracking, retries, scheduling

| Aspect | Details |
|--------|---------|
| **Technology** | Go (Temporal.io) or Python (Celery + Redis) |
| **Database** | PostgreSQL (job state), Redis (queue) |
| **API** | `POST /jobs`, `GET /jobs/{id}`, `GET /jobs/{id}/progress` (SSE/WS) |
| **Events Consumed** | `TranslationCompleted`, `AudioGenerated`, etc. |
| **Events Emitted** | `JobCreated`, `JobStarted`, `JobCompleted`, `JobFailed`, `TranslationRequested` |
| **Key Features** |
| **Scaling** | Leader election for scheduler; workers horizontal |

**Job Types:**
```python
class JobType(Enum):
    DOCUMENT_PROCESSING = "document_processing"  # Extract → Split → Glossary → Translate
    GLOSSARY_BUILD = "glossary_build"            # Extract terms → Validate → Translate → Save
    TRANSLATION = "translation"                   # Book/Volume/Chapter translation
    AUDIO_GENERATION = "audio_generation"        # Translate → TTS → Merge
    CHAPTER_SPLIT = "chapter_split"              # Manual/auto chapter boundaries
```

#### 2.2.6 Audio Service
**Responsibility**: Text-to-speech, audio post-processing, format conversion

| Aspect | Details |
|--------|---------|
| **Technology** | Python/FastAPI, multiple TTS backends |
| **Database** | Metadata in PostgreSQL; audio files in S3 |
| **API** | `POST /audio/generate`, `GET /audio/{id}/stream`, `GET /audio/{id}/download` |
| **Events Consumed** | `TranslationCompleted`, `AudioGenerationRequested` |
| **Events Emitted** | `AudioGenerationStarted`, `AudioGenerated`, `AudioGenerationFailed` |
| **TTS Backends** | macOS `say`, Azure TTS, ElevenLabs, Coqui TTS, piper |
| **Scaling** | GPU workers for neural TTS; CPU for macOS say |

**Audio Pipeline:**
```
Translated Text → Chunk by sentences → TTS per chunk → Silence normalize → Concatenate → Encode (M4A/MP3/WAV) → Upload to S3
```

#### 2.2.7 Text Processing Service (Optional - could be library)
**Responsibility**: Substitution rules, overlap cleaning, text normalization

| Aspect | Details |
|--------|---------|
| **Technology** | Rust or Go (high throughput text processing) |
| **Deployment** | Sidecar/library; or HTTP service |
| **API** | `POST /text/clean`, `POST /text/substitute`, `POST /text/normalize` |
| **Use Cases** | Regex substitution rules, chapter overlap removal, whitespace normalization |

---

### 2.3 Shared Infrastructure

#### 2.3.1 API Gateway
- **Technology**: Kong, Traefik, or AWS API Gateway
- **Features**: Authentication (JWT/OAuth), rate limiting, request routing, SSL termination
- **Routes**: `/api/v1/documents/*` → Document Service, `/api/v1/works/*` → Catalog Service, etc.

#### 2.3.2 Message Bus
- **Technology**: Apache Kafka (production) / NATS (simpler) / RabbitMQ
- **Topics**:
  - `document.events` - Document lifecycle
  - `catalog.events` - Work/Volume/Chapter changes
  - `translation.events` - Translation requests/completions
  - `glossary.events` - Term extraction/validation
  - `job.events` - Job orchestration
  - `audio.events` - Audio generation

#### 2.3.3 Service Discovery & Config
- **Consul/etcd** or **Kubernetes DNS** for service discovery
- **Vault/SealedSecrets** for API keys (NVIDIA, Gemini, ElevenLabs)
- **ConfigMap** for feature flags, model parameters

#### 2.3.4 Observability Stack
- **Logging**: Loki + Promtail (structured JSON logs)
- **Metrics**: Prometheus + Grafana (RED metrics per service)
- **Tracing**: Jaeger/Tempo (OpenTelemetry instrumentation)
- **Alerting**: Alertmanager + PagerDuty/Slack

---

## 3. Data Strategy

### 3.1 Database per Service
| Service | Database | Justification |
|---------|----------|---------------|
| Catalog | PostgreSQL | Relational metadata, ACID, complex queries |
| Glossary | PostgreSQL + pgvector | Hybrid relational + vector search |
| Jobs | PostgreSQL | Transactional job state, scheduling |
| Documents | PostgreSQL (metadata) + S3 (content) | Large binary storage separation |
| Audio | PostgreSQL (metadata) + S3 (files) | Large binary storage separation |

### 3.2 Data Synchronization
- **Event-Driven**: Services emit domain events; consumers update their local projections
- **No Distributed Transactions**: Saga pattern for cross-service operations
- **Eventual Consistency**: Acceptable for translation workflows (minutes latency OK)
- **Idempotency**: All event handlers idempotent (deduplication via event ID)

### 3.3 Migration Strategy from SQLite
```
Phase 1: Dual-write
  Monolith writes to SQLite + emits events
  New services consume events, build own stores

Phase 2: Read from new services
  Monolith reads from Catalog/Glossary APIs
  Write still to SQLite (or dual-write)

Phase 3: Cutover
  Monolith deprecated
  All writes through new services
  SQLite decommissioned
```

---

## 4. Communication Patterns

### 4.1 Synchronous (Request-Response)
- **REST/HTTP** for CRUD operations, queries
- **gRPC** for high-throughput internal calls (e.g., Translation → Glossary search)

### 4.2 Asynchronous (Event-Driven)
- **Kafka/NATS** for workflow orchestration
- **Event Schema**: CloudEvents format with Avro/Protobuf schemas in Schema Registry

### 4.3 Example Workflow: Full Document Processing

```
┌─────────┐     ┌─────────────┐     ┌────────────┐     ┌──────────────┐
│  Client │────►│ API Gateway │────►│ Job Orch.  │────►│ Document Svc │
└─────────┘     └─────────────┘     └─────┬┘     └────────────┘     └──────┬──────┘
                                 │                                 │
                    JobCreated    │              DocumentExtracted  │
                    event         │                  event          │
                           ┌──────┴──────┐                ┌────────┴────────┐
                           ▼             ▼                ▼                 ▼
                     ┌─────────┐   ┌──────────┐    ┌───────────┐     ┌────────────┐
                     │ Catalog │   │ Glossary │    │  Audio    │     │  Storage   │
                     │ Service │   │ Service  │    │ Service   │     │  (S3)      │
                     └────┬────┘   └────┬─────┘    └─────┬─────┘     └────────────┘
                          │             │                │
                    VolumeCreated  TermExtracted    AudioGenerated
                    event          event             event
```

---

## 5. Implementation Roadmap

### Phase 1: Foundation (Weeks 1-4)
- [ ] Set up Kubernetes cluster (kind/k3s for dev, EKS/GKE for prod)
- [ ] Deploy Kafka, PostgreSQL, Redis, MinIO, API Gateway
- [ ] Implement shared libraries: event schemas, client SDKs, observability
- [ ] Create CI/CD pipelines (GitHub Actions → ArgoCD)

### Phase 2: Core Services (Weeks 5-12)
| Sprint | Service | Deliverable |
|--------|---------|-------------|
| 5-6 | **Catalog Service** | Work/Volume/Chapter CRUD, PostgreSQL schema, gRPC/REST API |
| 7-8 | **Document Service** | Docling extraction, S3 storage, chapter boundary detection |
| 9-10 | **Glossary Service** | Term extraction, pgvector embeddings, semantic search API |
| 11-12 | **Translation Service** | LLM factory, chunking, glossary-aware translation, provider abstraction |

### Phase 3: Orchestration & Audio (Weeks 13-20)
| Sprint | Service | Deliverable |
|--------|---------|-------------|
| 13-14 | **Job Orchestrator** | Temporal.io workflows, job queue, progress tracking (SSE) |
| 15-16 | **Audio Service** | Multi-TTS backend, audio processing pipeline, streaming |
| 17-18 | **Text Processing** | Substitution rules, overlap cleaner as library/sidecar |
| 19-20 | **Integration** | End-to-end workflows, event choreography, DLQ handling |

### Phase 4: Migration & Frontend (Weeks 21-28)
| Sprint | Focus | Deliverable |
|--------|-------|-------------|
| 21-22 | **Frontend Migration** | Angular → new API Gateway, SSE for progress |
| 23-24 | **Data Migration** | Dual-write, backfill, cutover scripts |
| 25-26 | **CLI Migration** | New `pdftranslator` CLI talking to Gateway |
| 27-28 | **Observability** | Dashboards, alerts, runbooks, chaos testing |

---

## 6. Technical Decisions & Trade-offs

### 6.1 Service Granularity
| Decision | Rationale |
|----------|-----------|
| **7 services** (not 20) | Aligns with bounded contexts; avoids nanoservice overhead |
| **Translation + LLM combined** | Tight coupling; LLM config is intrinsic to translation |
| **Glossary separate** | Different scaling profile (vector search), different team ownership |
| **Catalog separate** | Metadata is read-heavy, different consistency needs |

### 6.2 Technology Choices
| Layer | Choice | Alternative Considered |
|-------|--------|------------------------|
| API Gateway | Kong | Traefik, AWS API Gateway |
| Message Bus | Kafka | NATS, RabbitMQ |
| Orchestration | Temporal.io | Celery, custom state machine |
| Service Mesh | Istio (later) | Linkerd, none initially |
| Vector DB | pgvector | Pinecone, Weaviate, Qdrant |
| TTS | Multi-backend abstraction | Single provider |

### 6.3 Consistency Model
- **Within Service**: Strong consistency (ACID)
- **Cross-Service**: Eventual consistency (Saga pattern)
- **User-Facing**: Optimistic UI with SSE progress updates

### 6.4 Error Handling Strategy
```
Retry Policy:
  - Transient (network, rate limit): Exponential backoff 3x
  - LLM errors: Retry with different provider (fallback chain)
  - Validation errors: Dead letter queue + alert
  - Business logic errors: Compensating transactions (Saga)
```

---

## 7. API Contracts (OpenAPI/Protobuf)

### 7.1 Service Contracts Location
```
api-contracts/
├── catalog/
│   ├── openapi.yaml
│   └── catalog.proto
├── document/
│   ├── openapi.yaml
│   └── document.proto
├── glossary/
│   ├── openapi.yaml
│   └── glossary.proto
├── translation/
│   ├── openapi.yaml
│   └── translation.proto
├── audio/
│   ├── openapi.yaml
│   └── audio.proto
└── job/
    ├── openapi.yaml
    └── job.proto
```

### 7.2 Example: Translation Service API
```yaml
# translation/openapi.yaml excerpt
paths:
  /translate:
    post:
      summary: Translate text with glossary
      operationId: translateText
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/TranslateRequest'
      responses:
        '200':
          description: Translation result
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/TranslateResponse'
        '422': { $ref: '#/components/responses/ValidationError' }
        '503': { $ref: '#/components/responses/ServiceUnavailable' }

components:
  schemas:
    TranslateRequest:
      type: object
      required: [text, source_lang, target_lang]
      properties:
        text:
          type: string
          maxLength: 100000
        source_lang:
          type: string
          pattern: '^[a-z]{2}(-[A-Z]{2})?$'
        target_lang:
          type: string
          pattern: '^[a-z]{2}(-[A-Z]{2})?$'
        glossary_terms:
          type: array
          items: { $ref: '#/components/schemas/GlossaryTerm' }
          maxItems: 50
        llm_config:
          $ref: '#/components/schemas/LLMConfig'
    
    GlossaryTerm:
      type: object
      properties:
        term: { type: string }
        translation: { type: string }
        entity_type: { type: string }
        do_not_translate: { type: boolean }
```

---

## 8. Deployment Architecture

### 8.1 Kubernetes Resources (per Service)
```yaml
# Base deployment template
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{SERVICE_NAME}}
spec:
  replicas: 3
  selector:
    matchLabels:
      app: {{SERVICE_NAME}}
  template:
    spec:
      containers:
      - name: {{SERVICE_NAME}}
        image: {{REGISTRY}}/{{SERVICE_NAME}}:{{VERSION}}
        ports: [{containerPort: 8000}]
        envFrom:
        - configMapRef: {name: {{SERVICE_NAME}}-config}
        - secretRef: {name: {{SERVICE_NAME}}-secrets}
        resources:
          requests: {memory: "256Mi", cpu: "250m"}
          limits: {memory: "1Gi", cpu: "1000m"}
        livenessProbe:
          httpGet: {path: /health, port: 8000}
          initialDelaySeconds: 10
        readinessProbe:
          httpGet: {path: /ready, port: 8000}
          initialDelaySeconds: 5
---
apiVersion: v1
kind: Service
metadata: {name: {{SERVICE_NAME}}}
spec:
  selector: {app: {{SERVICE_NAME}}}
  ports: [{port: 80, targetPort: 8000}]
```

### 8.2 Service-Specific Resources
| Service | Special Requirements |
|---------|---------------------|
| Document | GPU node pool for OCR; larger memory limits |
| Translation | GPU node pool for local LLM (Ollama); secret for API keys |
| Audio | GPU for neural TTS; large ephemeral storage for audio processing |
| Glossary | pgvector extension; read replicas |
| Job Orchestrator | Temporal cluster (separate namespace) |

---

## 9. Testing Strategy

### 9.1 Contract Testing
- **Pact** for consumer-driven contracts between services
- **Schema Registry** for event schemas (Avro/Protobuf)

### 9.2 Integration Testing
- **TestContainers** for PostgreSQL, Kafka, Redis in CI
- **Contract tests** run on every PR
- **End-to-end** workflow tests in staging

### 9.3 Chaos Engineering
- **LitmusChaos** or **Chaos Mesh** for:
  - Pod kills during translation
  - Kafka partition leader election
  - Database failover
  - Network latency injection

---

## 10. Migration Checklist

### 10.1 Pre-Migration
- [ ] Domain model documentation (DDD bounded contexts)
- [ ] Event storming workshop with team
- [ ] API contract design (OpenAPI/Protobuf)
- [ ] Infrastructure as Code (Terraform/Pulumi)
- [ ] CI/CD pipeline for microservices
- [ ] Observability stack deployed

### 10.2 Service Extraction Order (Strangler Fig)
1. **Catalog Service** - Read-only initially, powers new UI
2. **Document Service** - Extract upload/extraction logic
3. **Glossary Service** - Extract term management
4. **Translation Service** - Extract LLM orchestration
5. **Job Orchestrator** - Replace in-process job execution
6. **Audio Service** - Extract TTS pipeline
7. **Text Processing** - Extract as library or sidecar

### 10.3 Validation Criteria per Service
- [ ] All existing API contracts pass
- [ ] Load test: 2x production throughput
- [ ] Chaos test: survives single AZ failure
- [ ] Migration script: data parity with monolith
- [ ] Rollback plan documented and tested

---

## 11. Cost Estimation (AWS Example)

| Component | Monthly Estimate (USD) | Notes |
|-----------|------------------------|-------|
| EKS (3 m6i.xlarge) | $450 | Control plane + workers |
| RDS PostgreSQL (db.r6g.xlarge × 2) | $700 | Multi-AZ, read replica |
| ElastiCache Redis (cache.r6g.xlarge) | $200 | Job queue, caching |
| MSK Kafka (3 m5.large) | $300 | Or self-managed on EKS |
| S3 Storage (1TB) | $23 | Documents + audio |
| CloudFront | $50 | Audio streaming |
| NAT Gateway (2 AZ) | $90 | Outbound internet |
| **Total Infrastructure** | **~$1,800/month** | Excludes LLM API costs |
| LLM APIs (NVIDIA/Gemini) | Variable | Per-token pricing |

---

## 12. Team Structure (Inverse Conway Maneuver)

```
┌─────────────────────────────────────────────────────────┐
│                   PLATFORM TEAM                          │
│  Kubernetes │ CI/CD │ Observability │ Security │ Infra  │
└─────────────────────────────────────────────────────────┘
                    ▲               ▲               ▲
        ┌───────────┤───────────────┤───────────────┤───────────┐
        ▼           ▼               ▼               ▼           ▼
┌─────────────┐ ┌───────────┐ ┌────────────┐ ┌──────────┐ ┌─────────┐
│   CATALOG   │ │  DOCUMENT │ │  GLOSSARY  │ │TRANSLATION│ │ AUDIO   │
│   TEAM      │ │   TEAM    │ │   TEAM     │ │  TEAM    │ │  TEAM   │
└─────────────┘ └───────────┘ └────────────┘ └──────────┘ └─────────┘
```

**Team Responsibilities:**
- **Catalog Team**: Work/Volume/Chapter metadata, search, hierarchy
- **Document Team**: Extraction, OCR, format support, chunking
- **Glossary Team**: NER, embeddings, semantic search, term workflows
- **Translation Team**: LLM integration, chunking strategies, provider management
- **Audio Team**: TTS backends, audio processing, streaming
- **Platform Team**: Shared infrastructure, developer experience, security

---

## 13. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Distributed system complexity | High | High | Start with modular monolith; extract incrementally |
| Data consistency issues | Medium | High | Saga pattern, idempotent consumers, reconciliation jobs |
| Latency overhead (network) | Medium | Medium | gRPC for hot paths; co-locate services; caching |
| Operational burden | High | Medium | Platform team; GitOps; comprehensive observability |
| LLM API cost explosion | Medium | High | Request budgets; caching; fallback to cheaper models |
| Team cognitive load | High | Medium | Clear ownership; shared libraries; documentation |

---

## 14. Appendix: Current Code Mapping to Services

| Current Module | Target Service | Extraction Complexity |
|----------------|----------------|----------------------|
| `infrastructure/document/docling_extractor.py` | Document Service | Low (stateless) |
| `infrastructure/llm/*` | Translation Service | Low (protocol-based) |
| `tools/Translator.py` | Translation Service | Low |
| `services/translation_orchestrator.py` | Job Orchestrator | Medium (stateful) |
| `database/repositories/*` | Catalog + Glossary | High (shared DB) |
| `core/models/work.py` | Catalog Service | Medium (shared models) |
| `services/glossary_translator.py` | Glossary Service | Medium |
| `database/services/entity_extractor.py` | Glossary Service | Medium |
| `database/services/vector_store.py` | Glossary Service | Medium |
| `tools/AudioGenerator.py` | Audio Service | Low |
| `tools/OverlapCleaner.py` | Text Processing | Low |
| `services/text_substitution_service.py` | Text Processing | Low |
| `cli/commands/*` | CLI (thin client) | Low |

---

## 15. Next Steps

1. **Review & Validate** - Team review of bounded contexts and service boundaries
2. **Proof of Concept** - Extract Catalog Service first (read-only, lowest risk)
3. **Infrastructure Sprint** - Provision Kubernetes, Kafka, PostgreSQL, observability
4. **Architecture Decision Records** - Document key decisions (ADR format)
5. **Team Alignment** - Assign service ownership, establish APIs contracts

---

*Document Version: 1.0*  
*Author: Architecture Team*  
*Review Date: 2025-07-18*