# Remove Language Selection from Files Component Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Remove language selection from FilesComponent and backend upload flow to eliminate duplication with TranslateComponent.

**Architecture:** Remove source_lang and target_lang from the upload flow. Languages will only be configured in TranslateComponent and stored in Work entity. Frontend removes upload config UI, backend makes language params optional, database removes columns.

**Tech Stack:** Angular 19 (frontend), FastAPI (backend), PostgreSQL, Python 3.11

---

## Task 1: Remove Language Selection UI from FilesComponent

**Files:**
- Modify: `src/pdftranslator/frontend/src/app/features/files/files.component.html`
- Modify: `src/pdftranslator/frontend/src/app/features/files/files.component.ts`

**Step 1: Remove language selectors from template**

Remove lines 40-63 in `files.component.html`:

```html
<!-- DELETE THIS ENTIRE BLOCK -->
<div class="upload-config">
  <div class="config-field">
    <label for="source-lang">Source Language</label>
    <select id="source-lang" [(ngModel)]="uploadConfig.source_lang">
      <option value="en">English</option>
      <option value="es">Spanish</option>
      <option value="fr">French</option>
      <option value="de">German</option>
      <option value="ja">Japanese</option>
      <option value="zh">Chinese</option>
    </select>
  </div>
  <div class="config-field">
    <label for="target-lang">Target Language</label>
    <select id="target-lang" [(ngModel)]="uploadConfig.target_lang">
      <option value="en">English</option>
      <option value="es">Spanish</option>
      <option value="fr">French</option>
      <option value="de">German</option>
      <option value="ja">Japanese</option>
      <option value="zh">Chinese</option>
    </select>
  </div>
</div>
```

**Step 2: Remove uploadConfig property from component**

In `files.component.ts`, remove:

```typescript
// DELETE THIS
uploadConfig: FileUploadQuery = {
  source_lang: 'en',
  target_lang: 'es',
};
```

Also remove the `FileUploadQuery` import if no longer needed:

```typescript
// Remove from imports if not used elsewhere
import {
  FileUploadResponse,
  FileUploadQuery,  // REMOVE THIS
  FileStatus,
  ...
}
```

**Step 3: Update uploadFile call**

In `files.component.ts`, modify the `uploadFile` method (around line 144):

```typescript
// BEFORE:
this.fileService.uploadFile(file, this.uploadConfig, (progress) => {

// AFTER:
this.fileService.uploadFile(file, undefined, (progress) => {
```

Or simpler:

```typescript
this.fileService.uploadFile(file, {}, (progress) => {
```

**Step 4: Remove FormsModule import if not needed**

Check if `FormsModule` is still needed (for other `ngModel` usage). If not, remove from imports:

```typescript
// If no other ngModel usage, remove FormsModule
imports: [CommonModule, RouterModule],  // Remove FormsModule
```

**Step 5: Verify component compiles**

```bash
cd /Volumes/Elements2/PycharmProjects/PDFTranslator/src/pdftranslator/frontend
npm run build 2>&1 | head -50
```

Expected: Build succeeds or shows only unrelated errors.

**Step 6: Commit frontend changes**

```bash
git add src/pdftranslator/frontend/src/app/features/files/files.component.html
git add src/pdftranslator/frontend/src/app/features/files/files.component.ts
git commit -m "feat(frontend): remove language selection from FilesComponent"
```

---

## Task 2: Update FileService to Make Language Params Optional

**Files:**
- Modify: `src/pdftranslator/frontend/src/app/core/services/file.service.ts`

**Step 1: Make query parameter optional**

In `file.service.ts`, update the `uploadFile` method signature (around line 24):

```typescript
// BEFORE:
uploadFile(
  file: File,
  query: FileUploadQuery = {},
  progressCallback?: (progress: UploadProgress) => void
): Observable<FileUploadResponse> {

// AFTER: (no change needed, already has default)
// Keep as is - the default {} already makes it optional
```

No changes needed here - the default value already makes it optional.

**Step 2: Verify FileUploadQuery is optional in model**

Check `src/pdftranslator/frontend/src/app/core/models/file.model.ts`:

```typescript
export interface FileUploadQuery {
  source_lang?: string;  // Already optional with ?
  target_lang?: string;  // Already optional with ?
}
```

No changes needed - already optional.

**Step 3: Commit (if any changes made)**

