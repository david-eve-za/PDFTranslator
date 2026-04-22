# Design: Remove Language Selection from Files Component

**Date:** 2025-04-12
**Status:** Approved
**Scope:** Frontend + Backend

## Goal

Eliminate duplication of language selection between FilesComponent and TranslateComponent. Languages will only be configured in the Translate component, simplifying the upload flow and improving UX.

## Background

Currently, both FilesComponent and TranslateComponent have language selection UI:
- FilesComponent: Inline selects for source/target language (lines 40-63 in template)
- TranslateComponent: Uses LanguageSelectorComponent with swap functionality

This creates confusion and duplication. The user must select languages twice for the same workflow.

## Decision

Remove language selection completely from FilesComponent and the upload flow. Languages will be configured only in:
- TranslateComponent (for ad-hoc translations)
- Work entity (for persistent configuration)

## Architecture Changes

### Frontend

#### FilesComponent (`src/pdftranslator/frontend/src/app/features/files/files.component.ts`)
- Remove `uploadConfig: FileUploadQuery` property (line 64-67)
- Simplify `uploadFile()` to call service without language params

#### FilesComponent Template (`files.component.html`)
- Remove `<div class="upload-config">` block (lines 40-63)

#### FileService (`src/pdftranslator/frontend/src/app/core/services/file.service.ts`)
- Make `query` parameter optional with default `{}`
- Keep query param logic for backward compatibility

### Backend

#### Files API Route (`src/pdftranslator/backend/api/routes/files.py`)
- Make `source_lang` and `target_lang` query params optional (default `None`)
- Don't pass language params to service if not provided

#### FileService (`src/pdftranslator/backend/services/file_service.py`)
- Make `source_lang` and `target_lang` optional in `save_upload_file()`
- Don't assign to UploadedFile if not provided

#### UploadedFile Model (`src/pdftranslator/database/models.py`)
- Remove `source_lang` and `target_lang` fields from dataclass

#### UploadedFileRepository (`src/pdftranslator/database/repositories/uploaded_file_repository.py`)
- Remove `source_lang` and `target_lang` from all SQL queries
- Adjust tuple indices in result mapping

### Database

#### Migration
```sql
-- Drop language columns from uploaded_files table
ALTER TABLE uploaded_files DROP COLUMN IF EXISTS source_lang;
ALTER TABLE uploaded_files DROP COLUMN IF EXISTS target_lang;
```

## Data Flow

### Before
```
User uploads file → Select languages → File uploaded with language metadata → Work created
```

### After
```
User uploads file → File uploaded (no language) → Work created with default languages
User translates → Select languages in Translate → Translation starts
```

## Impact Analysis

### Files Changed
| File | Change Type |
|------|-------------|
| `files.component.ts` | Modified |
| `files.component.html` | Modified |
| `files.component.scss` | Modified (remove styles for upload-config) |
| `file.service.ts` | Modified |
| `file.model.ts` | No change (already optional) |
| `files.py` (backend) | Modified |
| `file_service.py` (backend) | Modified |
| `models.py` | Modified |
| `uploaded_file_repository.py` | Modified |

### Tests Updated
| Test File | Action |
|-----------|--------|
| `tests/backend/test_files.py` | Remove language param tests |
| `tests/database/test_uploaded_file_repository.py` | Update model tests |

## Deployment Strategy

1. Deploy backend changes (backward compatible - optional params)
2. Deploy frontend changes
3. Run database migration (drop columns)
4. Verify functionality

## Risks

| Risk | Mitigation |
|------|------------|
| Existing uploads with language data | Data loss acceptable - languages are reconfigured in Work |
| API breaking changes | Make params optional, maintain defaults |

## Success Criteria

- [ ] FilesComponent has no language selectors
- [ ] Upload works without language params
- [ ] TranslateComponent language selection works
- [ ] All tests pass
- [ ] Database migration successful
