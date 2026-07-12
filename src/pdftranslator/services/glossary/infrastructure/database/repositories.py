"""
SQLite Repository Implementations for Glossary Service.

CUPID Principle: Composable
- Protocols define contracts
- SQLite implementations are swappable
- All database logic here, not in domain
"""

from __future__ import annotations
from typing import Optional, List
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

import aiosqlite

from .....domain.models.glossary import Glossary, GlossaryEntry, GlossaryStatus
from .....domain.models.build_pipeline import (
    BuildPipeline,
    StageExecution,
    PipelineStageStatus,
    BuildPipelineStatus,
    PipelineStageEnum,
)
from .....domain.models.entity import EntityCandidate, EntityType
from ...repositories.protocols import (
    GlossaryRepository,
    GlossaryEntryRepository,
    BuildPipelineRepository,
    EntityExtractorRepository,
    GlossaryUnitOfWork,
    PaginationParams,
    PaginatedResult,
)


# ============================================================================
# ROW MAPPERS
# ============================================================================

def _row_to_glossary(row: aiosqlite.Row) -> Glossary:
    return Glossary(
        id=row["id"],
        uuid=UUID(row["uuid"]) if row.get("uuid") else uuid4(),
        work_id=row["work_id"],
        name=row["name"],
        source_lang=row["source_lang"],
        target_lang=row["target_lang"],
        status=GlossaryStatus(row["status"]),
        entries={},  # Loaded separately
        created_at=_parse_dt(row["created_at"]),
        updated_at=_parse_dt(row["updated_at"]),
    )


def _row_to_entry(row: aiosqlite.Row) -> GlossaryEntry:
    return GlossaryEntry(
        id=row["id"],
        uuid=UUID(row["uuid"]) if row.get("uuid") else uuid4(),
        work_id=row.get("work_id", row.get("glossary_id", 0)),
        term=row["term"],
        translation=row["translation"],
        entity_type=EntityType.from_str(row["entity_type"]),
        is_proper_noun=bool(row.get("is_proper_noun", False)),
        do_not_translate=bool(row.get("do_not_translate", False)),
        is_verified=bool(row.get("is_verified", False)),
        confidence=float(row.get("confidence", 0.0)),
        frequency=row.get("frequency", 1),
        context=row.get("context"),
        notes=row.get("notes"),
        source_lang=row.get("source_lang", "en"),
        target_lang=row.get("target_lang", "es"),
        created_at=_parse_dt(row["created_at"]),
        updated_at=_parse_dt(row["updated_at"]),
    )


def _row_to_pipeline(row: aiosqlite.Row) -> BuildPipeline:
    return BuildPipeline(
        id=UUID(row["id"]),
        work_id=row["work_id"],
        volume_id=row["volume_id"],
        source_lang=row["source_lang"],
        target_lang=row["target_lang"],
        min_frequency=row["min_frequency"],
        dry_run=bool(row.get("dry_run", False)),
        status=BuildPipelineStatus(row["status"]),
        stages=[],  # Loaded separately
        current_stage_index=row.get("current_stage_index", 0),
        filtered_count=row.get("filtered_count", 0),
        created_at=_parse_dt(row["created_at"]),
        updated_at=_parse_dt(row["updated_at"]),
    )


def _row_to_stage(row: aiosqlite.Row) -> StageExecution:
    return StageExecution(
        name=row["name"],
        status=PipelineStageStatus(row["status"]),
        input_data=_parse_json(row["input_data"]) if row["input_data"] else {},
        output_data=_parse_json(row["output_data"]) if row["output_data"] else {},
        error_message=row["error_message"],
        started_at=_parse_dt(row["started_at"]),
        completed_at=_parse_dt(row["completed_at"]),
        retry_count=row.get("retry_count", 0),
    )


