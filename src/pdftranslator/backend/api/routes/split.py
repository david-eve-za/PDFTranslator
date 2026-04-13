"""Split text routes."""

from fastapi import APIRouter, Depends, HTTPException

from pdftranslator.backend.api.models.schemas import (
    SplitPreviewRequest,
    SplitPreviewResponse,
    SplitProcessRequest,
    SplitProcessResponse,
)
from pdftranslator.cli.commands.split_text import parse_blocks, BlockParseError
from pdftranslator.database.connection import DatabasePool
from pdftranslator.database.repositories.volume_repository import VolumeRepository
from pdftranslator.database.repositories.chapter_repository import ChapterRepository

router = APIRouter(prefix="/api/split", tags=["split"])


def get_volume_repository() -> VolumeRepository:
    return VolumeRepository(DatabasePool.get_instance())


def get_chapter_repository() -> ChapterRepository:
    return ChapterRepository(DatabasePool.get_instance())


@router.post("/preview", response_model=SplitPreviewResponse)
async def preview_split(request: SplitPreviewRequest):
    """Preview parsed blocks from text."""
    try:
        blocks = parse_blocks(request.text)
        block_dicts = [
            {
                "block_type": b.block_type,
                "title": b.title,
                "content": b.content,
                "start_line": b.start_line,
                "end_line": b.end_line,
            }
            for b in blocks
        ]
        return SplitPreviewResponse(blocks=block_dicts, has_errors=False)
    except BlockParseError as e:
        return SplitPreviewResponse(
            blocks=[],
            has_errors=True,
            error_message=f"Line {e.line_number}: {e.message}",
        )


@router.post("/process", response_model=SplitProcessResponse)
async def process_split(
    request: SplitProcessRequest,
    volume_repo: VolumeRepository = Depends(get_volume_repository),
    chapter_repo: ChapterRepository = Depends(get_chapter_repository),
):
    """Process split text and create chapters."""
    volume = volume_repo.get_by_id(request.volume_id)
    if not volume:
        raise HTTPException(status_code=404, detail="Volume not found")

    try:
        blocks = parse_blocks(request.text)
    except BlockParseError as e:
        return SplitProcessResponse(
            success=False,
            error_message=f"Line {e.line_number}: {e.message}",
        )

    if not blocks:
        volume_repo.update_full_text(request.volume_id, request.text)
        return SplitProcessResponse(success=True, chapters_created=0)

    volume_repo.update_full_text(request.volume_id, request.text)

    existing_chapters = chapter_repo.get_by_volume(request.volume_id)
    for chapter in existing_chapters:
        if chapter.id:
            chapter_repo.delete(chapter.id)

    chapter_number = 1
    created_count = 0
    from pdftranslator.database.models import Chapter

    for block in blocks:
        if block.block_type == "Chapter":
            num = chapter_number
            chapter_number += 1
        else:
            num = None

        chapter = Chapter(
            id=None,
            volume_id=request.volume_id,
            chapter_number=num,
            title=block.title,
            original_text=block.content,
            translated_text=None,
        )
        chapter_repo.create(chapter)
        created_count += 1

    block_dicts = [
        {
            "block_type": b.block_type,
            "title": b.title,
            "content": b.content,
            "start_line": b.start_line,
            "end_line": b.end_line,
        }
        for b in blocks
    ]

    return SplitProcessResponse(
        success=True, chapters_created=created_count, blocks=block_dicts
    )
