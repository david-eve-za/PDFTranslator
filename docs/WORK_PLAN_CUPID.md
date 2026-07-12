# PDFTranslator - CUPID Microservices Migration Work Plan

**Based on:** `docs/MICROSERVICES_CUPID_PROPOSAL.md`  
**Date:** 2026-07-12  
**Version:** 1.0  
**Status:** Draft for Review  

---

## ⚠️ MANDATORY WORKING RULES (NO NEGOCIABLES)

### 1. Branching Strategy - OBLIGATORIO
```
MAIN BRANCH (main) → PROTECTED BRANCH
  ├── feature/xxx-descriptive-name      ← New features/services
  ├── refactor/xxx-descriptive-name     ← Refactoring existing code
  ├── chore/xxx-descriptive-name        ← Maintenance, tooling, docs
  └── fix/xxx-descriptive-name          ← Bug fixes
```

**Rules:**
- ✅ **ALWAYS** create new branch from UPDATED `main` (`git checkout main && git pull && git checkout -b feature/new-feature`)
- ✅ **NEVER** work directly on `main`
- ✅ Each feature/refactor/fix = **ONE SINGLE BRANCH**
- ✅ Descriptive branch names: `feature/catalog-service-read-api`, `refactor/extract-document-service`, `chore/setup-changelog`
- ✅ One commit = one atomic logical change (Conventional Commits)
- ✅ PR/MR mandatory for merge to main (even if auto-merge locally)

### 2. Merge Strategy - OBLIGATORIO
```
Feature Branch → Local Review → Tests Pass → Merge to main → Tag version → Update Changelog
```

**Merge Rules:**
- ✅ **Squash and merge** (preferred) or **Rebase and merge** - clean history
- ✅ **NEVER** merge directly without passing tests
- ✅ Semver tag after each merge to main: `v0.2.0`, `v0.3.0`, etc.
- ✅ Update `CHANGELOG.md` **IMMEDIATELY AFTER MERGE**

### 3. Changelog - OBLIGATORIO
- **File:** `CHANGELOG.md` at project root (Keep a Changelog format)
- **Update:** Immediately after each merge to main
- **Format:** Keep a Changelog 1.1.0 + SemVer 2.0.0
- **Rollback:** `git checkout v0.X.Y` to return to working version

---

## 📋 PHASE OVERVIEW (From CUPID Proposal)

| Phase | Weeks | CUPID Focus | Key Deliverable |
|-------|-------|-------------|-----------------|
| **1. Composable Extraction** | 1-4 | Composable + Predictable | Catalog API + Document CLI + Event Schemas |
| **2. Unix Pipeline Replacement** | 5-10 | Unix Philosophy + Composable | Glossary HTTP + Translation Provider + Text Processing Lib |
| **3. Predictable Orchestration** | 11-16 | Predictable + Domain-Focused | Temporal Workflows + Audio Service + Kafka Events |
| **4. Domain-Focused Cutover** | 17-22 | All Principles | Gateway + Frontend Migration + Monolith Decommission |

---

## 📦 DETAILED SPRINT BREAKDOWN

### PHASE 1: COMPOSABLE EXTRACTION (Weeks 1-4)

#### Sprint 1.1: Setup Changelog & Conventions
**Branch:** `chore/setup-changelog-and-conventions` (from `main`)

```bash
git checkout main && git pull origin main
git checkout -b chore/setup-changelog-and-conventions
```

| Task | Description | Done |
|------|-------------|------|
| 1.1.1 | Create `CHANGELOG.md` (Keep a Changelog format) | ✅ |
| 1.1.2 | Configure `.gitmessage` template (Conventional Commits) | ✅ |
| 1.1.3 | Setup `commitlint` + `husky` pre-commit hooks | ⬜ |
| 1.1.4 | Document conventions in `CONTRIBUTING.md` | ⬜ |
| 1.1.5 | Create `scripts/changelog-update.sh` automation | ✅ |
| 1.1.6 | **Commit:** `chore: add changelog and commit conventions` | ⬜ |
| 1.1.7 | **Merge to main** → Tag `v0.1.0` → Update CHANGELOG | ⬜ |

#### Sprint 1.2: Catalog Service Read-Only API
**Branch:** `feature/catalog-service-read-api` (from `main`)

```bash
git checkout main && git pull origin main
git checkout -b feature/catalog-service-read-api
```

