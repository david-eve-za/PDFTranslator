"""Chapter repository for SQLite."""

import logging
import numpy as np
from typing import Optional, List
from datetime import datetime

from pdftranslator.database.connection import DatabasePool
from pdftranslator.database.repositories.base import BaseRepository
from pdftranslator.database.models import Chapter
from pdftranslator.database.services.vector_store import VectorStoreService
from langchain_core.documents import Document

logger = logging.getLogger(__name__)


class ChapterRepository(BaseRepository[Chapter]):
    def __init__(self, pool: Optional[DatabasePool] = None):
        self._pool = pool or DatabasePool.get_instance()
        self._vector_service = VectorStoreService()

    def _parse_datetime(self, value) -> Optional[datetime]:
        """Parse datetime from SQLite string format."""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        try:
            # SQLite uses "YYYY-MM-DD HH:MM:SS" format (space), not ISO "T" separator
            # Also handle potential "Z" suffix
            value_str = str(value).strip()
            # Replace space with T for ISO format parsing
            if " " in value_str and "T" not in value_str:
                value_str = value_str.replace(" ", "T")
            if value_str.endswith("Z"):
                value_str = value_str[:-1] + "+00:00"
            return datetime.fromisoformat(value_str)
        except (ValueError, AttributeError):
            return None

    def _row_to_chapter(self, row) -> Chapter:
        return Chapter(
            id=row["id"],
            volume_id=row["volume_id"],
            chapter_number=row["chapter_number"],
            title=row["title"],
            start_position=row["start_position"] if "start_position" in row.keys() and row["start_position"] is not None else None,
            end_position=row["end_position"] if "end_position" in row.keys() and row["end_position"] is not None else None,
            original_text=row["original_text"] if "original_text" in row.keys() else None,
            translated_text=row["translated_text"] if "translated_text" in row.keys() else None,
            created_at=self._parse_datetime(row["created_at"]) if "created_at" in row.keys() else None,
        )

    def get_by_id(self, id: int) -> Optional[Chapter]:
        with self._pool.connection() as conn:
            cur = conn.execute(
                """
                SELECT id, volume_id, chapter_number, title, start_position,
                       end_position, original_text, translated_text
                FROM chapters
                WHERE id = ?
                """,
                (id,),
            )
            row = cur.fetchone()
            if row is None:
                return None
            return self._row_to_chapter(row)

    def get_all(self) -> List[Chapter]:
        with self._pool.connection() as conn:
            cur = conn.execute(
                """
                SELECT id, volume_id, chapter_number, title, start_position,
                       end_position, original_text, translated_text
                FROM chapters
                ORDER BY volume_id, chapter_number NULLS FIRST
                """
            )
            rows = cur.fetchall()
            return [self._row_to_chapter(row) for row in rows]

    def create(self, entity: Chapter) -> Chapter:
        with self._pool.connection() as conn:
            cur = conn.execute(
                """
                INSERT INTO chapters (volume_id, chapter_number, title,
                                     start_position, end_position,
                                     original_text, translated_text)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                RETURNING id, volume_id, chapter_number, title, start_position,
                          end_position, original_text, translated_text
                """,
                (
                    entity.volume_id,
                    entity.chapter_number,
                    entity.title,
                    entity.start_position,
                    entity.end_position,
                    entity.original_text,
                    entity.translated_text,
                ),
            )
            row = cur.fetchone()
            return self._row_to_chapter(row)

    def update(self, entity: Chapter) -> Optional[Chapter]:
        with self._pool.connection() as conn:
            cur = conn.execute(
                """
                UPDATE chapters
                SET volume_id = ?, chapter_number = ?, title = ?,
                    start_position = ?, end_position = ?,
                    original_text = ?, translated_text = ?
                WHERE id = ?
                RETURNING id, volume_id, chapter_number, title, start_position,
                          end_position, original_text, translated_text
                """,
                (
                    entity.volume_id,
                    entity.chapter_number,
                    entity.title,
                    entity.start_position,
                    entity.end_position,
                    entity.original_text,
                    entity.translated_text,
                    entity.id,
                ),
            )
            row = cur.fetchone()
            if row is None:
                return None
            return self._row_to_chapter(row)

    def delete(self, id: int) -> bool:
        with self._pool.connection() as conn:
            cur = conn.execute("DELETE FROM chapters WHERE id = ?", (id,))
            return cur.rowcount > 0

    def get_by_volume(self, volume_id: int) -> List[Chapter]:
        with self._pool.connection() as conn:
            cur = conn.execute(
                """
                SELECT id, volume_id, chapter_number, title, start_position,
                       end_position, original_text, translated_text
                FROM chapters
                WHERE volume_id = ?
                ORDER BY chapter_number NULLS FIRST
                """,
                (volume_id,),
            )
            rows = cur.fetchall()
            return [self._row_to_chapter(row) for row in rows]

    def search_content(
        self, volume_id: int, query: str, limit: int = 10
    ) -> List[Chapter]:
        """
        Search chapters by content using Python-side fuzzy matching.
        Since SQLite doesn't have pg_trgm, we fetch all and filter in Python.
        """
        chapters = self.get_by_volume(volume_id)
        if not chapters:
            return []

        # Use rapidfuzz for fuzzy matching
        from rapidfuzz import fuzz, process

        results = []
        for chapter in chapters:
            if chapter.original_text:
                score = fuzz.partial_ratio(query.lower(), chapter.original_text.lower())
                if score > 50:  # threshold
                    results.append((chapter, score))

        results.sort(key=lambda x: x[1], reverse=True)
        return [c for c, _ in results[:limit]]

    def find_similar(
        self,
        embedding: np.ndarray,
        volume_id: Optional[int] = None,
        limit: int = 10,
        threshold: float = 0.8,
    ) -> List[Chapter]:
        """
        Find chapters similar to the given embedding using Python-side cosine similarity.
        """
        chapters = self.get_by_volume(volume_id) if volume_id else self.get_all()
        if not chapters:
            return []

        # Filter chapters with embeddings
        chapters_with_emb = [c for c in chapters if c.embedding is not None]
        if not chapters_with_emb:
            return []

        # Compute cosine similarity in Python
        query_vec = np.array(embedding)
        doc_vecs = np.array([c.embedding for c in chapters_with_emb])

        query_norm = query_vec / np.linalg.norm(query_vec)
        doc_norms = doc_vecs / np.linalg.norm(doc_vecs, axis=1, keepdims=True)
        similarities = np.dot(doc_norms, query_norm)

        # Filter by threshold and sort
        results = [(chapters_with_emb[i], similarities[i]) for i in range(len(similarities))
                   if similarities[i] >= threshold]
        results.sort(key=lambda x: x[1], reverse=True)

        return [c for c, _ in results[:limit]]

    def search_with_rerank(
        self, query: str, volume_id: int, top_n: int = 5
    ) -> List[Chapter]:
        chapters = self.get_by_volume(volume_id)
        if not chapters:
            return []

        chapters_with_text = [c for c in chapters if c.original_text]
        if not chapters_with_text:
            return []

        docs = [Document(page_content=c.original_text) for c in chapters_with_text]

        reranked = self._vector_service.rerank_documents(
            query=query, documents=docs, top_n=top_n
        )

        reranked_texts = [d.page_content for d in reranked]

        return [c for c in chapters_with_text if c.original_text in reranked_texts]