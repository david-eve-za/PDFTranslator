"""
SQLite repository implementations for Translation Domain.
"""

from __future__ import annotations
from typing import Optional, List
from datetime import datetime
import json
import aiosqlite

from ...domain.models.job import TranslationJob, JobStatus, JobPriority
from ...domain.models.segment import Segment
from ...domain.models.glossary_ref import GlossaryReference
from ...domain.repositories.protocols import (
    TranslationJobRepository,
    SegmentRepository,
    TranslationUnitOfWork,
    PaginationParams,
    PaginatedResult,
)
from ...domain.repositories.exceptions import DomainError, NotFoundError
from .connection import DatabaseConnection


class SQLiteJobRepository(TranslationJobRepository):
    def __init__(self, db: DatabaseConnection):
        self._db = db

    async def get_by_id(self, job_id: int) -> Optional[TranslationJob]:
        async with self._db.read_only() as conn:
            row = await conn.execute("SELECT * FROM translation_jobs WHERE id = ?", (job_id,))
            row = await row.fetchone()
            if not row:
                return None
            return self._row_to_job(row)

    async def get_by_uuid(self, uuid: str) -> Optional[TranslationJob]:
        async with self._db.read_only() as conn:
            row = await conn.execute("SELECT * FROM translation_jobs WHERE uuid = ?", (uuid,))
            row = await row.fetchone()
            if not row:
                return None
            return self._row_to_job(row)

    async def get_all(self, pagination: PaginationParams, status: Optional[JobStatus] = None, work_id: Optional[int] = None) -> PaginatedResult[TranslationJob]:
        async with self._db.read_only() as conn:
            where_clauses = []
            params = []

            if status:
                where_clauses.append("status = ?")
                params.append(status.value)
            if work_id:
                where_clauses.append("work_id = ?")
                params.append(work_id)

            where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

            count_row = await conn.execute(f"SELECT COUNT(*) FROM translation_jobs {where_sql}", params)
            count_row = await count_row.fetchone()
            total = count_row[0] if count_row else 0

            params.extend([pagination.limit, pagination.offset])
            cursor = await conn.execute(
                f"SELECT * FROM translation_jobs {where_sql} ORDER BY id DESC LIMIT ? OFFSET ?",
                params,
            )
            rows = await cursor.fetchall()
            items = [self._row_to_job(row) for row in rows]

            return PaginatedResult(items=items, total=total, page=pagination.page, page_size=pagination.page_size)

    async def create(self, job: TranslationJob) -> TranslationJob:
        async with self._db.transaction() as conn:
            glossary_refs = json.dumps([{
                "glossary_id": r.glossary_id, "name": r.name,
                "source_lang": r.source_lang, "target_lang": r.target_lang,
                "priority": r.priority, "entry_count": r.entry_count
            } for r in job.glossary_refs])

            cursor = await conn.execute(
                """
                INSERT INTO translation_jobs (
                    uuid, source_lang, target_lang, work_id, volume_id, status, priority,
                    source_text, target_text, llm_provider, model_name, error_message,
                    started_at, completed_at, glossary_refs, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(job.uuid), job.source_lang, job.target_lang, job.work_id, job.volume_id,
                    job.status.value, job.priority.value, job.source_text, job.target_text,
                    job.llm_provider, job.model_name, job.error_message,
                    job.started_at.isoformat() if job.started_at else None,
                    job.completed_at.isoformat() if job.completed_at else None,
                    glossary_refs,
                    job.created_at.isoformat(), job.updated_at.isoformat(),
                ),
            )
            job.id = cursor.lastrowid
            return job

    async def update(self, job: TranslationJob) -> TranslationJob:
        async with self._db.transaction() as conn:
            job.updated_at = datetime.utcnow()
            glossary_refs = json.dumps([{
                "glossary_id": r.glossary_id, "name": r.name,
                "source_lang": r.source_lang, "target_lang": r.target_lang,
                "priority": r.priority, "entry_count": r.entry_count
            } for r in job.glossary_refs])

            await conn.execute(
                """
                UPDATE translation_jobs SET
                    source_lang = ?, target_lang = ?, work_id = ?, volume_id = ?,
                    status = ?, priority = ?, source_text = ?, target_text = ?,
                    llm_provider = ?, model_name = ?, error_message = ?,
                    started_at = ?, completed_at = ?, glossary_refs = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    job.source_lang, job.target_lang, job.work_id, job.volume_id,
                    job.status.value, job.priority.value, job.source_text, job.target_text,
                    job.llm_provider, job.model_name, job.error_message,
                    job.started_at.isoformat() if job.started_at else None,
                    job.completed_at.isoformat() if job.completed_at else None,
                    glossary_refs,
                    job.updated_at.isoformat(),
                    job.id,
                ),
            )
            return job

    async def delete(self, job_id: int) -> bool:
        async with self._db.transaction() as conn:
            cursor = await conn.execute("DELETE FROM translation_jobs WHERE id = ?", (job_id,))
            return cursor.rowcount > 0

    def _row_to_job(self, row: aiosqlite.Row) -> TranslationJob:
        glossary_refs_data = json.loads(row["glossary_refs"]) if row["glossary_refs"] else []
        glossary_refs = [GlossaryReference(**r) for r in glossary_refs_data]

        job = TranslationJob(
            id=row["id"],
            uuid=row["uuid"],
            source_lang=row["source_lang"],
            target_lang=row["target_lang"],
            work_id=row["work_id"],
            volume_id=row["volume_id"],
            status=JobStatus(row["status"]),
            priority=JobPriority(row["priority"]),
            source_text=row["source_text"],
            target_text=row["target_text"],
            llm_provider=row["llm_provider"],
            model_name=row["model_name"],
            error_message=row["error_message"],
            started_at=datetime.fromisoformat(row["started_at"]) if row["started_at"] else None,
            completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )
        job._glossary_refs = glossary_refs
        return job