| Task | Description | Done |
|------|-------------|------|
| 1.2.1 | Design OpenAPI contract for Works, Volumes, Chapters | ⬜ |
| 1.2.2 | Implement REST GET endpoints in FastAPI (reuse existing repos) | ⬜ |
| 1.2.3 | Pact contract tests against Angular frontend | ⬜ |
| 1.2.4 | Verify: Angular UI consumes API without visual changes | ⬜ |
| 1.2.5 | **Commit(s):** `feat(catalog): add read-only REST API` | ⬜ |
| 1.2.6 | **Merge to main** → Tag `v0.2.0` → Update CHANGELOG | ⬜ |

#### Sprint 1.3: Document Service CLI Extractor
**Branch:** `feature/document-service-extract-cli` (from `main`)

```bash
git checkout main && git pull origin main
git checkout -b feature/document-service-extract-cli
```

| Task | Description | Done |
|------|-------------|------|
| 1.3.1 | Extract `DoclingExtractor` to independent service | ⬜ |
| 1.3.2 | CLI: `pdftranslator-extract file.pdf --format json > out.json` | ⬜ |
| 1.3.3 | Output: `ExtractedDocument` JSON (Pydantic models) | ⬜ |
| 1.3.4 | Tests: Determinism (same PDF = same JSON) | ⬜ |
| 1.3.5 | **Commit(s):** `feat(document): add CLI extractor with JSON output` | ⬜ |
| 1.3.6 | **Merge to main** → Tag `v0.3.0` → Update CHANGELOG | ⬜ |

#### Sprint 1.4: Event Schemas (CloudEvents + Avro)
**Branch:** `chore/event-schemas-cloud-events` (from `main`)

```bash
git checkout main && git pull origin main
git checkout -b chore/event-schemas-cloud-events
```

| Task | Description | Done |
|------|-------------|------|
| 1.4.1 | Define Avro schemas: `WorkCreated`, `DocumentExtracted`, `GlossaryBuilt`, `TranslationCompleted` | ⬜ |
| 1.4.2 | Configure Schema Registry (Confluent/Apicurio) | ⬜ |
| 1.4.3 | Generate clients: Python, Go, TypeScript | ⬜ |
| 1.4.4 | Document versioning strategy | ⬜ |
| 1.4.5 | **Commit(s):** `chore(events): add CloudEvents + Avro schemas` | ⬜ |
| 1.4.6 | **Merge to main** → Tag `v0.4.0` → Update CHANGELOG | ⬜ |

---

### PHASE 2: UNIX PIPELINE REPLACEMENT (Weeks 5-10)

#### Sprint 2.1: Glossary Pipeline HTTP Service
**Branch:** `feature/glossary-pipeline-http-service` (from `main`)

| Task | Description | Done |
|------|-------------|------|
| 2.1.1 | Decompose `GlossaryPipeline` into stages: Extract → Validate → Translate → Embed → Store | ⬜ |
| 2.1.2 | Each stage = independent HTTP/gRPC endpoint | ⬜ |
| 2.1.3 | Pipeline orchestrator calls stages sequentially | ⬜ |
| 2.1.4 | Unit tests per stage + integration test full pipeline | ⬜ |
| 2.1.5 | **Commit(s):** `feat(glossary): extract pipeline stages as HTTP services` | ⬜ |
| 2.1.6 | **Merge to main** → Tag `v0.5.0` → Update CHANGELOG | ⬜ |

#### Sprint 2.2: Translation Service Provider Pattern
**Branch:** `feature/translation-service-provider-pattern` (from `main`)

| Task | Description | Done |
|------|-------------|------|
| 2.2.1 | Extract `TranslationOrchestrator` → `TranslationService` | ⬜ |
| 2.2.2 | Implement `LLMProvider` Protocol (NVIDIA, Gemini, Ollama) | ⬜ |
| 2.2.3 | `ProviderFactory` for dynamic selection | ⬜ |
| 2.2.4 | `RetryPolicy` configurable (Predictable) | ⬜ |
| 2.2.5 | `GlossaryClient` injected (Composable, not hardcoded) | ⬜ |
| 2.2.6 | Deterministic `TextChunker` extracted | ⬜ |
| 2.2.7 | **Commit(s):** `feat(translation): provider pattern + deterministic chunking` | ⬜ |
| 2.2.8 | **Merge to main** → Tag `v0.6.0` → Update CHANGELOG | ⬜ |

#### Sprint 2.3: Text Processing Library + CLI
**Branch:** `feature/text-processing-lib-cli` (from `main`)