def _parse_dt(value) -> Optional[datetime]:
    """Parse datetime from SQLite."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        value_str = str(value).strip()
        if " " in value_str and "T" not in value_str:
            value_str = value_str.replace(" ", "T")
        if value_str.endswith("Z"):
            value_str = value_str[:-1] + "+00:00"
        return datetime.fromisoformat(value_str)
    except (ValueError, AttributeError):
        return None


def _parse_json(value: str) -> dict:
    """Parse JSON string."""
    import json
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return {}


def _to_json(value: dict) -> str:
    """Serialize to JSON string."""
    import json
    return json.dumps(value)


# ============================================================================
# REPOSITORY IMPLEMENTATIONS
# ============================================================================

class SQLiteGlossaryRepository(GlossaryRepository):
    """SQLite implementation of GlossaryRepository."""

    def __init__(self, db: aiosqlite.Connection):
        self._db = db

    async def get_by_id(self, glossary_id: int) -> Optional[Glossary]:
        async with self._db.execute(
            "SELECT * FROM glossaries WHERE id = ?", (glossary_id,)
        ) as cur:
            row = await cur.fetchone()
            return _row_to_glossary(row) if row else None

    async def get_by_uuid(self, uuid_str: str) -> Optional[Glossary]:
        async with self._db.execute(
            "SELECT * FROM glossaries WHERE uuid = ?", (uuid_str,)
        ) as cur:
            row = await cur.fetchone()
            return _row_to_glossary(row) if row else None

    async def get_by_work(self, work_id: int) -> Optional[Glossary]:
        async with self._db.execute(
            "SELECT * FROM glossaries WHERE work_id = ?", (work_id,)
        ) as cur:
            row = await cur.fetchone()
            return _row_to_glossary(row) if row else None

    async def create(self, glossary: Glossary) -> Glossary:
        uuid_str = str(glossary.uuid)
        async with self._db.execute(
            """
            INSERT INTO glossaries (uuid, work_id, name, source_lang, target_lang, status)
            VALUES (?, ?, ?, ?, ?, ?)
            RETURNING id, uuid, work_id, name, source_lang, target_lang, status, created_at, updated_at
            """,
            (
                uuid_str,
                glossary.work_id,
                glossary.name,
                glossary.source_lang,
                glossary.target_lang,
                glossary.status.value,
            ),
        ) as cur:
            row = await cur.fetchone()
            await self._db.commit()
            return _row_to_glossary(row)

    async def update(self, glossary: Glossary) -> Glossary:
        async with self._db.execute(
            """
            UPDATE glossaries SET
                name = ?, status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            RETURNING id, uuid, work_id, name, source_lang, target_lang, status, created_at, updated_at
            """,
            (glossary.name, glossary.status.value, glossary.id),
        ) as cur:
            row = await cur.fetchone()
            await self._db.commit()
            if not row:
                raise ValueError(f"Glossary {glossary.id} not found")
            return _row_to_glossary(row)

    async def delete(self, glossary_id: int) -> bool:
        async with self._db.execute(
            "DELETE FROM glossaries WHERE id = ?", (glossary_id,)
        ) as cur:
            await self._db.commit()
            return cur.rowcount > 0

    async def list(
        self,
        pagination: PaginationParams,
        work_id: Optional[int] = None,
        status: Optional[str] = None,
    ) -> PaginatedResult[Glossary]:
        where = []
        params = []

        if work_id is not None:
            where.append("work_id = ?")
            params.append(work_id)
        if status is not None:
            where.append("status = ?")
            params.append(status)

        where_clause = "WHERE " + " AND ".join(where) if where else ""

        # Count total
        async with self._db.execute(
            f"SELECT COUNT(*) FROM glossaries {where_clause}", params
        ) as cur:
            row = await cur.fetchone()
            total = row[0] if row else 0

        # Get page
        params.extend([pagination.limit, pagination.offset])
        async with self._db.execute(
            f"""
            SELECT * FROM glossaries {where_clause}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """,
            params,
        ) as cur:
            rows = await cur.fetchall()
            items = [_row_to_glossary(r) for r in rows]

        return PaginatedResult(
            items=items,
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
        )


class SQLiteGlossaryEntryRepository(GlossaryEntryRepository):
    """SQLite implementation of GlossaryEntryRepository."""

    def __init__(self, db: aiosqlite.Connection):
        self._db = db

    async def get_by_id(self, entry_id: int) -> Optional[GlossaryEntry]:
        async with self._db.execute(
            "SELECT * FROM glossary_entries WHERE id = ?", (entry_id,)
        ) as cur:
            row = await cur.fetchone()
            return _row_to_entry(row) if row else None

    async def get_by_term(self, work_id: int, term: str) -> Optional[GlossaryEntry]:
        # Need to join with glossaries
        async with self._db.execute(
            """
            SELECT ge.* FROM glossary_entries ge
            JOIN glossaries g ON ge.glossary_id = g.id
            WHERE g.work_id = ? AND LOWER(ge.term) = LOWER(?)
            """,
            (work_id, term),
        ) as cur:
            row = await cur.fetchone()
            return _row_to_entry(row) if row else None

    async def get_by_uuid(self, uuid_str: str) -> Optional[GlossaryEntry]:
        async with self._db.execute(
            "SELECT * FROM glossary_entries WHERE uuid = ?", (uuid_str,)
        ) as cur:
            row = await cur.fetchone()
            return _row_to_entry(row) if row else None

    async def create(self, entry: GlossaryEntry) -> GlossaryEntry:
        # First get glossary_id from work_id
        async with self._db.execute(
            "SELECT id FROM glossaries WHERE work_id = ?", (entry.work_id,)
        ) as cur:
            row = await cur.fetchone()
            if not row:
                raise ValueError(f"No glossary for work {entry.work_id}")
            glossary_id = row["id"]

        uuid_str = str(entry.uuid)
        async with self._db.execute(
            """
            INSERT INTO glossary_entries
                (uuid, glossary_id, term, translation, entity_type,
                 is_proper_noun, do_not_translate, is_verified,
                 confidence, frequency, context, notes,
                 source_lang, target_lang)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            RETURNING id, uuid, glossary_id, term, translation, entity_type,
                     is_proper_noun, do_not_translate, is_verified,
                     confidence, frequency, context, notes,
                     source_lang, target_lang, created_at, updated_at
            """,
            (
                uuid_str,
                glossary_id,
                entry.term,
                entry.translation,
                entry.entity_type.value,
                entry.is_proper_noun,
                entry.do_not_translate,
                entry.is_verified,
                entry.confidence,
                entry.frequency,
                entry.context,
                entry.notes,
                entry.source_lang,
                entry.target_lang,
            ),
        ) as cur:
            row = await cur.fetchone()
            await self._db.commit()
            return _row_to_entry(row)

    async def update(self, entry: GlossaryEntry) -> GlossaryEntry:
        async with self._db.execute(
            """
            UPDATE glossary_entries SET
                term = ?, translation = ?, entity_type = ?,
                is_proper_noun = ?, do_not_translate = ?, is_verified = ?,
                confidence = ?, frequency = ?, context = ?, notes = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            RETURNING id, uuid, glossary_id, term, translation, entity_type,
                     is_proper_noun, do_not_translate, is_verified,
                     confidence, frequency, context, notes,
                     source_lang, target_lang, created_at, updated_at
            """,
            (
                entry.term,
                entry.translation,
                entry.entity_type.value,
                entry.is_proper_noun,
                entry.do_not_translate,
                entry.is_verified,
                entry.confidence,
                entry.frequency,
                entry.context,
                entry.notes,
                entry.id,
            ),
        ) as cur:
            row = await cur.fetchone()
            await self._db.commit()
            if not row:
                raise ValueError(f"Entry {entry.id} not found")
            return _row_to_entry(row)

    async def delete(self, entry_id: int) -> bool:
        async with self._db.execute(
            "DELETE FROM glossary_entries WHERE id = ?", (entry_id,)
        ) as cur:
            await self._db.commit()
            return cur.rowcount > 0

    async def batch_create(self, entries: List[GlossaryEntry]) -> List[GlossaryEntry]:
        results = []
        for entry in entries:
            results.append(await self.create(entry))
        return results

    async def batch_update(self, entries: List[GlossaryEntry]) -> List[GlossaryEntry]:
        results = []
        for entry in entries:
            results.append(await self.update(entry))
        return results

    async def list_by_work(
        self,
        work_id: int,
        pagination: PaginationParams,
        entity_type: Optional[EntityType] = None,
        verified_only: bool = False,
    ) -> PaginatedResult[GlossaryEntry]:
        where = ["g.work_id = ?"]
        params = [work_id]

        if entity_type is not None:
            where.append("ge.entity_type = ?")
            params.append(entity_type.value)

        if verified_only:
            where.append("ge.is_verified = 1")

        where_clause = "WHERE " + " AND ".join(where)

        # Count
        async with self._db.execute(
            f"""
            SELECT COUNT(*) FROM glossary_entries ge
            JOIN glossaries g ON ge.glossary_id = g.id
            {where_clause}
            """,
            params,
        ) as cur:
            row = await cur.fetchone()
            total = row[0] if row else 0

        # Get page
        params.extend([pagination.limit, pagination.offset])
        async with self._db.execute(
            f"""
            SELECT ge.* FROM glossary_entries ge
            JOIN glossaries g ON ge.glossary_id = g.id
            {where_clause}
            ORDER BY ge.term
            LIMIT ? OFFSET ?
            """,
            params,
        ) as cur:
            rows = await cur.fetchall()
            items = [_row_to_entry(r) for r in rows]

        return PaginatedResult(
            items=items,
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
        )

    async def search(
        self,
        work_id: int,
        query: str,
        pagination: PaginationParams,
    ) -> PaginatedResult[GlossaryEntry]:
        where = ["g.work_id = ?", "ge.term LIKE ?"]
        params = [work_id, f"%{query}%"]

        where_clause = "WHERE " + " AND ".join(where)

        async with self._db.execute(
            f"""
            SELECT COUNT(*) FROM glossary_entries ge
            JOIN glossaries g ON ge.glossary_id = g.id
            {where_clause}
            """,
            params,
        ) as cur:
            row = await cur.fetchone()
            total = row[0] if row else 0

        params.extend([pagination.limit, pagination.offset])
        async with self._db.execute(
            f"""
            SELECT ge.* FROM glossary_entries ge
            JOIN glossaries g ON ge.glossary_id = g.id
            {where_clause}
            ORDER BY ge.term
            LIMIT ? OFFSET ?
            """,
            params,
        ) as cur:
            rows = await cur.fetchall()
            items = [_row_to_entry(r) for r in rows]

        return PaginatedResult(
            items=items,
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
        )

    async def get_existing_terms(self, work_id: int) -> set[str]:
        async with self._db.execute(
            """
            SELECT LOWER(ge.term) FROM glossary_entries ge
            JOIN glossaries g ON ge.glossary_id = g.id
            WHERE g.work_id = ?
            """,
            (work_id,),
        ) as cur:
            rows = await cur.fetchall()
            return {row[0] for row in rows}


class SQLiteBuildPipelineRepository(BuildPipelineRepository):
    """SQLite implementation of BuildPipelineRepository."""

    def __init__(self, db: aiosqlite.Connection):
        self._db = db

    async def get_by_id(self, pipeline_id: str) -> Optional[BuildPipeline]:
        async with self._db.execute(
            "SELECT * FROM build_pipelines WHERE id = ?", (pipeline_id,)
        ) as cur:
            row = await cur.fetchone()
            if not row:
                return None
            pipeline = _row_to_pipeline(row)
            # Load stages
            pipeline = await self._load_stages(pipeline)
            return pipeline

    async def get_by_work_volume(self, work_id: int, volume_id: int) -> Optional[BuildPipeline]:
        async with self._db.execute(
            """
            SELECT * FROM build_pipelines
            WHERE work_id = ? AND volume_id = ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (work_id, volume_id),
        ) as cur:
            row = await cur.fetchone()
            if not row:
                return None
            pipeline = _row_to_pipeline(row)
            return await self._load_stages(pipeline)

    async def _load_stages(self, pipeline: BuildPipeline) -> BuildPipeline:
        async with self._db.execute(
            "SELECT * FROM pipeline_stages WHERE pipeline_id = ? ORDER BY name",
            (str(pipeline.id),),
        ) as cur:
            rows = await cur.fetchall()
            stages = [_row_to_stage(r) for r in rows]
            return pipeline._replace(stages=stages)

    async def create(self, pipeline: BuildPipeline) -> BuildPipeline:
        uuid_str = str(pipeline.id)
        async with self._db.execute(
            """
            INSERT INTO build_pipelines
                (id, work_id, volume_id, source_lang, target_lang,
                 min_frequency, dry_run, status, current_stage_index, filtered_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            RETURNING *
            """,
            (
                uuid_str,
                pipeline.work_id,
                pipeline.volume_id,
                pipeline.source_lang,
                pipeline.target_lang,
                pipeline.min_frequency,
                pipeline.dry_run,
                pipeline.status.value,
                pipeline.current_stage_index,
                pipeline.filtered_count,
            ),
        ) as cur:
            row = await cur.fetchone()
            await self._db.commit()
            new_pipeline = _row_to_pipeline(row)

            # Create stages
            for stage_name in PipelineStageEnum.all():
                await self._db.execute(
                    """
                    INSERT INTO pipeline_stages (pipeline_id, name, status)
                    VALUES (?, ?, 'pending')
                    """,
                    (uuid_str, stage_name),
                )
            await self._db.commit()

            return new_pipeline

    async def update(self, pipeline: BuildPipeline) -> BuildPipeline:
        async with self._db.execute(
            """
            UPDATE build_pipelines SET
                status = ?, current_stage_index = ?, filtered_count = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            RETURNING *
            """,
            (
                pipeline.status.value,
                pipeline.current_stage_index,
                pipeline.filtered_count,
                str(pipeline.id),
            ),
        ) as cur:
            row = await cur.fetchone()
            await self._db.commit()
            if not row:
                raise ValueError(f"Pipeline {pipeline.id} not found")
            pipeline = _row_to_pipeline(row)

            # Update stages
            for stage in pipeline.stages:
                await self._db.execute(
                    """
                    INSERT INTO pipeline_stages
                        (pipeline_id, name, status, input_data, output_data,
                         error_message, started_at, completed_at, retry_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(pipeline_id, name) DO UPDATE SET
                        status = excluded.status,
                        input_data = excluded.input_data,
                        output_data = excluded.output_data,
                        error_message = excluded.error_message,
                        started_at = excluded.started_at,
                        completed_at = excluded.completed_at,
                        retry_count = excluded.retry_count,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (
                        str(pipeline.id),
                        stage.name,
                        stage.status.value,
                        _to_json(stage.input_data),
                        _to_json(stage.output_data),
                        stage.error_message,
                        stage.started_at.isoformat() if stage.started_at else None,
                        stage.completed_at.isoformat() if stage.completed_at else None,
                        stage.retry_count,
                    ),
                )
            await self._db.commit()

            return pipeline

    async def delete(self, pipeline_id: str) -> bool:
        async with self._db.execute(
            "DELETE FROM build_pipelines WHERE id = ?", (pipeline_id,)
        ) as cur:
            await self._db.commit()
            return cur.rowcount > 0

    async def list(
        self,
        pagination: PaginationParams,
        work_id: Optional[int] = None,
        status: Optional[str] = None,
    ) -> PaginatedResult[BuildPipeline]:
        where = []
        params = []

        if work_id is not None:
            where.append("work_id = ?")
            params.append(work_id)
        if status is not None:
            where.append("status = ?")
            params.append(status)

        where_clause = "WHERE " + " AND ".join(where) if where else ""

        async with self._db.execute(
            f"SELECT COUNT(*) FROM build_pipelines {where_clause}", params
        ) as cur:
            row = await cur.fetchone()
            total = row[0] if row else 0

        params.extend([pagination.limit, pagination.offset])
        async with self._db.execute(
            f"""
            SELECT * FROM build_pipelines {where_clause}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """,
            params,
        ) as cur:
            rows = await cur.fetchall()
            items = [await self._load_stages(_row_to_pipeline(r)) for r in rows]

        return PaginatedResult(
            items=items,
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
        )


class SQLiteEntityExtractorRepository(EntityExtractorRepository):
    """SQLite wrapper around existing EntityExtractor service."""

    def __init__(self, db: aiosqlite.Connection):
        self._db = db

    async def extract(
        self,
        text: str,
        source_lang: str,
        min_frequency: int = 2,
    ) -> List[EntityCandidate]:
        # Delegate to existing entity extractor (in database/services)
        # For now, return empty - will be wired up in dependencies
        from pdftranslator.database.services.entity_extractor import EntityExtractor
        from pdftranslator.database.connection import DatabasePool

        pool = DatabasePool.get_instance()
        extractor = EntityExtractor(pool, min_frequency=min_frequency)
        return extractor.extract(text, source_lang)


# ============================================================================
# UNIT OF WORK
# ============================================================================

class SQLiteUnitOfWork(GlossaryUnitOfWork):
    """SQLite Unit of Work for transactional operations."""

    def __init__(self, db: aiosqlite.Connection):
        self._db = db
        self.glossaries: GlossaryRepository = SQLiteGlossaryRepository(db)
        self.glossary_entries: GlossaryEntryRepository = SQLiteGlossaryEntryRepository(db)
        self.pipelines: BuildPipelineRepository = SQLiteBuildPipelineRepository(db)
        self.entity_extractor: EntityExtractorRepository = SQLiteEntityExtractorRepository(db)

    async def __aenter__(self) -> "SQLiteUnitOfWork":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_type:
            await self.rollback()
        else:
            await self.commit()

    async def commit(self) -> None:
        await self._db.commit()

    async def rollback(self) -> None:
        await self._db.rollback()