"""Translation configuration and job routes."""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from pdftranslator.backend.api.models.schemas import (
    TranslationJobListResponse,
    TranslationJobResponse,
    TranslationStartRequest,
)
from pdftranslator.core.config.llm import BCP47Language, LLMProvider
from pdftranslator.database.repositories.chapter_repository import ChapterRepository
from pdftranslator.database.repositories.glossary_repository import GlossaryRepository
from pdftranslator.database.repositories.translation_job_repository import (
    TranslationJob,
    TranslationJobRepository,
)
from pdftranslator.database.repositories.volume_repository import VolumeRepository
from pdftranslator.services.translation_orchestrator import (
    TranslationOrchestrator,
    TranslationProgress,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["translation"])

# Active SSE connections: job_id -> asyncio.Queue
# Cleaned up periodically to prevent memory leaks from abandoned connections
active_jobs: dict[int, asyncio.Queue] = {}
# Track last activity for cleanup
_job_last_activity: dict[int, datetime] = {}


async def _cleanup_stale_jobs() -> None:
    """Remove jobs that haven't had activity for 5 minutes."""
    cutoff = datetime.now() - timedelta(minutes=5)
    stale_job_ids = [
        job_id
        for job_id, last_active in _job_last_activity.items()
        if last_active < cutoff
    ]
    for job_id in stale_job_ids:
        queue = active_jobs.pop(job_id, None)
        if queue:
            # Signal completion to any waiting consumers
            await queue.put({"type": "error", "data": {"message": "SSE connection timed out"}})
        _job_last_activity.pop(job_id, None)
        logger.info(f"Cleaned up stale SSE job {job_id}")


async def _periodic_cleanup() -> None:
    """Background task to clean up stale SSE connections periodically."""
    while True:
        await asyncio.sleep(60)  # Run every minute
        try:
            await _cleanup_stale_jobs()
        except Exception as e:
            logger.error(f"Error in periodic SSE cleanup: {e}")


# Start cleanup task on module load
_cleanup_task: asyncio.Task | None = None


def _start_cleanup_task() -> None:
    """Start the periodic cleanup task (called from lifespan)."""
    global _cleanup_task
    if _cleanup_task is None or _cleanup_task.done():
        _cleanup_task = asyncio.create_task(_periodic_cleanup())


def _stop_cleanup_task() -> None:
    """Stop the periodic cleanup task."""
    global _cleanup_task
    if _cleanup_task and not _cleanup_task.done():
        _cleanup_task.cancel()
        _cleanup_task = None


def _job_to_response(job: TranslationJob) -> dict:
    return {
        "id": job.id,
        "work_id": job.work_id,
        "scope": job.scope,
        "volume_id": job.volume_id,
        "chapter_id": job.chapter_id,
        "source_lang": job.source_lang,
        "target_lang": job.target_lang,
        "skip_translated": job.skip_translated,
        "dry_run": job.dry_run,
        "status": job.status,
        "total_chapters": job.total_chapters,
        "completed_chapters": job.completed_chapters,
        "success_count": job.success_count,
        "failure_count": job.failure_count,
        "current_chapter_info": job.current_chapter_info,
        "error_message": job.error_message,
        "created_at": job.created_at.isoformat() if job.created_at else datetime.now().isoformat(),
        "updated_at": job.updated_at.isoformat() if job.updated_at else datetime.now().isoformat(),
    }


@router.get("/languages")
async def get_languages() -> List[dict]:
    """Get supported languages for translation."""
    return [
        {"code": lang.value, "name": lang.name.replace("_", " ").title()}
        for lang in BCP47Language
    ]


@router.get("/providers")
async def get_providers() -> List[dict]:
    """Get available LLM providers."""
    return [
        {
            "id": provider.value,
            "name": provider.value.upper(),
            "description": f"{provider.value.capitalize()} LLM provider",
        }
        for provider in LLMProvider
    ]


@router.post("/translate")
async def start_translation(request: TranslationStartRequest) -> dict:
    """Start a translation job."""
    job_repo = TranslationJobRepository()

    job = TranslationJob(
        work_id=request.work_id,
        scope=request.scope,
        volume_id=request.volume_id,
        chapter_id=request.chapter_id,
        source_lang=request.source_lang,
        target_lang=request.target_lang,
        skip_translated=request.skip_translated,
        dry_run=request.dry_run,
    )
    created_job = job_repo.create(job)

    queue: asyncio.Queue = asyncio.Queue()
    active_jobs[created_job.id] = queue
    _job_last_activity[created_job.id] = datetime.now()

    asyncio.create_task(_run_translation_job(created_job.id, queue))

    return {"job_id": created_job.id, "status": "pending"}


