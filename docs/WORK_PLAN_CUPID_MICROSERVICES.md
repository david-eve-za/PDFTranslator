# PDFTranslator - CUPID Microservices Migration Work Plan

**Based on:** `docs/MICROSERVICES_CUPID_PROPOSAL.md`  
**Date:** 2026-07-12  
**Version:** 1.0  
**Status:** Draft for Review  

---

## 🎯 Mandatory Working Rules (OBLIGATORIOS)

> **⚠️ ESTAS REGLAS SON OBLIGATORIAS Y NO NEGOCIABLES**

### 1. Branching Strategy - **Obligatorio**
```
MAIN BRANCH (main) → PROTECTED BRANCH
  └── feature/xxx-descriptive-name      ← New features/services
  └── refactor/xxx-descriptive-name     ← Refactoring existing code
  └── chore/xxx-descriptive-name        ← Maintenance, tooling, docs
  └── fix/xxx-descriptive-name          ← Bug fixes
```

**Rules:**
- ✅ **SIEMPRE** crear nueva rama desde `main` actualizado (`git checkout main && git pull && git checkout -b feature/nueva-funcionalidad`)
- ✅ **NUNCA** trabajar directamente en `main`
- ✅ Cada feature/refactor/fix = **UNA SOLA RAMA**
- ✅ Ramas descriptivas: `feature/catalog-service-read-api`, `refactor/extract-document-service`, `chore/setup-changelog`
- ✅ **Un commit = un cambio lógico atómico** (conventional commits)
- ✅ PR/MR obligatorio para merge a main (aunque sea auto-merge en local)

### 2. Merge Strategy - **Obligatorio**
```
Feature Branch → Local Review → Tests Pass → Merge to main → Tag version → Changelog update
```

**Merge Rules:**
- ✅ **Squash and merge** (preferible) o **Rebase and merge** - historia limpia
- ✅ **NUNCA** merge directo sin pasar tests
- ✅ Tag semver después de cada merge a main: `v0.2.0`, `v0.3.0`, etc.
- ✅ Actualizar CHANGELOG.md **inmediatamente después del merge**

### 3. Changelog - **Obligatorio**
- **Archivo:** `CHANGELOG.md` en raíz del proyecto (formato Keep a Changelog)
- **Actualización:** Inmediatamente después de cada merge a main
- **Formato:** Keep a Changelog 1.1.0 + SemVer 2.0.0
- **Rollback:** `git checkout v0.X.Y` para volver a versión funcional

---

## 📋 FASES DEL PLAN (Basado en CUPID Migration Strategy)

### FASE 1: COMPOSABLE EXTRACTION (Semanas 1-4)
**Objetivo CUPID:** Extraer servicios componibles, probar contracts

| Sprint | Tarea | Rama | Entregable | CUPID Gate |
|--------|-------|------|------------|------------|
| 1.1 | Setup: CHANGELOG.md, convenciones de commit, hooks | `chore/setup-changelog-and-conventions` | CHANGELOG.md, .gitmessage, commitlint config | ✅ Predictable |
| 1.2 | Catalog Service: Read-only API sobre SQLite existente | `feature/catalog-service-read-api` | REST/gRPC GET endpoints, contract tests (Pact) | ✅ Composable |
| 1.3 | Document Service: CLI `pdftranslator-extract file.pdf > out.json` | `feature/document-service-extract-cli` | CLI extractor, JSON output, tests | ✅ Unix Philosophy |
| 1.4 | Event Schemas: CloudEvents + Avro schemas + Schema Registry | `chore/event-schemas-cloud-events` | schemas/, schema registry config | ✅ Predictable |

### FASE 2: UNIX PIPELINE REPLACEMENT (Semanas 5-10)
**Objetivo CUPID:** Reemplazar pipeline in-process con servicios HTTP