```bash
git status
# If changes made:
git add src/pdftranslator/frontend/src/app/core/services/file.service.ts
git commit -m "refactor(frontend): make FileUploadQuery optional in FileService"
```

---

## Task 3: Update Backend Files API Route

**Files:**
- Modify: `src/pdftranslator/backend/api/routes/files.py`

**Step 1: Make language params optional**

In `files.py`, update the `upload_file` endpoint (around line 56-63):

```python
# BEFORE:
@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    file: Annotated[UploadFile, File()],
    source_lang: str = Query(default="en", description="Source language code"),
    target_lang: str = Query(default="es", description="Target language code"),
    service: FileService = Depends(get_file_service),
):

# AFTER:
from typing import Optional

@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    file: Annotated[UploadFile, File()],
    source_lang: Optional[str] = Query(default=None, description="Source language code (optional)"),
    target_lang: Optional[str] = Query(default=None, description="Target language code (optional)"),
    service: FileService = Depends(get_file_service),
):
```

**Step 2: Update service call to handle None**

```python
# BEFORE (around line 81-87):
uploaded_file = await service.save_upload_file(
    file_content=file_content,
    original_filename=file.filename,
    content_type=file.content_type,
    source_lang=source_lang,
    target_lang=target_lang,
)

# AFTER:
uploaded_file = await service.save_upload_file(
    file_content=file_content,
    original_filename=file.filename,
    content_type=file.content_type,
    source_lang=source_lang,  # Pass None if not provided
    target_lang=target_lang,
)
```

**Step 3: Commit backend API changes**

```bash
git add src/pdftranslator/backend/api/routes/files.py
git commit -m "refactor(backend): make language params optional in files upload endpoint"
```

---

## Task 4: Update Backend FileService

**Files:**
- Modify: `src/pdftranslator/backend/services/file_service.py`

**Step 1: Make language params optional**

In `file_service.py`, update `save_upload_file` method (around line 99-106):

```python
# BEFORE:
async def save_upload_file(
    self,
    file_content: bytes,
    original_filename: str,
    content_type: str | None,
    source_lang: str = "en",
    target_lang: str = "es",
) -> UploadedFile:

# AFTER:
async def save_upload_file(
    self,
    file_content: bytes,
    original_filename: str,
    content_type: str | None,
    source_lang: str | None = None,
    target_lang: str | None = None,
) -> UploadedFile:
```

**Step 2: Update UploadedFile creation**

```python
# BEFORE (around line 116-126):
uploaded_file = UploadedFile(
    filename=unique_filename,
    original_name=original_filename,
    file_path=str(file_path),
    file_size=file_size,
    file_type=file_type,
    mime_type=content_type,
    status="uploaded",
    source_lang=source_lang,
    target_lang=target_lang,
)

# AFTER:
uploaded_file = UploadedFile(
    filename=unique_filename,
    original_name=original_filename,
    file_path=str(file_path),
    file_size=file_size,
    file_type=file_type,
    mime_type=content_type,
    status="uploaded",
    # source_lang and target_lang removed - will be set in Work
)
```

**Step 3: Commit backend service changes**

```bash
git add src/pdftranslator/backend/services/file_service.py
git commit -m "refactor(backend): make language params optional in FileService"
```

---

## Task 5: Remove Language Fields from UploadedFile Model

**Files:**
- Modify: `src/pdftranslator/database/models.py`

**Step 1: Remove source_lang and target_lang from UploadedFile dataclass**

```python
# BEFORE:
@dataclass
class UploadedFile:
    """Represents an uploaded file pending processing."""

    id: int | None = None
    filename: str = ""
    original_name: str = ""
    file_path: str | None = None
    file_size: int = 0
    file_type: str = ""
    mime_type: str | None = None
    work_id: int | None = None
    volume_id: int | None = None
    status: str = "uploaded"
    error_message: str | None = None
    source_lang: str = "en"        # REMOVE
    target_lang: str = "es"        # REMOVE
    created_at: datetime | None = None
    updated_at: datetime | None = None

# AFTER:
@dataclass
class UploadedFile:
    """Represents an uploaded file pending processing."""

    id: int | None = None
    filename: str = ""
    original_name: str = ""
    file_path: str | None = None
    file_size: int = 0
    file_type: str = ""
    mime_type: str | None = None
    work_id: int | None = None
    volume_id: int | None = None
    status: str = "uploaded"
    error_message: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
```