@router.get("/translate/{job_id}")
async def get_translation_job(job_id: int) -> dict:
    """Get translation job status."""
    job_repo = TranslationJobRepository()
    job = job_repo.get_by_id(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Translation job not found")
    return _job_to_response(job)


@router.get("/translate/{job_id}/stream")
async def stream_translation_progress(job_id: int):
    """SSE endpoint for translation progress."""
    job_repo = TranslationJobRepository()
    job = job_repo.get_by_id(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Translation job not found")

    if job.status in ("completed", "error"):
        final_event = "job_complete" if job.status == "completed" else "error"
        final_data = {
            "success_count": job.success_count,
            "failure_count": job.failure_count,
        } if job.status == "completed" else {"message": job.error_message}

        async def single_event():
            yield f"event: {final_event}\ndata: {json.dumps(final_data)}\n\n"

        return StreamingResponse(single_event(), media_type="text/event-stream")

    queue = active_jobs.get(job_id)

    if queue is None:
        # Job exists but no active SSE connection - create a new queue
        queue = asyncio.Queue()
        active_jobs[job_id] = queue
        _job_last_activity[job_id] = datetime.now()

    async def event_generator():
        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=300.0)
                except asyncio.TimeoutError:
                    # Send heartbeat to keep connection alive
                    yield ": heartbeat\n\n"
                    continue

                # Update last activity timestamp
                _job_last_activity[job_id] = datetime.now()

                event_type = event.get("type", "progress")
                event_data = event.get("data", {})
                yield f"event: {event_type}\ndata: {json.dumps(event_data)}\n\n"

                if event_type in ("job_complete", "error"):
                    break
        finally:
            # Clean up when client disconnects
            active_jobs.pop(job_id, None)
            _job_last_activity.pop(job_id, None)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/translate", response_model=TranslationJobListResponse)
async def list_translation_jobs() -> dict:
    """List all translation jobs."""
    job_repo = TranslationJobRepository()
    jobs = job_repo.get_all()
    items = [_job_to_response(j) for j in jobs]
    return {"items": items, "total": len(items)}


async def _run_translation_job(job_id: int, queue: asyncio.Queue) -> None:
    """Run a translation job in background and push progress to queue."""
    job_repo = TranslationJobRepository()
    chapter_repo = ChapterRepository()
    glossary_repo = GlossaryRepository()
    volume_repo = VolumeRepository()

    job = job_repo.get_by_id(job_id)
    if job is None:
        await queue.put({"type": "error", "data": {"message": "Job not found"}})
        return

    def on_progress(progress: TranslationProgress) -> None:
        event_type = "progress"
        event_data = {
            "completed_chapters": progress.completed_chapters,
            "total_chapters": progress.total_chapters,
            "current": progress.current_chapter,
        }

        if progress.chapter_status in ("success", "failure", "skipped"):
            event_type = "chapter_complete"
            event_data = {
                "chapter_id": progress.chapter_id,
                "title": progress.chapter_title,
                "status": progress.chapter_status,
                "completed_chapters": progress.completed_chapters,
                "total_chapters": progress.total_chapters,
            }

        # Update last activity
        _job_last_activity[job_id] = datetime.now()

        asyncio.run_coroutine_threadsafe(
            queue.put({"type": event_type, "data": event_data}),
            asyncio.get_event_loop(),
        )

    # Check glossary build status before starting
    if job.scope in ("all_book", "all_volume"):
        await _check_glossary_status(job, volume_repo, glossary_repo)

    orchestrator = TranslationOrchestrator(
        chapter_repo=chapter_repo,
        glossary_repo=glossary_repo,
        volume_repo=volume_repo,
        job_repo=job_repo,
    )

    try:
        # Run with timeout to prevent stuck jobs
        await asyncio.wait_for(
            asyncio.to_thread(orchestrator.execute_job, job),
            timeout=3600.0,  # 1 hour max per job
        )

        final_job = job_repo.get_by_id(job_id)
        if final_job and final_job.status == "completed":
            await queue.put({
                "type": "job_complete",
                "data": {
                    "success_count": final_job.success_count,
                    "failure_count": final_job.failure_count,
                },
            })
        elif final_job and final_job.status == "error":
            await queue.put({
                "type": "error",
                "data": {"message": final_job.error_message},
            })
    except asyncio.TimeoutError:
        logger.error(f"Translation job {job_id} timed out after 1 hour")
        job.status = "error"
        job.error_message = "Translation timed out after 1 hour"
        job_repo.update(job)
        await queue.put({"type": "error", "data": {"message": "Translation timed out"}})
    except Exception as e:
        logger.error(f"Translation job {job_id} error: {e}")
        await queue.put({"type": "error", "data": {"message": str(e)}})
    finally:
        active_jobs.pop(job_id, None)
        _job_last_activity.pop(job_id, None)


async def _check_glossary_status(
    job: TranslationJob,
    volume_repo: VolumeRepository,
    glossary_repo: GlossaryRepository,
) -> None:
    """Check if glossary needs to be built before translation."""
    volumes_to_check = []

    if job.scope == "all_book":
        volumes = volume_repo.get_by_work_id(job.work_id)
        volumes_to_check = volumes
    elif job.scope == "all_volume" and job.volume_id:
        volume = volume_repo.get_by_id(job.volume_id)
        if volume:
            volumes_to_check = [volume]

    for volume in volumes_to_check:
        if volume.glossary_build_status == "pending":
            logger.warning(
                f"Glossary not built for volume {volume.id} (work {job.work_id}). "
                f"Starting glossary build..."
            )
            # Trigger glossary build - could be async, here we log warning
            # In production, you might want to auto-trigger or block
            # For now, just warn and continue with empty glossary
        elif volume.glossary_build_status == "building":
            logger.warning(
                f"Glossary build in progress for volume {volume.id}. "
                f"Translation will use partial glossary."
            )
        elif volume.glossary_build_status == "failed":
            logger.error(
                f"Glossary build failed for volume {volume.id}: {volume.glossary_error_message}. "
                f"Translation will proceed without glossary."
            )