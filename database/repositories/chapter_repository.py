from typing import Optional, List
from psycopg_pool import ConnectionPool
import numpy as np

from database.repositories.base import BaseRepository
from database.models import Chapter
from database.services.vector_store import VectorStoreService
from langchain_core.documents import Document


class ChapterRepository(BaseRepository[Chapter]):
    def __init__(self, dsn: str, min_size: int = 2, max_size: int = 10):
        self._dsn = dsn
        self._pool: Optional[ConnectionPool] = None
        self._min_size = min_size
        self._max_size = max_size
        self._vector_service = VectorStoreService()

    def _get_pool(self) -> ConnectionPool:
        if self._pool is None:
            self._pool = ConnectionPool(
                conninfo=self._dsn,
                min_size=self._min_size,
                max_size=self._max_size,
                open=True,
            )
        return self._pool

    def _row_to_chapter(self, row: tuple) -> Chapter:
        return Chapter(
            id=row[0],
            volume_id=row[1],
            chapter_number=row[2],
            title=row[3],
            original_text=row[4],
            translated_text=row[5],
            embedding=row[6] if len(row) > 6 else None,
        )

    def get_by_id(self, id: int) -> Optional[Chapter]:
        pool = self._get_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, volume_id, chapter_number, title, original_text,
                           translated_text, embedding
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
        pool = self._get_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, volume_id, chapter_number, title, original_text,
                           translated_text, embedding
                    FROM chapters
                    ORDER BY volume_id, chapter_number
                    """
                )
                rows = cur.fetchall()
                return [self._row_to_chapter(row) for row in rows]

    def create(self, entity: Chapter) -> Chapter:
        pool = self._get_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO chapters (volume_id, chapter_number, title,
                                         original_text, translated_text, embedding)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id, volume_id, chapter_number, title, original_text,
                              translated_text, embedding
                    """,
                    (
                        entity.volume_id,
                        entity.chapter_number,
                        entity.title,
                        entity.original_text,
                        entity.translated_text,
                        entity.embedding,
                    ),
                )
                row = cur.fetchone()
                return self._row_to_chapter(row)

    def update(self, entity: Chapter) -> Chapter:
        pool = self._get_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE chapters
                    SET volume_id = %s, chapter_number = %s, title = %s,
                        original_text = %s, translated_text = %s, embedding = %s
                    WHERE id = %s
                    RETURNING id, volume_id, chapter_number, title, original_text,
                              translated_text, embedding
                    """,
                    (
                        entity.volume_id,
                        entity.chapter_number,
                        entity.title,
                        entity.original_text,
                        entity.translated_text,
                        entity.embedding,
                        entity.id,
                    ),
                )
                row = cur.fetchone()
                if row is None:
                    return None
                return self._row_to_chapter(row)

    def delete(self, id: int) -> bool:
        pool = self._get_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM chapters WHERE id = %s", (id,))
                return cur.rowcount > 0

    def get_by_volume(self, volume_id: int) -> List[Chapter]:
        pool = self._get_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, volume_id, chapter_number, title, original_text,
                           translated_text, embedding
                    FROM chapters
                    WHERE volume_id = %s
                    ORDER BY chapter_number
                    """,
                    (volume_id,),
                )
                rows = cur.fetchall()
                return [self._row_to_chapter(row) for row in rows]

    def search_content(
        self, volume_id: int, query: str, limit: int = 10
    ) -> List[Chapter]:
        pool = self._get_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, volume_id, chapter_number, title, original_text,
                           translated_text, embedding
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
        pool = self._get_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                if volume_id is not None:
                    cur.execute(
                        """
                        SELECT id, volume_id, chapter_number, title, original_text,
                               translated_text, embedding,
                               1 - (embedding <=> %s) as similarity
                        FROM chapters
                        WHERE volume_id = %s AND embedding IS NOT NULL
                        ORDER BY embedding <=> %s
                        LIMIT %s
                        """,
                        (embedding.tolist(), volume_id, embedding.tolist(), limit),
                    )
                else:
                    cur.execute(
                        """
                        SELECT id, volume_id, chapter_number, title, original_text,
                               translated_text, embedding,
                               1 - (embedding <=> %s) as similarity
                        FROM chapters
                        WHERE embedding IS NOT NULL
                        ORDER BY embedding <=> %s
                        LIMIT %s
                        """,
                        (embedding.tolist(), embedding.tolist(), limit),
                    )
        rows = cur.fetchall()
        results = []
        for row in rows:
            if row[7] >= threshold:
                results.append(self._row_to_chapter(row[:7]))
        return results

    def search_with_rerank(
        self, query: str, volume_id: int, top_n: int = 5
    ) -> List[Chapter]:
        """
        Busca capítulos con reranking semántico.

        Args:
            query: Consulta de búsqueda
            volume_id: ID del volumen
            top_n: Número máximo de resultados

        Returns:
            Lista de capítulos rerankeados por relevancia
        """
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
