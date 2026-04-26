# TranslateComponent Refactor Design

## Overview

Refactor the frontend `TranslateComponent` to follow the same concepts as the CLI `translate` command. The current component simulates translation with fake progress and file upload. The refactored component will use works from the database, support scope selection (All Book / All Volume / Single Chapter), integrate glossary-aware translation, and display real-time progress via SSE.

## Current State

### TranslateComponent (frontend)
- Uploads a PDF/EPUB file via `FileUploadComponent`
- Simulates translation with `setInterval` fake progress
- Returns a mock download URL (`mock://download/translated-document.pdf`)
- No database interaction (works, volumes, chapters)
- No glossary integration
- No scope selection
- Uses `LanguageSelectorComponent` and `TranslationConfigService` for languages/providers

### CLI `translate` command
- Selects a Work from the database
- Displays work structure (volumes, chapters, translation status)
- Supports 3 scopes: All Book, All Volume, Single Chapter
- Loads glossary entries for the work
- Uses `GlossaryAwareTranslator` with post-processing
- Saves translations to database (`chapter.translated_text`)
- Shows summary with success/failure counts
- Supports `--dry-run` and `--skip-translated` flags

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Data source | Works from DB only | Matches CLI flow; works are already imported via Split |
| Execution model | SSE (Server-Sent Events) | Real-time progress without polling complexity |
| Architecture | Single component | Same approach as CLI (single file), simpler to implement |
| Glossary | Automatic, same as CLI | Load from work, no manual selection needed |
| Skip translated | Toggle, default on | Matches CLI `--skip-translated` behavior |
| Languages | From Work entity | `work.source_lang` / `work.target_lang`, same as CLI fallback |

## User Flow

```
IDLE
  → [Select Work from list]
WORK_SELECTED (shows structure: volumes, chapters, translation status)
  → [Choose Scope: All Book / All Volume / Single Chapter]
SCOPE_SELECTED
  → If "All Volume": select volume
  → If "Single Chapter": select volume → select chapter
READY (Start Translation button enabled)
  → [Click Start Translation]
TRANSLATING (SSE real-time progress)
  → Translation completes
COMPLETED (summary: success/failure/skipped, link to Library)
  or
ERROR (error message, retry option)
```

## Component Signals

```typescript
// Step control
step: signal<'select-work' | 'select-scope' | 'select-target' | 'ready' | 'translating' | 'completed' | 'error'>

// Selections
selectedWork: signal<Work | null>
selectedScope: signal<'all_book' | 'all_volume' | 'single_chapter' | null>
selectedVolume: signal<Volume | null>
selectedChapter: signal<Chapter | null>
skipTranslated: signal<boolean> (default: true)

// Translation progress (from SSE)
progressData: signal<{
  currentChapter: string;
  completedCount: number;
  totalCount: number;
  chapterStatuses: Array<{id: number; title: string; status: 'translating' | 'completed' | 'skipped' | 'error'}>;
}>()

// Summary
translationSummary: signal<{success: number; failure: number; skipped: number} | null>
```

## Backend Changes

### New Endpoint: POST /api/translate/start

Request body:
```json
{
  "work_id": 1,
  "scope": "all_book" | "all_volume" | "single_chapter",
  "volume_id": null,
  "chapter_id": null,
  "source_lang": "en",
  "target_lang": "es",
  "skip_translated": true
}
```

Response: SSE stream (`text/event-stream`)

SSE events:
- `event: progress` → `{chapter_id, chapter_title, status: "translating"|"completed"|"skipped"|"error", completed, total}`
- `event: summary` → `{success_count, failure_count, skipped_count}`
- `event: error` → `{message}`
- `event: done` → stream closure

### Shared Translation Service

Move translation orchestration logic from CLI to a shared service:

**File**: `src/pdftranslator/services/translation_orchestrator.py`

Contents:
- `translate_chapter()` — translate a single chapter
- `translate_volume()` — translate all chapters in a volume
- `translate_book()` — translate all volumes in a work
- Each method accepts a **progress callback** (`on_progress(status)`) that:
  - CLI uses to update Rich progress bars
  - Backend uses to emit SSE events