**Step 2: Commit model changes**

```bash
git add src/pdftranslator/database/models.py
git commit -m "refactor(database): remove language fields from UploadedFile model"
```

---

## Task 6: Update UploadedFile Repository

**Files:**
- Modify: `src/pdftranslator/database/repositories/uploaded_file_repository.py`

**Step 1: Update SQL queries to remove language columns**

Find all SQL queries that include `source_lang` and `target_lang` and remove them.

**SELECT queries:**

```python
# BEFORE (around line 20-26):
def _row_to_uploaded_file(self, row: tuple) -> UploadedFile:
    return UploadedFile(
        id=row[0],
        filename=row[1],
        original_name=row[2],
        file_path=row[3],
        file_size=row[4],
        file_type=row[5],
        mime_type=row[6],
        work_id=row[7],
        volume_id=row[8],
        status=row[9],
        error_message=row[10],
        source_lang=row[11],        # REMOVE
        target_lang=row[12],        # REMOVE
        created_at=row[13],
        updated_at=row[14],
    )

# AFTER:
def _row_to_uploaded_file(self, row: tuple) -> UploadedFile:
    return UploadedFile(
        id=row[0],
        filename=row[1],
        original_name=row[2],
        file_path=row[3],
        file_size=row[4],
        file_type=row[5],
        mime_type=row[6],
        work_id=row[7],
        volume_id=row[8],
        status=row[9],
        error_message=row[10],
        created_at=row[11],
        updated_at=row[12],
    )
```

**Step 2: Update SELECT column lists**

```python
# BEFORE:
SELECT id, filename, original_name, file_path, file_size, file_type, mime_type, 
       work_id, volume_id, status, error_message, source_lang, target_lang, created_at, updated_at

# AFTER:
SELECT id, filename, original_name, file_path, file_size, file_type, mime_type, 
       work_id, volume_id, status, error_message, created_at, updated_at
```

**Step 3: Update INSERT queries**

```python
# BEFORE (around line 50-60):
INSERT INTO uploaded_files 
    (filename, original_name, file_path, file_size, file_type, mime_type, 
     work_id, volume_id, status, error_message, source_lang, target_lang, created_at, updated_at)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
RETURNING id, filename, original_name, file_path, file_size, file_type, mime_type,
          work_id, volume_id, status, error_message, source_lang, target_lang, created_at, updated_at

# AFTER:
INSERT INTO uploaded_files 
    (filename, original_name, file_path, file_size, file_type, mime_type, 
     work_id, volume_id, status, error_message, created_at, updated_at)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
RETURNING id, filename, original_name, file_path, file_size, file_type, mime_type,
          work_id, volume_id, status, error_message, created_at, updated_at
```

**Step 4: Update INSERT parameters**

```python
# BEFORE:
cursor.execute(query, (
    entity.filename,
    entity.original_name,
    entity.file_path,
    entity.file_size,
    entity.file_type,
    entity.mime_type,
    entity.work_id,
    entity.volume_id,
    entity.status,
    entity.error_message,
    entity.source_lang,        # REMOVE
    entity.target_lang,        # REMOVE
    entity.created_at,
    entity.updated_at,
))

# AFTER:
cursor.execute(query, (
    entity.filename,
    entity.original_name,
    entity.file_path,
    entity.file_size,
    entity.file_type,
    entity.mime_type,
    entity.work_id,
    entity.volume_id,
    entity.status,
    entity.error_message,
    entity.created_at,
    entity.updated_at,
))
```

**Step 5: Update UPDATE queries**

```python
# BEFORE:
UPDATE uploaded_files 
SET filename = %s, original_name = %s, file_path = %s, file_size = %s, 
    file_type = %s, mime_type = %s, work_id = %s, volume_id = %s, 
    status = %s, error_message = %s, source_lang = %s, target_lang = %s,
    updated_at = %s
WHERE id = %s

# AFTER:
UPDATE uploaded_files 
SET filename = %s, original_name = %s, file_path = %s, file_size = %s, 
    file_type = %s, mime_type = %s, work_id = %s, volume_id = %s, 
    status = %s, error_message = %s, updated_at = %s
WHERE id = %s
```

**Step 6: Commit repository changes**

```bash
git add src/pdftranslator/database/repositories/uploaded_file_repository.py
git commit -m "refactor(database): remove language columns from UploadedFile repository"
```