| Sprint | Tarea | Rama | Entregable | CUPID Gate |
|--------|-------|------|------------|------------|
| 2.1 | Glossary Pipeline: HTTP service con stages independientes | `feature/glossary-pipeline-http-service` | Pipeline stages como microservicios, tests por stage | ✅ Composable + Unix |
| 2.2 | Translation Service: Extraer LLM orchestration + Provider pattern | `feature/translation-service-provider-pattern` | Provider protocol, retry policy, glossary client DI | ✅ Idiomatic + Predictable |
| 2.3 | Text Processing: Library + CLI filter (`cat | textproc | translate`) | `feature/text-processing-lib-cli` | Pure functions, fluent builder, CLI pipe | ✅ Unix + Composable |
| 2.4 | Contract Tests + Load Tests para todos servicios Fase 2 | `chore/contract-load-tests-phase2` | Pact tests passing, k6 load tests | ✅ All Gates |

### FASE 3: PREDICTABLE ORCHESTRATION (Semanas 11-16)
**Objetivo CUPID:** Temporal workflows reemplazan TranslationOrchestrator

| Sprint | Tarea | Rama | Entregable | CUPID Gate |
|--------|-------|------|------------|------------|
| 3.1 | Job Orchestrator: Temporal workflows + Activities | `feature/job-orchestrator-temporal` | Temporal workflows, durable execution, replay tests | ✅ Predictable |
| 3.2 | Audio Service: Extraer TTS pipeline a Rust/Go service | `feature/audio-service-rust-pipeline` | TTSEngine trait, pipeline stages, EBU R128 | ✅ Unix + Idiomatic |
| 3.3 | Event Bus: Kafka + CloudEvents integration | `feature/event-bus-kafka-cloudevents` | Event publishing/consuming, schema registry | ✅ Composable + Predictable |
| 3.4 | Chaos Testing + Deterministic Replay Validation | `chore/chaos-testing-deterministic-replay` | Chaos mesh tests, workflow replay verification | ✅ Predictable |

### FASE 4: DOMAIN-FOCUSED CUTOVER (Semanas 17-22)
**Objetivo CUPID:** Cutover completo, decomisionar monolito

| Sprint | Tarea | Rama | Entregable | CUPID Gate |
|--------|-------|------|------------|------------|
| 4.1 | API Gateway: Kong setup + routing rules | `feature/api-gateway-kong-setup` | Gateway routes, auth, rate limiting | ✅ Composable |
| 4.2 | Frontend → Gateway migration (dual-write period) | `feature/frontend-gateway-migration` | Angular consumes gateway, feature flags | ✅ Predictable |
| 4.3 | Dual-write → New services (data migration) | `feature/dual-write-data-migration` | Scripts migración, verificación paridad | ✅ Predictable |
| 4.4 | SQLite Decommission + Dead Code Removal | `refactor/decommission-sqlite-monolith` | Remove old code, clean imports | ✅ Unix Philosophy |
| 4.5 | Full Integration Tests + Production Readiness | `chore/integration-tests-prod-readiness` | E2E tests, runbooks, observability | ✅ All CUPID |

---

## 📦 DETAILED TASK BREAKDOWN PER SPRINT

### SPRINT 1.1: Setup Changelog & Conventions
**Branch:** `chore/setup-changelog-and-conventions` (from `main`)

```bash
# Comandos obligatorios
git checkout main && git pull origin main
git checkout -b chore/setup-changelog-and-conventions
```

**Tasks:**
- [ ] Crear `CHANGELOG.md` (formato Keep a Changelog)
- [ ] Configurar `.gitmessage` template (Conventional Commits)
- [ ] Setup `commitlint` + `husky` pre-commit hooks
- [ ] Documentar convenciones en `CONTRIBUTING.md`
- [ ] Crear script `scripts/changelog-update.sh` para automatizar
- [ ] **Commit:** `chore: add changelog and commit conventions`
- [ ] **Merge a main** → Tag `v0.1.0` → Actualizar CHANGELOG

---

### SPRINT 1.2: Catalog Service Read-Only API
**Branch:** `feature/catalog-service-read-api` (from `main`)

```bash
git checkout main && git pull origin main
git checkout -b feature/catalog-service-read-api
```

