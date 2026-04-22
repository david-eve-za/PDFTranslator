# File Upload API Examples

## Upload a File

```bash
# Upload a PDF file
curl -X POST "http://localhost:8000/api/files/upload?source_lang=en&target_lang=es" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@/path/to/My Book - Volume 1.pdf"

# Response
{
  "id": 1,
  "filename": "abc123.pdf",
  "original_name": "My Book - Volume 1.pdf",
  "file_size": 1048576,
  "file_type": "pdf",
  "work_id": 1,
  "work_title": "My Book",
  "volume_id": 1,
  "volume_number": 1,
  "status": "done",
  "created_at": "2026-04-11T16:30:00"
}
```

## List Files

```bash
# Get list of uploaded files
curl "http://localhost:8000/api/files/?page=1&page_size=20"

# Response
{
  "items": [
    {
      "id": 1,
      "filename": "abc123.pdf",
      "original_name": "My Book - Volume 1.pdf",
      "file_size": 1048576,
      "file_type": "pdf",
      "work_id": 1,
      "volume_id": 1,
      "status": "done",
      "created_at": "2026-04-11T16:30:00"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20
}
```

## Get File Details

```bash
curl "http://localhost:8000/api/files/1"
```

## Delete File

```bash
curl -X DELETE "http://localhost:8000/api/files/1"

# Response
{
  "message": "File deleted",
  "id": 1
}
```

## Filename Format

Files must follow the pattern: `Title - Volume X.extension`

Examples:
- `My Light Novel - Volume 1.pdf`
- `Fantasy Book - Volume 12.epub`

## Supported Formats

- PDF (`.pdf`)
- EPUB (`.epub`)
- Word (`.doc`, `.docx`)

## Size Limit

Maximum file size: **300 MB**