- Reuse `GlossaryAwareTranslator` class (already in `translate_chapter.py`)

The CLI `translate_chapter.py` will import from this shared service instead of having inline logic.

### Schemas

New Pydantic schemas in `schemas.py`:
- `TranslationStartRequest` — request body for `/api/translate/start`

## Frontend Changes

### New Service: TranslationService

**File**: `src/app/core/services/translation.service.ts`

```typescript
@Injectable({ providedIn: 'root' })
export class TranslationService {
  startTranslation(request: TranslationStartRequest): Observable<TranslationProgressEvent> {
    // POST to /api/translate/start
    // Parse SSE stream
    // Emit events as Observable
  }
}
```

### TranslateComponent Refactor

**Remove**:
- `FileUploadComponent` import and usage
- `LanguageSelectorComponent` import and usage
- `TranslationConfigService` dependency
- `simulateProcessing()` and fake progress logic
- `downloadUrl` signal and `downloadResult()` method
- `selectedFile`, `sourceLanguage`, `targetLanguage`, `selectedProvider` signals
- `swapLanguages()`, `onFileSelected()`, `onProviderChange()` methods

**Add**:
- `WorkService` injection for loading works
- `VolumeService` injection for loading volumes
- `TranslationService` injection for SSE translation
- Step-based UI flow (select-work → select-scope → select-target → ready → translating → completed)
- Work structure display (volumes with chapter status)
- Scope selection (All Book / All Volume / Single Chapter)
- Volume/chapter dropdowns
- Skip translated toggle
- Real-time progress from SSE
- Translation summary display
- Message handling pattern per AGENTS.md (`showSuccess`/`showError` with `OnDestroy`)

### Template Structure

```
Step 1: Select Work
  - Card/list of works (title, author, # volumes, translation progress)
  - On select: load work structure

Step 2: Select Scope
  - 3 option cards: All Book, All Volume, Single Chapter
  - Work structure display (volumes + chapters with status)
  - If All Volume: volume dropdown
  - If Single Chapter: volume → chapter dropdown
  - Skip translated toggle
  - Language display (from work: source_lang → target_lang)

Step 3: Translating
  - Progress bar with current chapter
  - Chapter list with status icons (✓ ○ ✗)
  - Counter: X/Y chapters completed

Step 4: Completed
  - Summary: success, failure, skipped counts
  - "Go to Library" button
  - "Translate Again" button
```

## Error Handling

| Case | Behavior |
|------|----------|
| Work has no volumes | Show "No volumes found" + link to Split |
| Work has no glossary | Show warning "Consider running build-glossary" + allow translation |
| Work has no chapters | Show "No chapters available to translate" |
| Chapter has no original text | Auto-skip with visual indicator (same as CLI) |
| Translation chunk error | Mark chapter as error, continue with others (same as CLI) |
| SSE disconnect | Show error with retry option |
| SSE timeout (5 min no events) | Show timeout with retry option |

All message displays follow AGENTS.md pattern: `showSuccess`/`showError` with `clearMessageTimeout`, component implements `OnDestroy`.

## Files to Change

### Backend
1. `src/pdftranslator/services/translation_orchestrator.py` — **NEW**: shared translation logic
2. `src/pdftranslator/backend/api/routes/translation.py` — **MODIFY**: add `POST /api/translate/start` with SSE
3. `src/pdftranslator/backend/api/models/schemas.py` — **MODIFY**: add `TranslationStartRequest`
4. `src/pdftranslator/cli/commands/translate_chapter.py` — **MODIFY**: import from shared service

### Frontend
5. `src/app/core/services/translation.service.ts` — **NEW**: SSE client service
6. `src/app/core/models/translation-progress.model.ts` — **MODIFY**: align types with SSE events
7. `src/app/features/translate/translate.component.ts` — **REWRITE**: full refactor
8. `src/app/features/translate/translate.component.html` — **REWRITE**: new template
9. `src/app/features/translate/translate.component.scss` — **MODIFY**: update styles for new UI