**Tasks:**
- [ ] Diseñar API contract (OpenAPI) para Works, Volumes, Chapters
- [ ] Implementar REST endpoints GET en FastAPI (reutilizar repos existing)
- [ ] Pact contract tests contra Angular frontend
- [ ] Verificar: Angular UI consume API sin cambios visuales
- [ ] **Commit(s):** feat(catalog): add read-only REST API
- [ ] **Merge a main** → Tag `v0.2.0` → CHANGELOG

---

### SPRINT 1.3: Document Service CLI Extractor
**Branch:** `feature/document-service-extract-cli` (from `main`)

```bash
git checkout main && git pull origin main
git checkout -b feature/document-service-extract-cli
```

**Tasks:**
- [ ] Extraer `DoclingExtractor` a servicio independiente
- [ ] CLI `pdftranslator-extract file.pdf --format json > out.json`
- [ ] Output: `ExtractedDocument` JSON (Pydantic models)
- [ ] Tests: determinismo (mismo PDF = mismo JSON)
- [ ] **Commit(s):** feat(document): add CLI extractor with JSON output
- [ ] **Merge a main** → Tag `v0.3.0` → CHANGELOG

---

### SPRINT 1.4: Event Schemas (CloudEvents + Avro)
**Branch:** `chore/event-schemas-cloud-events` (from `main`)

```bash
git checkout main && git pull origin main
git checkout -b chore/event-schemas-cloud-events
```

**Tasks:**
- [ ] Definir schemas Avro para: `WorkCreated`, `DocumentExtracted`, `GlossaryBuilt`, `TranslationCompleted`
- [ ] Configurar Schema Registry (Confluent/Apicurio)
- [ ] Generar clientes Python/Go/TypeScript desde schemas
- [ ] Documentar versioning strategy
- [ ] **Commit(s):** chore(events): add CloudEvents + Avro schemas
- [ ] **Merge a main** → Tag `v0.4.0` → CHANGELOG

---

### SPRINT 2.1: Glossary Pipeline HTTP Service
**Branch:** `feature/glossary-pipeline-http-service` (from `main`)

```bash
git checkout main && git pull origin main
git checkout -b feature/glossary-pipeline-http-service
```

**Tasks:**
- [ ] Decomponer `GlossaryPipeline` en stages: Extract → Validate → Translate → Embed → Store
- [ ] Cada stage = endpoint HTTP independiente (o gRPC)
- [ ] Pipeline orchestrator llama stages en secuencia
- [ ] Tests unitarios por stage + integration test pipeline completo
- [ ] **Commit(s):** feat(glossary): extract pipeline stages as HTTP services
- [ ] **Merge a main** → Tag `v0.5.0` → CHANGELOG

---

### SPRINT 2.2: Translation Service Provider Pattern
**Branch:** `feature/translation-service-provider-pattern` (from `main`)

```bash
git checkout main && git pull origin main
git checkout -b feature/translation-service-provider-pattern
```

**Tasks:**
- [ ] Extraer `TranslationOrchestrator` → `TranslationService`
- [ ] Implementar `LLMProvider` Protocol (NVIDIA, Gemini, Ollama)
- [ ] `ProviderFactory` para selección dinámica
- [ ] `RetryPolicy` configurable (Predictable)
- [ ] `GlossaryClient` inyectado (Composable, no hardcoded)
- [ ] Deterministic `TextChunker` extraído
- [ ] **Commit(s):** feat(translation): provider pattern + deterministic chunking
- [ ] **Merge a main** → Tag `v0.6.0` → CHANGELOG

---

### SPRINT 2.3: Text Processing Library + CLI
**Branch:** `feature/text-processing-lib-cli` (from `main`)

```bash
git checkout main && git pull origin main
git checkout -b feature/text-processing-lib-cli
```

**Tasks:**
- [ ] Crear `TextPipeline` con fluent builder
- [ ] Steps: substitutions, overlap cleaner, normalizer
- [ ] CLI: `cat input.txt | python -m text_processing --normalize > output.txt`
- [ ] Tests: pure functions, property-based testing
- [ ] **Commit(s):** feat(text-processing): composable pipeline library + CLI
- [ ] **Merge a main** → Tag `v0.7.0` → CHANGELOG

---

### SPRINT 2.4: Contract + Load Tests Phase 2
**Branch:** `chore/contract-load-tests-phase2` (from `main`)