---

## Task 7: Update Backend Schemas

**Files:**
- Modify: `src/pdftranslator/backend/api/models/schemas.py`

**Step 1: Remove FileUploadQuery schema (or make all fields optional)**

```python
# BEFORE:
class FileUploadQuery(BaseModel):
    """Query parameters for file upload."""

    source_lang: str = Field(default="en", description="Source language code")
    target_lang: str = Field(default="es", description="Target language code")

# AFTER:
class FileUploadQuery(BaseModel):
    """Query parameters for file upload (deprecated - languages configured in Work)."""

    source_lang: str | None = Field(default=None, description="Source language code (ignored)")
    target_lang: str | None = Field(default=None, description="Target language code (ignored)")
```

Or simply delete the schema if not used elsewhere.

**Step 2: Commit schema changes**

```bash
git add src/pdftranslator/backend/api/models/schemas.py
git commit -m "refactor(backend): deprecate language fields in FileUploadQuery schema"
```

---

## Task 8: Create Database Migration Script

**Files:**
- Create: `Docker/postgres/migrations/001_remove_language_from_uploaded_files.sql`

**Step 1: Create migration file**

```bash
mkdir -p /Volumes/Elements2/PycharmProjects/PDFTranslator/Docker/postgres/migrations
```

**Step 2: Write migration SQL**

```sql
-- Migration: Remove language columns from uploaded_files table
-- Date: 2025-04-12
-- Description: Languages are now configured in Work entity, not in UploadedFile

-- Drop columns if they exist
ALTER TABLE uploaded_files DROP COLUMN IF EXISTS source_lang;
ALTER TABLE uploaded_files DROP COLUMN IF EXISTS target_lang;

-- Note: This migration is safe to run multiple times (IF EXISTS)
```

**Step 3: Commit migration**

```bash
git add Docker/postgres/migrations/001_remove_language_from_uploaded_files.sql
git commit -m "feat(database): add migration to remove language columns from uploaded_files"
```

---

## Task 9: Update Tests

**Files:**
- Modify: `tests/backend/test_files.py` (if exists)
- Modify: `tests/database/test_uploaded_file_repository.py` (if exists)

**Step 1: Find and update affected tests**

```bash
cd /Volumes/Elements2/PycharmProjects/PDFTranslator
grep -r "source_lang\|target_lang" tests/ --include="*.py"
```

**Step 2: Update test fixtures and assertions**

Remove or update any tests that:
- Test language selection in upload
- Assert on `source_lang` or `target_lang` in UploadedFile
- Create UploadedFile instances with language fields

**Step 3: Run tests to verify**

```bash
pytest tests/ -v --tb=short
```

**Step 4: Commit test updates**

```bash
git add tests/
git commit -m "test: update tests for language removal from UploadedFile"
```

---

## Task 10: Final Verification

**Step 1: Run all backend tests**

```bash
cd /Volumes/Elements2/PycharmProjects/PDFTranslator
pytest tests/ -v
```

Expected: All tests pass (or only unrelated failures)

**Step 2: Build frontend**

```bash
cd /Volumes/Elements2/PycharmProjects/PDFTranslator/src/pdftranslator/frontend
npm run build
```

Expected: Build succeeds

**Step 3: Manual test**

1. Start backend: `python PDFAgent.py backend`
2. Start frontend: `python PDFAgent.py frontend`
3. Navigate to Files page
4. Upload a PDF file - verify no language selection required
5. Navigate to Translate page - verify language selection still works

**Step 4: Final commit**

```bash
git add -A
git status
git commit -m "feat: remove language selection from Files component

- Remove language selectors from FilesComponent template
- Remove uploadConfig property from FilesComponent
- Make language params optional in backend upload endpoint
- Remove language fields from UploadedFile model and repository
- Add database migration script

Languages are now only configured in TranslateComponent and stored in Work entity."
```

---

## Summary

| Task | Description | Files Modified |
|------|-------------|----------------|
| 1 | Remove UI from FilesComponent | 2 |
| 2 | Update FileService | 1 |
| 3 | Update backend API route | 1 |
| 4 | Update backend FileService | 1 |
| 5 | Update UploadedFile model | 1 |
| 6 | Update repository | 1 |
| 7 | Update schemas | 1 |
| 8 | Create migration | 1 |
| 9 | Update tests | 2+ |
| 10 | Final verification | - |