| Task | Description | Done |
|------|-------------|------|
| 2.3.1 | Create `TextPipeline` with fluent builder | ⬜ |
| 2.3.2 | Steps: substitutions, overlap cleaner, normalizer | ⬜ |
| 2.3.3 | CLI pipe: `cat input.txt \| python -m text_processing --normalize > output.txt` | ⬜ |
| 2.3.4 | Tests: pure functions, property-based testing | ⬜ |
| 2.3.5 | **Commit(s):** `feat(text-processing): composable pipeline library + CLI` | ⬜ |
| 2.3.6 | **Merge to main** → Tag `v0.7.0` → Update CHANGELOG | ⬜ |

#### Sprint 2.4: Contract + Load Tests Phase 2
**Branch:** `chore/contract-load-tests-phase2` (from `main`)

| Task | Description | Done |
|------|-------------|------|
| 2.4.1 | Pact tests for all Phase 2 contracts | ⬜ |
| 2.4.2 | k6 load tests for each service | ⬜ |
| 2.4.3 | CI integration for contract + load tests | ⬜ |
| 2.4.4 | **Commit(s):** `chore(test): add contract and load tests for phase 2` | ⬜ |
| 2.4.5 | **Merge to main** → Tag `v0.8.0` → Update CHANGELOG | ⬜ |

---

### PHASE 3: PREDICTABLE ORCHESTRATION (Weeks 11-16)

#### Sprint 3.1: Job Orchestrator Temporal Workflows
**Branch:** `feature/job-orchestrator-temporal` (from `main`)

| Task | Description | Done |
|------|-------------|------|
| 3.1.1 | Define Temporal workflows replacing `TranslationOrchestrator` | ⬜ |
| 3.1.2 | Activities: ExtractDocument, CreateCatalogEntries, BuildGlossary, TranslateChapters, GenerateAudio | ⬜ |
| 3.1.3 | Durable execution, retry policies, timeouts | ⬜ |
| 3.1.4 | Workflow replay tests (deterministic) | ⬜ |
| 3.1.5 | **Commit(s):** `feat(orchestrator): temporal workflows for translation jobs` | ⬜ |
| 3.1.6 | **Merge to main** → Tag `v0.9.0` → Update CHANGELOG | ⬜ |

#### Sprint 3.2: Audio Service Rust Pipeline
**Branch:** `feature/audio-service-rust-pipeline` (from `main`)

| Task | Description | Done |
|------|-------------|------|
| 3.2.1 | Extract TTS pipeline to Rust service | ⬜ |
| 3.2.2 | `TTSEngine` trait for pluggable backends | ⬜ |
| 3.2.3 | Pipeline stages: chunk → synthesize → merge → normalize (EBU R128) → encode | ⬜ |
| 3.2.4 | macOS `say` backend implementation | ⬜ |
| 3.2.5 | CLI: `cat text.txt \| pdftranslator-audio --voice paulina > audio.m4a` | ⬜ |
| 3.2.6 | **Commit(s):** `feat(audio): rust TTS pipeline with TTSEngine trait` | ⬜ |
| 3.2.7 | **Merge to main** → Tag `v0.10.0` → Update CHANGELOG | ⬜ |

#### Sprint 3.3: Event Bus Kafka + CloudEvents
**Branch:** `feature/event-bus-kafka-cloudevents` (from `main`)

| Task | Description | Done |
|------|-------------|------|
| 3.3.1 | Kafka cluster setup (local + CI) | ⬜ |
| 3.3.2 | Event publishing from all services | ⬜ |
| 3.3.3 | Consumer patterns for each service | ⬜ |
| 3.3.4 | Schema Registry integration | ⬜ |
| 3.3.5 | **Commit(s):** `feat(events): kafka + cloudevents integration` | ⬜ |
| 3.3.6 | **Merge to main** → Tag `v0.11.0` → Update CHANGELOG | ⬜ |

#### Sprint 3.4: Chaos Testing + Deterministic Replay
**Branch:** `chore/chaos-testing-deterministic-replay` (from `main`)

| Task | Description | Done |
|------|-------------|------|
| 3.4.1 | Chaos Mesh experiments: network partitions, pod kills, latency | ⬜ |
| 3.4.2 | Verify deterministic workflow replay | ⬜ |
| 3.4.3 | Failure mode documentation | ⬜ |
| 3.4.4 | **Commit(s):** `chore(test): chaos testing + replay validation` | ⬜ |
| 3.4.5 | **Merge to main** → Tag `v0.12.0` → Update CHANGELOG | ⬜ |

