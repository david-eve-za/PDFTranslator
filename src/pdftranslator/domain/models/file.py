"""Domain model for uploaded files.

Maps from SQL schema: uploaded_files -> UploadedFile
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class UploadedFile:
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
