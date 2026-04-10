from datetime import datetime
from typing import List
from fastapi import APIRouter, UploadFile, File, HTTPException
from ..models.schemas import FileUploadResponse

router = APIRouter(prefix="/api/files", tags=["files"])


@router.post("/upload", response_model=List[FileUploadResponse])
async def upload_files(files: List[UploadFile] = File(...)):
    responses = []
    for file in files:
        allowed_extensions = {".pdf", ".epub", ".doc", ".docx"}
        file_ext = "." + file.filename.split(".")[-1].lower()

        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"File type {file_ext} not allowed. Allowed types: {allowed_extensions}",
            )

        responses.append(
            FileUploadResponse(
                id=str(hash(file.filename + str(datetime.now()))),
                name=file.filename,
                size=0,
                type=file_ext[1:],
                uploaded_at=datetime.now(),
                work_id=hash(file.filename) % 10000,
                volume_id=hash(file.filename) % 10000,
            )
        )

    return responses


@router.get("/", response_model=List[FileUploadResponse])
async def list_files():
    return []


@router.get("/{file_id}", response_model=FileUploadResponse)
async def get_file(file_id: str):
    raise HTTPException(status_code=404, detail="File not found")


@router.delete("/{file_id}")
async def delete_file(file_id: str):
    return {"message": "File deleted"}