---

### PHASE 4: DOMAIN-FOCUSED CUTOVER (Weeks 17-22)

#### Sprint 4.1: API Gateway Kong Setup
**Branch:** `feature/api-gateway-kong-setup` (from `main`)

| Task | Description | Done |
|------|-------------|------|
| 4.1.1 | Kong deployment with declarative config | ⬜ |
| 4.1.2 | Routing rules for all services | ⬜ |
| 4.1.3 | Auth, rate limiting, timeout budgets | ⬜ |
| 4.1.4 | **Commit(s):** `feat(gateway): kong API gateway configuration` | ⬜ |
| 4.1.5 | **Merge to main** → Tag `v0.13.0` → Update CHANGELOG | ⬜ |

#### Sprint 4.2: Frontend → Gateway Migration
**Branch:** `feature/frontend-gateway-migration` (from `main`)

| Task | Description | Done |
|------|-------------|------|
| 4.2.1 | Angular services consume Gateway instead of direct backend | ⬜ |
| 4.2.2 | Feature flags for gradual migration | ⬜ |
| 4.2.3 | Dual-write period monitoring | ⬜ |
| 4.2.4 | **Commit(s):** `feat(frontend): migrate to API gateway` | ⬜ |
| 4.2.5 | **Merge to main** → Tag `v0.14.0` → Update CHANGELOG | ⬜ |

#### Sprint 4.3: Dual-Write Data Migration
**Branch:** `feature/dual-write-data-migration` (from `main`)

| Task | Description | Done |
|------|-------------|------|
| 4.3.1 | Migration scripts: SQLite → PostgreSQL per service | ⬜ |
| 4.3.2 | Data parity verification | ⬜ |
| 4.3.3 | Cutover plan with rollback | ⬜ |
| 4.3.4 | **Commit(s):** `feat(migration): dual-write data migration scripts` | ⬜ |
| 4.3.5 | **Merge to main** → Tag `v0.15.0` → Update CHANGELOG | ⬜ |

#### Sprint 4.4: SQLite Decommission + Dead Code Removal
**Branch:** `refactor/decommission-sqlite-monolith` (from `main`)

| Task | Description | Done |
|------|-------------|------|
| 4.4.1 | Remove old monolith code (`TranslationOrchestrator`, old repos, etc.) | ⬜ |
| 4.4.2 | Remove SQLite dependencies | ⬜ |
| 4.4.3 | Clean imports, unused code | ⬜ |
| 4.4.4 | **Commit(s):** `refactor: decommission sqlite monolith` | ⬜ |
| 4.4.5 | **Merge to main** → Tag `v0.16.0` → Update CHANGELOG | ⬜ |

#### Sprint 4.5: Integration Tests + Production Readiness
**Branch:** `chore/integration-tests-prod-readiness` (from `main`)

| Task | Description | Done |
|------|-------------|------|
| 4.5.1 | End-to-end integration tests | ⬜ |
| 4.5.2 | Runbooks for each service | ⬜ |
| 4.5.3 | Observability dashboards (Grafana) | ⬜ |
| 4.5.4 | Load testing full pipeline | ⬜ |
| 4.5.5 | **Commit(s):** `chore(prod): integration tests + runbooks + observability` | ⬜ |
| 4.5.6 | **Merge to main** → Tag `v1.0.0` → Update CHANGELOG | ⬜ |

---

## 🏷️ VERSION TIMELINE

| Version | Target Date | Phase | Key Milestone |
|---------|-------------|-------|---------------|
| v0.1.0  | Week 1      | Setup | Changelog + Conventions |
| v0.2.0  | Week 2      | 1.2   | Catalog Read API |
| v0.3.0  | Week 3      | 1.3   | Document CLI Extractor |
| v0.4.0  | Week 4      | 1.4   | Event Schemas |
| v0.5.0  | Week 6      | 2.1   | Glossary Pipeline HTTP |
| v0.6.0  | Week 7      | 2.2   | Translation Provider Pattern |
| v0.7.0  | Week 8      | 2.3   | Text Processing Lib + CLI |
| v0.8.0  | Week 9      | 2.4   | Contract + Load Tests |
| v0.9.0  | Week 12     | 3.1   | Temporal Workflows |
| v0.10.0 | Week 13     | 3.2   | Audio Service Rust |
| v0.11.0 | Week 14     | 3.3   | Kafka + CloudEvents |
| v0.12.0 | Week 15     | 3.4   | Chaos + Replay Tests |
| v0.13.0 | Week 17     | 4.1   | Kong Gateway |
| v0.14.0 | Week 18     | 4.2   | Frontend → Gateway |
| v0.15.0 | Week 19     | 4.3   | Data Migration |
| v0.16.0 | Week 20     | 4.4   | Monolith Decommission |
| **v1.0.0** | **Week 22** | **4.5** | **Production Ready** |

