from typing import Optional, List

from database.connection import DatabasePool
from database.repositories.base import BaseRepository
from database.models import Work, Volume
from database.services.vector_store import VectorStoreService


class BookRepository(BaseRepository[Work]):
    def _row_to_work(self, row: tuple) -> Work:
        return Work(
            id=row[0],
            title=row[1],
            title_translated=row[2],
            source_lang=row[3],
            target_lang=row[4],
            author=row[5],
        )

    def _row_to_volume(self, row: tuple) -> Volume:
        return Volume(
            id=row[0],
            work_id=row[1],
            volume_number=row[2],
            title=row[3],
            full_text=row[4],
            translated_text=row[5],
        )

    def __init__(self, pool: Optional[DatabasePool] = None):
        self._pool = pool or DatabasePool.get_instance()
        self._vector_service = VectorStoreService()

    def get_by_id(self, id: int) -> Optional[Work]:
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, title, title_translated, source_lang, target_lang, author
                    FROM works
                    WHERE id = %s
                    """,
                    (id,),
                )
                row = cur.fetchone()
                if row is None:
                    return None
                return self._row_to_work(row)

    def get_all(self) -> List[Work]:
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, title, title_translated, source_lang, target_lang, author
                    FROM works
                    ORDER BY id
                    """
                )
                rows = cur.fetchall()
                return [self._row_to_work(row) for row in rows]

    def create(self, entity: Work) -> Work:
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO works (title, title_translated, source_lang, target_lang, author)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id, title, title_translated, source_lang, target_lang, author
                    """,
                    (
                        entity.title,
                        entity.title_translated,
                        entity.source_lang,
                        entity.target_lang,
                        entity.author,
                    ),
                )
                row = cur.fetchone()
                return self._row_to_work(row)

    def update(self, entity: Work) -> Optional[Work]:
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE works
                    SET title = %s, title_translated = %s, source_lang = %s, target_lang = %s, author = %s
                    WHERE id = %s
                    RETURNING id, title, title_translated, source_lang, target_lang, author
                    """,
                    (
                        entity.title,
                        entity.title_translated,
                        entity.source_lang,
                        entity.target_lang,
                        entity.author,
                        entity.id,
                    ),
                )
                row = cur.fetchone()
                if row is None:
                    return None
                return self._row_to_work(row)

    def delete(self, id: int) -> bool:
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM works WHERE id = %s", (id,))
                return cur.rowcount > 0

    def get_volumes(self, work_id: int) -> List[Volume]:
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, work_id, volume_number, title, full_text, translated_text
                    FROM volumes
                    WHERE work_id = %s
                    ORDER BY volume_number
                    """,
                    (work_id,),
                )
                rows = cur.fetchall()
                return [self._row_to_volume(row) for row in rows]

    def add_volume(self, volume: Volume) -> Volume:
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO volumes (work_id, volume_number, title, full_text, translated_text)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id, work_id, volume_number, title, full_text, translated_text
                    """,
                    (
                        volume.work_id,
                        volume.volume_number,
                        volume.title,
                        volume.full_text,
                        volume.translated_text,
                    ),
                )
                row = cur.fetchone()
                return self._row_to_volume(row)

    def find_by_title(self, title: str, fuzzy: bool = False) -> List[Work]:
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                if fuzzy:
                    cur.execute(
                        """
                        SELECT id, title, title_translated, source_lang, target_lang, author
                        FROM works
                        WHERE title % %s
                        ORDER BY similarity(title, %s) DESC
                        """,
                        (title, title),
                    )
                else:
                    cur.execute(
                        """
                        SELECT id, title, title_translated, source_lang, target_lang, author
                        FROM works
                        WHERE title = %s
                        ORDER BY id
                        """,
                        (title,),
                    )
                rows = cur.fetchall()
                return [self._row_to_work(row) for row in rows]

    def find_similar_works(self, query: str, top_k: int = 5) -> List[Work]:
        """
        Busca obras similares usando embeddings semánticos.

        Args:
            query: Consulta de búsqueda
            top_k: Número máximo de resultados

        Returns:
            Lista de obras más similares
        """
        query_embedding = self._vector_service.embed_query(query)
        works = self.get_all()
        if not works:
            return []
        titles = [w.title for w in works]
        title_embeddings = self._vector_service.embed_documents(titles)
        indices = self._vector_service.find_most_similar(
            query_embedding, title_embeddings, top_k
        )
        return [works[i] for i in indices]