```bash
git checkout main && git pull origin main
git checkout -b chore/contract-load-tests-phase2
```

**Tasks:**
- [ ] Pact tests para todos los contratos Fase 2
- [ ] k6 load tests: p99 < budget por servicio
- [ ] CI pipeline: contract test → load test → deploy
- [ ] **Commit(s):** chore(test): add contract and load tests for phase 2
- [ ] **Merge a main** → Tag `v0.8.0` → CHANGELOG

---

### SPRINT 3.1: Job Orchestrator Temporal
**Branch:** `feature/job-orchestrator-temporal` (from `main`)

```bash
git checkout main && git pull origin main
git checkout -b feature/job-orchestrator-temporal
```

**Tasks:**
- [ ] Setup Temporal cluster (dev)
- [ ] Migrar `TranslationWorkflow` a Temporal Go SDK
- [ ] Activities: Extract, Catalog, Glossary, Translate, Audio
- [ ] Retry policies, timeouts, heartbeats configurables
- [ ] Test: Workflow replay produce resultados idénticos
- [ ] **Commit(s):** feat(orchestrator): temporal workflows for translation jobs
- [ ] **Merge a main** → Tag `v0.9.0` → CHANGELOG

---

### SPRINT 3.2: Audio Service Rust Pipeline
**Branch:** `feature/audio-service-rust-pipeline` (from `main`)

```bash
git checkout main && git pull origin main
git checkout -b feature/audio-service-rust-pipeline
```

**Tasks:**
- [ ] Crear crate Rust `audio-service`
- [ ] `TTSEngine` trait: macOS `say`, Piper, Coqui backends
- [ ] Pipeline: chunk → TTS → merge → normalize (EBU R128) → encode
- [ ] CLI: `cat text.txt | audio-service --voice paulina > book.m4a`
- [ ] gRPC service para Job Orchestrator
- [ ] **Commit(s):** feat(audio): rust TTS pipeline with EBU R128
- [ ] **Merge a main** → Tag `v0.10.0` → CHANGELOG

---

### SPRINT 3.3: Event Bus Kafka + CloudEvents
**Branch:** `feature/event-bus-kafka-cloudevents` (from `main`)

```bash
git checkout main && git pull origin main
git checkout -b feature/event-bus-kafka-cloudevents
```

**Tasks:**
- [ ] Kafka cluster setup (Strimzi/KRaft)
- [ ] Producers: Catalog, Document, Glossary, Translation, Audio services
- [ ] Consumers: Job Orchestrator, Analytics, Notifications
- [ ] Schema Registry integration (Avro serialization)
- [ ] Dead letter queues, retry topics
- [ ] **Commit(s):** feat(events): kafka + cloudevents integration
- [ ] **Merge a main** → Tag `v0.11.0` → CHANGELOG

---

### SPRINT 3.4: Chaos Testing + Deterministic Replay
**Branch:** `chore/chaos-testing-deterministic-replay` (from `main`)

```bash
git checkout main && git pull origin main
git checkout -b chore/chaos-testing-deterministic-replay
```

**Tasks:**
- [ ] Chaos Mesh: pod kill, network partition, latency injection
- [ ] Verificar: workflow replay = resultados idénticos
- [ ] Test: servicio caído → recover sin pérdida datos
- [ ] Documentar runbooks de failure scenarios
- [ ] **Commit(s):** chore(test): chaos testing + deterministic replay validation
- [ ] **Merge a main** → Tag `v0.12.0` → CHANGELOG

---

### SPRINT 4.1: API Gateway Kong Setup
**Branch:** `feature/api-gateway-kong-setup` (from `main`)

```bash
git checkout main && git pull origin main
git checkout -b feature/api-gateway-kong-setup
```

**Tasks:**
- [ ] Kong deployment (DB-less mode + declarative config)
- [ ] Routes: `/api/catalog`, `/api/document`, `/api/glossary`, `/api/translation`, `/api/audio`
- [ ] Auth: JWT validation, API keys
- [ ] Rate limiting, timeout budgets
- [ ] Observability: Prometheus metrics, Jaeger tracing
- [ ] **Commit(s):** feat(gateway): kong API gateway with routing + auth
- [ ] **Merge a main** → Tag `v0.13.0` → CHANGELOG

