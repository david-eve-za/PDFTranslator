"""Book/Work repository for SQLite."""

from typing import Optional, List

from pdftranslator.database.connection import DatabasePool
from pdftranslator.database.repositories.base import BaseRepository
from pdftranslator.database.models import Work
from pdftranslator.database.services.vector_store import VectorStoreService


class BookRepository(BaseRepository[Work]):
    def _row_to_work(self, row: tuple) -> Work:
        return Work(
            id=row[0],
            title=row[1],
            title_translated=row[2],
            source_lang=row[3],
            target_lang=row[4],
            author=row[5] if len(row) > 5 else None,
        )

    def __init__(self, pool: Optional[DatabasePool] = None):
        self._pool = pool or DatabasePool.get_instance()
        self._vector_service = VectorStoreService()

    def get_by_id(self, id: int) -> Optional[Work]:
        with self._pool.connection() as conn:
            cur = conn.execute(
                """
                SELECT id, title, title_translated, source_lang, target_lang, author
                FROM works
                WHERE id = ?
                """,
                (id,),
            )
            row = cur.fetchone()
            if row is None:
                return None
            return self._row_to_work(row)

    def get_all(self) -> List[Work]:
        with self._pool.connection() as conn:
            cur = conn.execute(
                """
                SELECT id, title, title_translated, source_lang, target_lang, author
                FROM works
                ORDER BY id
                """
            )
            rows = cur.fetchall()
            return [self._row_to_work(row) for row in rows]

    def create(self, entity: Work) -> Work:
        with self._pool.connection() as conn:
            cur = conn.execute(
                """
                INSERT INTO works (title, title_translated, source_lang, target_lang, author)
                VALUES (?, ?, ?, ?, ?)
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
        with self._pool.connection() as conn:
            cur = conn.execute(
                """
                UPDATE works
                SET title = ?, title_translated = ?, source_lang = ?, target_lang = ?, author = ?
                WHERE id = ?
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
        with self._pool.connection() as conn:
            cur = conn.execute("DELETE FROM works WHERE id = ?", (id,))
            return cur.rowcount > 0

    def find_by_title(self, title: str, fuzzy: bool = False) -> List[Work]:
        with self._pool.connection() as conn:
            if fuzzy:
                # Use LIKE for fuzzy search in SQLite
                cur = conn.execute(
                    """
                    SELECT id, title, title_translated, source_lang, target_lang, author
                    FROM works
                    WHERE title LIKE ?
                    ORDER BY title
                    """,
                    (f"%{title}%",),
                )
            else:
                cur = conn.execute(
                    """
                    SELECT id, title, title_translated, source_lang, target_lang, author
                    FROM works
                    WHERE title = ?
                    ORDER BY id
                    """,
                    (title,),
                )
            rows = cur.fetchall()
            return [self._row_to_work(row) for row in rows]

    def find_similar_works(self, query: str, top_k: int = 5) -> List[Work]:
        """
        Search for similar works using embeddings (Python-level cosine similarity).
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

    def find_all(self) -> List[Work]:
        """Returns all works in the database."""
        with self._pool.connection() as conn:
            cur = conn.execute(
                "SELECT id, title, title_translated, source_lang, target_lang, author FROM works"
            )
            rows = cur.fetchall()
            return [self._row_to_work(row) for row in rows]