class SQLiteSegmentRepository(SegmentRepository):
    def __init__(self, db: DatabaseConnection):
        self._db = db

    async def get_by_id(self, segment_id: int) -> Optional[Segment]:
        async with self._db.read_only() as conn:
            row = await conn.execute("SELECT * FROM translation_segments WHERE id = ?", (segment_id,))
            row = await row.fetchone()
            if not row:
                return None
            return self._row_to_segment(row)

    async def get_by_job_id(self, job_id: int) -> List[Segment]:
        async with self._db.read_only() as conn:
            cursor = await conn.execute("SELECT * FROM translation_segments WHERE job_id = ? ORDER BY segment_number", (job_id,))
            rows = await cursor.fetchall()
            return [self._row_to_segment(row) for row in rows]

    async def create(self, segment: Segment) -> Segment:
        async with self._db.transaction() as conn:
            cursor = await conn.execute(
                """
                INSERT INTO translation_segments (
                    uuid, job_id, segment_number, source_text, target_text,
                    context_before, context_after, notes, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(segment.uuid), segment.job_id, segment.segment_number,
                    segment.source_text, segment.target_text,
                    segment.context_before, segment.context_after, segment.notes,
                    segment.created_at.isoformat(), segment.updated_at.isoformat(),
                ),
            )
            segment.id = cursor.lastrowid
            return segment

    async def update(self, segment: Segment) -> Segment:
        async with self._db.transaction() as conn:
            segment.updated_at = datetime.utcnow()
            await conn.execute(
                """
                UPDATE translation_segments SET
                    segment_number = ?, source_text = ?, target_text = ?,
                    context_before = ?, context_after = ?, notes = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    segment.segment_number, segment.source_text, segment.target_text,
                    segment.context_before, segment.context_after, segment.notes,
                    segment.updated_at.isoformat(), segment.id,
                ),
            )
            return segment

    async def delete(self, segment_id: int) -> bool:
        async with self._db.transaction() as conn:
            cursor = await conn.execute("DELETE FROM translation_segments WHERE id = ?", (segment_id,))
            return cursor.rowcount > 0

    def _row_to_segment(self, row: aiosqlite.Row) -> Segment:
        return Segment(
            id=row["id"],
            uuid=row["uuid"],
            job_id=row["job_id"],
            segment_number=row["segment_number"],
            source_text=row["source_text"],
            target_text=row["target_text"],
            context_before=row["context_before"],
            context_after=row["context_after"],
            notes=row["notes"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )


class SQLiteUnitOfWork(TranslationUnitOfWork):
    def __init__(self, db: DatabaseConnection):
        self._db = db
        self._jobs: Optional[SQLiteJobRepository] = None
        self._segments: Optional[SQLiteSegmentRepository] = None
        self._committed = False

    @property
    def jobs(self) -> SQLiteJobRepository:
        if self._jobs is None:
            self._jobs = SQLiteJobRepository(self._db)
        return self._jobs

    @property
    def segments(self) -> SQLiteSegmentRepository:
        if self._segments is None:
            self._segments = SQLiteSegmentRepository(self._db)
        return self._segments

    async def commit(self) -> None:
        self._committed = True

    async def rollback(self) -> None:
        pass

    async def __aenter__(self) -> SQLiteUnitOfWork:
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        pass