---

### SPRINT 4.2: Frontend Gateway Migration
**Branch:** `feature/frontend-gateway-migration` (from `main`)

```bash
git checkout main && git pull origin main
git checkout -b feature/frontend-gateway-migration
```

**Tasks:**
- [ ] Angular service layer → Gateway URLs
- [ ] Feature flags para dual-write period
- [ ] E2E tests contra gateway
- [ ] Rollback plan documentado
- [ ] **Commit(s):** feat(frontend): migrate to API gateway with feature flags
- [ ] **Merge a main** → Tag `v0.14.0` → CHANGELOG

---

### SPRINT 4.3: Dual-Write Data Migration
**Branch:** `feature/dual-write-data-migration` (from `main`)

```bash
git checkout main && git pull origin main
git checkout -b feature/dual-write-data-migration
```

**Tasks:**
- [ ] Scripts migración SQLite → PostgreSQL por servicio
- [ ] Dual-write: writes van a ambos, reads de nuevo
- [ ] Verificación paridad: count, checksums, sampling
- [ ] Cutover plan con rollback
- [ ] **Commit(s):** feat(migration): dual-write SQLite to PostgreSQL
- [ ] **Merge a main** → Tag `v0.15.0` → CHANGELOG

---

### SPRINT 4.4: SQLite Decommission + Dead Code Removal
**Branch:** `refactor/decommission-sqlite-monolith` (from `main`)

```bash
git checkout main && git pull origin main
git checkout -b refactor/decommission-sqlite-monolith
```

**Tasks:**
- [ ] Eliminar `TranslationOrchestrator`, `process_single_file()`, monolito code
- [ ] Limpiar imports, repos inutilizados, settings singleton
- [ ] Tests: full suite pasa sin código monolito
- [ ] Documentar arquitectura final
- [ ] **Commit(s):** refactor: remove monolith code after migration
- [ ] **Merge a main** → Tag `v1.0.0` → CHANGELOG

---

### SPRINT 4.5: Integration Tests + Production Readiness
**Branch:** `chore/integration-tests-prod-readiness` (from `main`)

```bash
git checkout main && git pull origin main
git checkout -b chore/integration-tests-prod-readiness
```

**Tasks:**
- [ ] E2E tests: PDF → Audiobook completo
- [ ] Runbooks: deploy, rollback, scaling, debugging
- [ ] Observability dashboards: Grafana, alertas
- [ ] Load test: 100 concurrent translations
- [ ] Security audit: secrets, network policies
- [ ] **Commit(s):** chore: integration tests + production runbooks
- [ ] **Merge a main** → Tag `v1.1.0` → CHANGELOG

---

## 🔄 WORKFLOW OBLIGATORIO POR TAREA

```bash
# 1. ANTES DE EMPEZAR CUALQUIER TAREA
git checkout main
git pull origin main
git checkout -b <tipo>/<descripcion-corta-kebab-case>

# 2. DESARROLLO (commits atómicos, conventional commits)
git add -p
git commit -m "feat(catálogo): add read-only GET /works endpoint"

# 3. TESTS LOCALES
pytest -xvs
# o cargo test / go test ./...

# 4. PUSH Y PR (aunque sea local)
git push origin <rama>

# 5. REVIEW LOCAL (self-review checklist)
# - [ ] Tests pasan
# - [ ] Lint pasa
# - [ ] Changelog actualizado (draft en rama)
# - [ ] Docs actualizadas si aplica

# 6. MERGE A MAIN (squash preferiblemente)
git checkout main
git pull origin main
git merge --squash <rama>
git commit -m "feat(catalog): add read-only GET /works endpoint

Closes #123"

# 7. TAG VERSION + CHANGELOG
git tag -a v0.X.Y -m "v0.X.Y: feat(catalog): read-only API"
git push origin main --tags

# 8. ACTUALIZAR CHANGELOG.MD (inmediatamente)
# Editar CHANGELOG.md sección [Unreleased] → mover a versión nueva

# 9. LIMPIAR RAMA
git branch -d <rama>
git push origin --delete <rama>
```