---

## 🔄 MANDATORY WORKFLOW PER SPRINT

```bash
# 1. START SPRINT - Always from updated main
git checkout main && git pull origin main
git checkout -b feature/your-descriptive-name

# 2. WORK - Atomic commits with conventional messages
git add -A
git commit -m "feat(scope): description of change"
# Repeat for each logical change

# 3. LOCAL VERIFICATION
pytest                    # All tests pass
ruff check .             # Linting passes
ruff format .            # Formatting passes

# 4. PREPARE MERGE
git checkout main && git pull origin main
git merge --squash feature/your-descriptive-name  # or rebase
# Resolve conflicts if any

# 5. FINAL VERIFICATION
pytest                    # All tests still pass

# 6. COMMIT MERGE + TAG + CHANGELOG
git commit -m "feat(scope): merge feature description"
./scripts/changelog-update.sh v0.X.Y
git add CHANGELOG.md
git commit -m "chore(changelog): update for v0.X.Y"
git tag -a v0.X.Y -m "Release v0.X.Y"

# 7. PUSH
git push origin main --tags
```

---

## ✅ CUPID COMPLIANCE CHECKLIST PER SERVICE

| Service | Composable | Unix Philosophy | Predictable | Idiomatic | Domain-Focused |
|---------|------------|-----------------|-------------|-----------|----------------|
| **Document** | ✅ JSON output | ✅ file → JSON | ✅ Deterministic | ✅ Python + Docling | ✅ Doc structure |
| **Catalog** | ✅ gRPC/REST/Events | ✅ CRUD only | ✅ ACID + explicit errors | ✅ Go + sqlc | ✅ Library hierarchy |
| **Glossary** | ✅ Pipeline stages | ✅ Stage = pure fn | ✅ Versioned embeddings | ✅ Python ML stack | ✅ Terminology |
| **Translation** | ✅ Provider + Glossary DI | ✅ Text in/out | ✅ Fixed chunking/retry | ✅ Protocol + asyncio | ✅ Context-aware |
| **Orchestrator** | ✅ Activity composition | ✅ Temporal = workflow as code | ✅ Deterministic replay | ✅ Go + Temporal SDK | ✅ Job lifecycle |
| **Audio** | ✅ Engine trait + formats | ✅ Pipeline stages | ✅ EBU R128 | ✅ Rust + symphonia | ✅ Audiobook gen |
| **Text Processing** | ✅ Fluent builder + CLI | ✅ Stdin/stdout | ✅ Pure functions | ✅ Python regex | ✅ Translation prep |

**Target: 35/35** — Every service satisfies all 5 CUPID principles

---

## 📁 FILES CREATED BY THIS PLAN

| File | Purpose |
|------|---------|
| `CHANGELOG.md` | Version history (Keep a Changelog) |
| `.gitmessage` | Conventional commit template |
| `commitlint.config.js` | Commit message validation |
| `scripts/changelog-update.sh` | Automated changelog generation |
| `docs/WORK_PLAN_CUPID.md` | This document |

---

## 🎯 SUCCESS CRITERIA

1. **All 22 sprints completed** with merge to main + tag + changelog
2. **35/35 CUPID compliance** across 7 services
3. **Zero downtime migration** from monolith to microservices
4. **Full test coverage**: Unit + Contract + Load + Chaos + E2E
5. **Production ready**: Runbooks, observability, rollback procedures
6. **Clean git history**: Linear, conventional commits, tagged releases

---

## 📝 NEXT STEPS

1. **Review this plan** with team
2. **Approve Sprint 1.1** (chore/setup-changelog-and-conventions)
3. **Begin execution** following mandatory workflow

---

*Document Version: 1.0*  
*Philosophy: CUPID — Composable, Unix Philosophy, Predictable, Idiomatic, Domain-Focused*  
*Author: Architecture Team*  
*Review Date: 2026-07-19*