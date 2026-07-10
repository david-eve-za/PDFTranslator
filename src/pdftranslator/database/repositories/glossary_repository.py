"""Glossary term repository for SQLite."""

from typing import Optional, List
import json

from pdftranslator.database.connection import DatabasePool
from pdftranslator.database.repositories.base import BaseRepository
from pdftranslator.database.models import GlossaryEntry, TermContext, ContextExample
from pdftranslator.database.services.vector_store import VectorStoreService
from langchain_core.documents import Document


class GlossaryRepository(BaseRepository[GlossaryEntry]):
    def __init__(self, pool: Optional[DatabasePool] = None):
        self._pool = pool or DatabasePool.get_instance()
        self._vector_service = VectorStoreService()

    def _row_to_entry(self, row) -> GlossaryEntry:
        return GlossaryEntry(
            id=row["id"],
            work_id=row["work_id"],
            term=row["term"],
            translation=row["translation"],
            notes=row["notes"] if "notes" in row.keys() else None,
            is_proper_noun=bool(row["is_proper_noun"]) if "is_proper_noun" in row.keys() else False,
            entity_type=row["entity_type"] if "entity_type" in row.keys() else "other",
            do_not_translate=bool(row["do_not_translate"]) if "do_not_translate" in row.keys() else False,
            is_verified=bool(row["is_verified"]) if "is_verified" in row.keys() else False,
            confidence=float(row["confidence"]) if "confidence" in row.keys() else 0.0,
            context=row["context"] if "context" in row.keys() else None,
            frequency=row["frequency"] if "frequency" in row.keys() else 0,
            source_lang=row["source_lang"] if "source_lang" in row.keys() else "en",
            target_lang=row["target_lang"] if "target_lang" in row.keys() else "es",
            embedding=None,  # Embeddings not stored in SQLite
            created_at=row["created_at"] if "created_at" in row.keys() else None,
            updated_at=row["updated_at"] if "updated_at" in row.keys() else None,
        )

    def _row_to_context(self, row) -> TermContext:
        return TermContext(
            id=row["id"],
            term_id=row["term_id"],
            context_hint=row["context_hint"],
            translation=row["translation"],
            example_usage=row["example_usage"] if "example_usage" in row.keys() else None,
            created_at=row["created_at"] if "created_at" in row.keys() else None,
        )

    def _row_to_example(self, row) -> ContextExample:
        return ContextExample(
            id=row["id"],
            context_id=row["context_id"],
            original_sentence=row["original_sentence"],
            translated_sentence=row["translated_sentence"],
            chapter_id=row["chapter_id"] if "chapter_id" in row.keys() else None,
            created_at=row["created_at"] if "created_at" in row.keys() else None,
        )

    def get_by_id(self, id: int) -> Optional[GlossaryEntry]:
        with self._pool.connection() as conn:
            cur = conn.execute("SELECT * FROM glossary_terms WHERE id = ?", (id,))
            row = cur.fetchone()
            if row is None:
                return None
            return self._row_to_entry(row)

    def get_all(self) -> List[GlossaryEntry]:
        with self._pool.connection() as conn:
            cur = conn.execute("SELECT * FROM glossary_terms ORDER BY term")
            return [self._row_to_entry(row) for row in cur.fetchall()]

    def create(self, entity: GlossaryEntry) -> GlossaryEntry:
        with self._pool.connection() as conn:
            cur = conn.execute(
                """
                INSERT INTO glossary_terms (
                    work_id, term, translation, notes, is_proper_noun, entity_type,
                    do_not_translate, is_verified, confidence, context, frequency,
                    source_lang, target_lang
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                RETURNING *
                """,
                (
                    entity.work_id,
                    entity.term,
                    entity.translation,
                    entity.notes,
                    entity.is_proper_noun,
                    entity.entity_type,
                    entity.do_not_translate,
                    entity.is_verified,
                    entity.confidence,
                    entity.context,
                    entity.frequency,
                    entity.source_lang,
                    entity.target_lang,
                ),
            )
            row = cur.fetchone()
            return self._row_to_entry(row)

    def update(self, entity: GlossaryEntry) -> Optional[GlossaryEntry]:
        with self._pool.connection() as conn:
            cur = conn.execute(
                """
                UPDATE glossary_terms SET
                    work_id = ?, term = ?, translation = ?, notes = ?,
                    is_proper_noun = ?, entity_type = ?, do_not_translate = ?,
                    is_verified = ?, confidence = ?, context = ?, frequency = ?,
                    source_lang = ?, target_lang = ?
                WHERE id = ?
                RETURNING *
                """,
                (
                    entity.work_id,
                    entity.term,
                    entity.translation,
                    entity.notes,
                    entity.is_proper_noun,
                    entity.entity_type,
                    entity.do_not_translate,
                    entity.is_verified,
                    entity.confidence,
                    entity.context,
                    entity.frequency,
                    entity.source_lang,
                    entity.target_lang,
                    entity.id,
                ),
            )
            row = cur.fetchone()
            if row is None:
                return None
            return self._row_to_entry(row)

    def delete(self, id: int) -> bool:
        with self._pool.connection() as conn:
            cur = conn.execute("DELETE FROM glossary_terms WHERE id = ?", (id,))
            return cur.rowcount > 0

    def get_by_work_id(self, work_id: int) -> List[GlossaryEntry]:
        """Get all glossary terms for a specific work."""
        with self._pool.connection() as conn:
            cur = conn.execute(
                "SELECT * FROM glossary_terms WHERE work_id = ? ORDER BY term",
                (work_id,),
            )
            return [self._row_to_entry(row) for row in cur.fetchall()]

    def find_by_term(self, work_id: int, term: str) -> Optional[GlossaryEntry]:
        """Find a glossary term by exact match."""
        with self._pool.connection() as conn:
            cur = conn.execute(
                "SELECT * FROM glossary_terms WHERE work_id = ? AND term = ?",
                (work_id, term),
            )
            row = cur.fetchone()
            if row is None:
                return None
            return self._row_to_entry(row)

    def search_terms(self, work_id: int, query: str, limit: int = 50) -> List[GlossaryEntry]:
        """Search glossary terms using LIKE (replaces pg_trgm)."""
        with self._pool.connection() as conn:
            cur = conn.execute(
                """
                SELECT * FROM glossary_terms
                WHERE work_id = ? AND term LIKE ?
                ORDER BY term
                LIMIT ?
                """,
                (work_id, f"%{query}%", limit),
            )
            return [self._row_to_entry(row) for row in cur.fetchall()]

    def get_verified_terms(self, work_id: int) -> List[GlossaryEntry]:
        """Get all verified terms for a work."""
        with self._pool.connection() as conn:
            cur = conn.execute(
                "SELECT * FROM glossary_terms WHERE work_id = ? AND is_verified = 1 ORDER BY term",
                (work_id,),
            )
            return [self._row_to_entry(row) for row in cur.fetchall()]

    def get_do_not_translate_terms(self, work_id: int) -> List[GlossaryEntry]:
        """Get all terms marked as do_not_translate."""
        with self._pool.connection() as conn:
            cur = conn.execute(
                "SELECT * FROM glossary_terms WHERE work_id = ? AND do_not_translate = 1 ORDER BY term",
                (work_id,),
            )
            return [self._row_to_entry(row) for row in cur.fetchall()]

    def bulk_upsert_terms(self, terms: List[GlossaryEntry]) -> int:
        """Insert or update multiple terms efficiently."""
        if not terms:
            return 0
        with self._pool.connection() as conn:
            count = 0
            for term in terms:
                existing = self.find_by_term(term.work_id, term.term)
                if existing:
                    term.id = existing.id
                    self.update(term)
                else:
                    self.create(term)
                count += 1
            return count

    # Term Contexts
    def add_context(self, context: TermContext) -> TermContext:
        with self._pool.connection() as conn:
            cur = conn.execute(
                """
                INSERT INTO term_contexts (term_id, context_hint, translation, example_usage)
                VALUES (?, ?, ?, ?)
                RETURNING id, term_id, context_hint, translation, example_usage, created_at
                """,
                (
                    context.term_id,
                    context.context_hint,
                    context.translation,
                    context.example_usage,
                ),
            )
            row = cur.fetchone()
            return self._row_to_context(row)

    def get_contexts(self, term_id: int) -> List[TermContext]:
        with self._pool.connection() as conn:
            cur = conn.execute(
                "SELECT * FROM term_contexts WHERE term_id = ? ORDER BY id",
                (term_id,),
            )
            return [self._row_to_context(row) for row in cur.fetchall()]

    def update_context(self, context: TermContext) -> Optional[TermContext]:
        with self._pool.connection() as conn:
            cur = conn.execute(
                """
                UPDATE term_contexts SET
                    context_hint = ?, translation = ?, example_usage = ?
                WHERE id = ?
                RETURNING id, term_id, context_hint, translation, example_usage, created_at
                """,
                (
                    context.context_hint,
                    context.translation,
                    context.example_usage,
                    context.id,
                ),
            )
            row = cur.fetchone()
            if row is None:
                return None
            return self._row_to_context(row)

    def delete_context(self, context_id: int) -> bool:
        with self._pool.connection() as conn:
            cur = conn.execute("DELETE FROM term_contexts WHERE id = ?", (context_id,))
            return cur.rowcount > 0

    # Context Examples
    def add_example(self, example: ContextExample) -> ContextExample:
        with self._pool.connection() as conn:
            cur = conn.execute(
                """
                INSERT INTO context_examples (context_id, original_sentence, translated_sentence, chapter_id)
                VALUES (?, ?, ?, ?)
                RETURNING id, context_id, original_sentence, translated_sentence, chapter_id, created_at
                """,
                (
                    example.context_id,
                    example.original_sentence,
                    example.translated_sentence,
                    example.chapter_id,
                ),
            )
            row = cur.fetchone()
            return self._row_to_example(row)

    def get_examples(self, context_id: int) -> List[ContextExample]:
        with self._pool.connection() as conn:
            cur = conn.execute(
                "SELECT * FROM context_examples WHERE context_id = ? ORDER BY id",
                (context_id,),
            )
            return [self._row_to_example(row) for row in cur.fetchall()]

    def update_example(self, example: ContextExample) -> Optional[ContextExample]:
        with self._pool.connection() as conn:
            cur = conn.execute(
                """
                UPDATE context_examples SET
                    original_sentence = ?, translated_sentence = ?, chapter_id = ?
                WHERE id = ?
                RETURNING id, context_id, original_sentence, translated_sentence, chapter_id, created_at
                """,
                (
                    example.original_sentence,
                    example.translated_sentence,
                    example.chapter_id,
                    example.id,
                ),
            )
            row = cur.fetchone()
            if row is None:
                return None
            return self._row_to_example(row)

    def delete_example(self, example_id: int) -> bool:
        with self._pool.connection() as conn:
            cur = conn.execute("DELETE FROM context_examples WHERE id = ?", (example_id,))
            return cur.rowcount > 0

    def search_terms_with_rerank(
        self, query: str, work_id: int, top_n: int = 10
    ) -> List[GlossaryEntry]:
        """
        Search terms using fuzzy search + semantic reranking.
        """
        candidates = self.search_terms(work_id, query, limit=top_n * 2)

        if not candidates:
            return []

        docs = [
            Document(page_content=f"{entry.term}: {entry.translation or ''}")
            for entry in candidates
        ]

        reranked = self._vector_service.rerank_documents(
            query=query, documents=docs, top_n=top_n
        )

        reranked_terms = [doc.page_content.split(":")[0] for doc in reranked]

        return [e for e in candidates if e.term in reranked_terms]

    def filter_new_entities(self, candidates: list, work_id: int) -> list:
        existing_terms = self._get_existing_terms(work_id)
        return [c for c in candidates if c.text.lower() not in existing_terms]

    def _get_existing_terms(self, work_id: int) -> set:
        with self._pool.connection() as conn:
            cur = conn.execute(
                "SELECT LOWER(term) FROM glossary_terms WHERE work_id = ?",
                (work_id,),
            )
            return {row[0] for row in cur.fetchall()}

    def batch_create_with_embeddings(
        self,
        entries: list,
        work_id: int,
        source_language: str,
        target_language: str,
    ) -> List[GlossaryEntry]:
        """Batch create glossary entries (embeddings handled by vector store)."""
        results = []
        for entry, embedding in entries:
            glossary_entry = GlossaryEntry(
                work_id=work_id,
                term=entry.text,
                translation=getattr(entry, "translation", None),
                entity_type=entry.entity_type,
                is_proper_noun=False,
                frequency=entry.frequency,
                source_lang=source_language,
                target_lang=target_language,
            )
            created = self.create(glossary_entry)
            results.append(created)
        return results