---

## 📝 CHANGELOG.MD TEMPLATE (Keep a Changelog)

```markdown
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- 

### Changed
- 

### Deprecated
- 

### Removed
- 

### Fixed
- 

### Security
- 

---

## [1.1.0] - 2026-XX-XX

### Added
- Integration tests for full PDF → Audiobook pipeline
- Production runbooks (deploy, rollback, scaling)
- Grafana dashboards and alerting rules

### Changed
- 

### Fixed
- 

---

## [1.0.0] - 2026-XX-XX

### Added
- Full microservices architecture (7 services)
- Temporal workflow orchestration
- Kafka + CloudEvents event bus
- Kong API Gateway with auth/rate-limiting

### Removed
- Monolithic TranslationOrchestrator
- SQLite single database
- In-process glossary/translation coupling

### Fixed
- Deterministic workflow replay verified

---

## [0.15.0] - 2026-XX-XX

### Added
- Dual-write migration SQLite → PostgreSQL
- Data parity verification scripts

### Changed
- All services read from PostgreSQL

---

## [0.14.0] - 2026-XX-XX

### Added
- Angular frontend migrated to API Gateway
- Feature flags for gradual rollout

...

## [0.1.0] - 2026-07-12

### Added
- Initial changelog and commit conventions
- Conventional commits + commitlint + husky setup
```

---

## ✅ CHECKLIST DE VALIDACIÓN POR SPRINT

### Antes de Merge (Definition of Done)
- [ ] Tests unitarios pasan (>80% coverage)
- [ ] Tests de integración pasan
- [ ] Contract tests (Pact) pasan
- [ ] Lint/format pasa (ruff, gofmt, clippy, eslint)
- [ ] Security scan pasa (trivy, bandit, gosec)
- [ ] CHANGELOG.md actualizado en la rama
- [ ] Documentación actualizada (README, API docs, runbooks)
- [ ] No breaking changes sin version major bump

### CUPID Gates (por fase)
| Gate | Verificación |
|------|--------------|
| **Composable** | Pact tests pass; consumers can mock independently |
| **Unix Philosophy** | CLI works in pipes: `cat \| service \| service > out` |
| **Predictable** | Schema versioned; retry policy fixed; replay = same result |
| **Idiomatic** | Code follows language conventions (go vet, clippy, ruff) |
| **Domain-Focused** | Domain models have behavior, not just data |

---

## 🚨 ROLLBACK PROCEDURE

```bash
# 1. Identificar último tag funcional
git tag -l "v*" --sort=-v:refname | head -10

# 2. Verificar CHANGELOG para entender qué cambió
cat CHANGELOG.md | head -100

# 3. Rollback a versión específica
git checkout v0.12.0  # Ejemplo: v0.12.0 fue último estable

# 4. Crear rama de hotfix si necesario
git checkout -b hotfix/rollback-v0.12.0

# 5. Deploy desde tag
# kubectl set image deployment/...=image:v0.12.0
```

---

## 📌 PRÓXIMOS PASOS INMEDIATOS

1. **Aprobar este plan** → Usuario confirma o solicita cambios
2. **Ejecutar Sprint 1.1** → Setup CHANGELOG + convenciones (base obligatoria)
3. **Kickoff Event Storming** (CUPID Next Step #1) → Descubrir bounded contexts reales
4. **Iniciar Sprint 1.2** → Catalog Service Read-Only API

---

## 📎 REFERENCIAS

- **Propuesta CUPID:** `docs/MICROSERVICES_CUPID_PROPOSAL.md`
- **Convenciones:** [Conventional Commits 1.0.0](https://www.conventionalcommits.org/)
- **Changelog:** [Keep a Changelog 1.1.0](https://keepachangelog.com/)
- **SemVer:** [Semantic Versioning 2.0.0](https://semver.org/)
- **Pact:** [Contract Testing](https://docs.pact.io/)
- **Temporal:** [Go SDK](https://docs.temporal.io/dev-guide/go/)
- **CloudEvents:** [Spec 1.0](https://github.com/cloudevents/spec)