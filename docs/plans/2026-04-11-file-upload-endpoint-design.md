# File Upload Endpoint Design

**Date:** 2026-04-11  
**Status:** Implemented  
**API Style:** REST (with GraphQL planned for future queries)

## Overview

Implemented a complete file upload system for PDFTranslator that:
1. Accepts PDF/EPUB files via multipart/form-data
2. Extracts text using existing `TextExtractor`
3. Creates Work/Volume in database following CLI's `add_to_database` flow
4. Cleans up temporary files after successful processing
5. Tracks file metadata in `uploaded_files` table

## Architecture

### Layers
```
files.py (router) → FileService → FileRepository → Database
                         ↓
                   TextExtractor (existing)
                         ↓
                   WorkRepository/VolumeRepository
```

### Database Schema

**New table:** `uploaded_files` (schema 010)
```sql
CREATE TABLE uploaded_files (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,         -- unique UUID filename
    original_name VARCHAR(500) NOT NULL,    -- user's original filename
    file_path TEXT,                         -- temporary path (deleted after processing)
    file_size BIGINT NOT NULL,
    file_type VARCHAR(50) NOT NULL,         -- pdf, epub, etc.
    mime_type VARCHAR(100),
    work_id INTEGER REFERENCES works(id),
    volume_id INTEGER REFERENCES volumes(id),
    status VARCHAR(50) DEFAULT 'uploaded',  -- uploaded|processing|done|error
    error_message TEXT,
    source_lang VARCHAR(10) DEFAULT 'en',
    target_lang VARCHAR(10) DEFAULT 'es',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/files/upload` | Upload file, extract text, create Work/Volume |
| GET | `/api/files/` | List files with pagination |
| GET | `/api/files/{file_id}` | Get file details |
| DELETE | `/api/files/{file_id}` | Delete file record |

### Upload Flow

```
POST /api/files/upload?source_lang=en&target_lang=es
Content-Type: multipart/form-data

1. Validate MIME type and file size (max 300MB)
2. Save to temporary directory with UUID filename
3. Create `uploaded_files` record (status='uploaded')
4. Parse filename: "Title - Volume X" pattern
5. Extract text using TextExtractor
6. Create/find Work with BookRepository
7. Create Volume with extracted text
8. Delete temporary file
9. Update status to 'done'
10. Return file metadata with work_id/volume_id
```

## Security

- **MIME validation:** Only `application/pdf`, `application/epub+zip`, etc.
- **Size limit:** 300MB configurable
- **Filename sanitization:** Removes special characters
- **Unique filenames:** UUID-based to prevent collisions
- **File cleanup:** Automatic deletion after successful processing

## Files Created

```
src/pdftranslator/
├── database/
│   ├── models.py                          # Added UploadedFile dataclass
│   ├── schemas/010_uploaded_files.sql     # Database schema
│   └── repositories/
│       └── uploaded_file_repository.py    # Repository for uploaded_files
├── backend/
│   ├── api/routes/files.py               # REST endpoints (modified)
│   ├── api/models/schemas.py             # Pydantic schemas (modified)
│   └── services/
│       ├── __init__.py
│       └── file_service.py               # Business logic
tests/backend/
└── test_files.py                         # Unit tests
```

## Tests

All 9 tests passing:
- File upload with valid PDF
- Invalid extension rejection
- File too large rejection
- Empty file list
- Pagination
- Get existing file
- Get nonexistent file
- Delete existing file
- Delete nonexistent file

## Future Work

1. **GraphQL endpoint** for complex queries (work + volumes + chapters in single request)
2. **Async processing** with background tasks for large files
3. **Resume failed uploads** with status tracking
4. **Batch upload** endpoint for multiple files
