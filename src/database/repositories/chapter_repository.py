from typing import Optional, List
import numpy as np

from src.database.connection import DatabasePool
from src.database.repositories.base import BaseRepository
from src.database.models import Chapter
from src.database.services.vector_store import VectorStoreService
from langchain_core.documents import Document


class ChapterRepository(BaseRepository[Chapter]):
    def __init__(self, pool: Optional[DatabasePool] = None):
        self._pool = pool or DatabasePool.get_instance()
        self._vector_service = VectorStoreService()

    def _row_to_chapter(self, row: tuple) -> Chapter:
        return Chapter(
            id=row[0],
            volume_id=row[1],
            chapter_number=row[2],
            title=row[3],
            original_text=row[4],
            translated_text=row[5],
        )

    def get_by_id(self, id: int) -> Optional[Chapter]:
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, volume_id, chapter_number, title, original_text,
                    translated_text
                    FROM chapters
                    WHERE id = %s
                    """,
                    (id,),
                )
                row = cur.fetchone()
                if row is None:
                    return None
                return self._row_to_chapter(row)

    def get_all(self) -> List[Chapter]:
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, volume_id, chapter_number, title, original_text,
                    translated_text
                    FROM chapters
                    ORDER BY volume_id, chapter_number NULLS FIRST
                    """
                )
                rows = cur.fetchall()
                return [self._row_to_chapter(row) for row in rows]

    def create(self, entity: Chapter) -> Chapter:
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO chapters (volume_id, chapter_number, title,
                    original_text, translated_text)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id, volume_id, chapter_number, title, original_text,
                    translated_text
                    """,
                    (
                        entity.volume_id,
                        entity.chapter_number,
                        entity.title,
                        entity.original_text,
                        entity.translated_text,
                    ),
                )
                row = cur.fetchone()
                return self._row_to_chapter(row)

    def update(self, entity: Chapter) -> Chapter:
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE chapters
                    SET volume_id = %s, chapter_number = %s, title = %s,
                    original_text = %s, translated_text = %s
                    WHERE id = %s
                    RETURNING id, volume_id, chapter_number, title, original_text,
                    translated_text
                    """,
                    (
                        entity.volume_id,
                        entity.chapter_number,
                        entity.title,
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
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM chapters WHERE id = %s", (id,))
                return cur.rowcount > 0

    def get_by_volume(self, volume_id: int) -> List[Chapter]:
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, volume_id, chapter_number, title, original_text,
                    translated_text
                    FROM chapters
                    WHERE volume_id = %s
                    ORDER BY chapter_number NULLS FIRST
                    """,
                    (volume_id,),
                )
                rows = cur.fetchall()
                return [self._row_to_chapter(row) for row in rows]

    def search_content(
        self, volume_id: int, query: str, limit: int = 10
    ) -> List[Chapter]:
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, volume_id, chapter_number, title, original_text,
                    translated_text
                    FROM chapters
                    WHERE volume_id = %s
                    AND (original_text % %s OR title % %s)
                    ORDER BY GREATEST(similarity(original_text, %s), similarity(title, %s)) DESC
                    LIMIT %s
                    """,
                    (volume_id, query, query, query, query, limit),
                )
                rows = cur.fetchall()
                return [self._row_to_chapter(row) for row in rows]

    def find_similar(
        self,
        embedding: np.ndarray,
        volume_id: Optional[int] = None,
        limit: int = 10,
        threshold: float = 0.8,
    ) -> List[Chapter]:
        """Find chapters similar to the given embedding using vector similarity."""
        # Note: The new Chapter model doesn't have embedding field
        # This method would need a separate embedding table or the database
        # schema to include embedding. For now, return empty list.
        # TODO: Implement when embedding storage is clarified
        return []

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
