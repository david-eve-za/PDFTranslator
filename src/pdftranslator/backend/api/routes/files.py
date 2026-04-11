"""File upload and management routes."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile

from pdftranslator.backend.api.models.schemas import (
    FileListResponse,
    FileUploadResponse,
)
from pdftranslator.backend.services.file_service import FileService, ProcessingResult
from pdftranslator.database.models import UploadedFile

router = APIRouter(prefix="/api/files", tags=["files"])


def get_file_service() -> FileService:
    return FileService()


def _uploaded_file_to_response(uploaded_file: UploadedFile) -> FileUploadResponse:
    return FileUploadResponse(
        id=uploaded_file.id,
        filename=uploaded_file.filename,
        original_name=uploaded_file.original_name,
        file_size=uploaded_file.file_size,
        file_type=uploaded_file.file_type,
        work_id=uploaded_file.work_id,
        work_title=None,
        volume_id=uploaded_file.volume_id,
        volume_number=None,
        status=uploaded_file.status,
        created_at=uploaded_file.created_at or datetime.now(),
    )


def _processing_result_to_response(
    uploaded_file: UploadedFile, result: ProcessingResult
) -> FileUploadResponse:
    return FileUploadResponse(
        id=uploaded_file.id,
        filename=uploaded_file.filename,
        original_name=uploaded_file.original_name,
        file_size=uploaded_file.file_size,
        file_type=uploaded_file.file_type,
        work_id=result.work_id,
        work_title=result.work_title,
        volume_id=result.volume_id,
        volume_number=result.volume_number,
        status="done" if result.success else "error",
        created_at=uploaded_file.created_at or datetime.now(),
    )


@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    file: Annotated[UploadFile, File()],
    source_lang: str = Query(default="en", description="Source language code"),
    target_lang: str = Query(default="es", description="Target language code"),
    service: FileService = Depends(get_file_service),
):
    """Upload a file for processing. Extracts text and creates Work/Volume."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    is_valid, error_msg = service.validate_file(file.filename, file.content_type, 0)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)

    file_content = await file.read()
    file_size = len(file_content)

    is_valid, error_msg = service.validate_file(
        file.filename, file.content_type, file_size
    )
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)

    try:
        uploaded_file = await service.save_upload_file(
            file_content=file_content,
            original_filename=file.filename,
            content_type=file.content_type,
            source_lang=source_lang,
            target_lang=target_lang,
        )

        result = service.process_file(uploaded_file)

        if not result.success:
            raise HTTPException(
                status_code=422,
                detail=result.error_message or "Processing failed",
            )

        return _processing_result_to_response(uploaded_file, result)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}") from e


@router.get("/", response_model=FileListResponse)
async def list_files(
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    service: FileService = Depends(get_file_service),
):
    """List all uploaded files with pagination."""
    files, total = service.list_files(page=page, page_size=page_size)
    items = [_uploaded_file_to_response(f) for f in files]
    return FileListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{file_id}", response_model=FileUploadResponse)
async def get_file(
    file_id: int,
    service: FileService = Depends(get_file_service),
):
    """Get file details by ID."""
    uploaded_file = service.get_file(file_id)
    if not uploaded_file:
        raise HTTPException(status_code=404, detail="File not found")
    return _uploaded_file_to_response(uploaded_file)


@router.delete("/{file_id}")
async def delete_file(
    file_id: int,
    service: FileService = Depends(get_file_service),
):
    """Delete file by ID. Removes from database (file already cleaned up)."""
    deleted = service.delete_file(file_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="File not found")
    return {"message": "File deleted", "id": file_id}
