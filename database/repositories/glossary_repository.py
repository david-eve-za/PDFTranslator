from typing import Optional, List
from psycopg_pool import ConnectionPool
import numpy as np

from database.repositories.base import BaseRepository
from database.models import GlossaryEntry, TermContext, ContextExample
from database.services.vector_store import VectorStoreService
from langchain_core.documents import Document


class GlossaryRepository(BaseRepository[GlossaryEntry]):
    def __init__(
        self,
        host: str,
        port: int,
        database: str,
        user: str,
        password: str,
        min_size: int = 2,
        max_size: int = 10,
    ):
        self._conninfo = (
            f"dbname={database} "
            f"user={user} "
            f"password='{password}' "
            f"host={host} "
            f"port={port}"
        )
        self._pool: Optional[ConnectionPool] = None
        self._min_size = min_size
        self._max_size = max_size
        self._vector_service = VectorStoreService()

    def _get_pool(self) -> ConnectionPool:
        if self._pool is None:
            self._pool = ConnectionPool(
                conninfo=self._conninfo,
                min_size=self._min_size,
                max_size=self._max_size,
                open=True,
            )
        return self._pool

    def _row_to_glossary_entry(self, row: tuple) -> GlossaryEntry:
        return GlossaryEntry(
            id=row[0],
            work_id=row[1],
            term=row[2],
            translation=row[3],
            notes=row[4],
            is_proper_noun=row[5],
            embedding=row[6] if len(row) > 6 and row[6] is not None else None,
            contexts=[],
        )

    def _row_to_term_context(self, row: tuple) -> TermContext:
        return TermContext(
            id=row[0],
            term_id=row[1],
            context_hint=row[2],
            translation=row[3],
            example_usage=row[4] if len(row) > 4 else None,
            examples=[],
        )

    def _row_to_context_example(self, row: tuple) -> ContextExample:
        return ContextExample(
            id=row[0],
            context_id=row[1],
            original_sentence=row[2],
            translated_sentence=row[3],
            chapter_id=row[4] if len(row) > 4 else None,
        )

    def get_by_id(self, id: int) -> Optional[GlossaryEntry]:
        pool = self._get_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, work_id, term, translation, notes, is_proper_noun, embedding
                    FROM glossary_entries
                    WHERE id = %s
                    """,
                    (id,),
                )
                row = cur.fetchone()
                if row is None:
                    return None
                entry = self._row_to_glossary_entry(row)
                entry.contexts = self.get_contexts(id)
                return entry

    def get_all(self) -> List[GlossaryEntry]:
        pool = self._get_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, work_id, term, translation, notes, is_proper_noun, embedding
                    FROM glossary_entries
                    ORDER BY term
                    """
                )
                rows = cur.fetchall()
                return [self._row_to_glossary_entry(row) for row in rows]

    def create(self, entity: GlossaryEntry) -> GlossaryEntry:
        pool = self._get_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO glossary_entries (work_id, term, translation, notes, is_proper_noun, embedding)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id, work_id, term, translation, notes, is_proper_noun, embedding
                    """,
                    (
                        entity.work_id,
                        entity.term,
                        entity.translation,
                        entity.notes,
                        entity.is_proper_noun,
                        entity.embedding.tolist()
                        if entity.embedding is not None
                        else None,
                    ),
                )
                row = cur.fetchone()
                return self._row_to_glossary_entry(row)

    def update(self, entity: GlossaryEntry) -> GlossaryEntry:
        pool = self._get_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE glossary_entries
                    SET work_id = %s, term = %s, translation = %s, notes = %s,
                    is_proper_noun = %s, embedding = %s
                    WHERE id = %s
                    RETURNING id, work_id, term, translation, notes, is_proper_noun, embedding
                    """,
                    (
                        entity.work_id,
                        entity.term,
                        entity.translation,
                        entity.notes,
                        entity.is_proper_noun,
                        entity.embedding.tolist()
                        if entity.embedding is not None
                        else None,
                        entity.id,
                    ),
                )
                row = cur.fetchone()
                if row is None:
                    return None
                return self._row_to_glossary_entry(row)

    def delete(self, id: int) -> bool:
        pool = self._get_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM glossary_entries WHERE id = %s", (id,))
                return cur.rowcount > 0

    def get_by_work(self, work_id: int) -> List[GlossaryEntry]:
        pool = self._get_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, work_id, term, translation, notes, is_proper_noun, embedding
                    FROM glossary_entries
                    WHERE work_id = %s
                    ORDER BY term
                    """,
                    (work_id,),
                )
                rows = cur.fetchall()
                return [self._row_to_glossary_entry(row) for row in rows]

    def find_by_term(
        self, term: str, work_id: Optional[int] = None, fuzzy: bool = False
    ) -> List[GlossaryEntry]:
        pool = self._get_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                if fuzzy:
                    if work_id is not None:
                        cur.execute(
                            """
                            SELECT id, work_id, term, translation, notes, is_proper_noun, embedding
                            FROM glossary_entries
                            WHERE work_id = %s AND term % %s
                            ORDER BY similarity(term, %s) DESC
                            """,
                            (work_id, term, term),
                        )
                    else:
                        cur.execute(
                            """
                            SELECT id, work_id, term, translation, notes, is_proper_noun, embedding
                            FROM glossary_entries
                            WHERE term % %s
                            ORDER BY similarity(term, %s) DESC
                            """,
                            (term, term),
                        )
                else:
                    if work_id is not None:
                        cur.execute(
                            """
                            SELECT id, work_id, term, translation, notes, is_proper_noun, embedding
                            FROM glossary_entries
                            WHERE work_id = %s AND term = %s
                            """,
                            (work_id, term),
                        )
                    else:
                        cur.execute(
                            """
                            SELECT id, work_id, term, translation, notes, is_proper_noun, embedding
                            FROM glossary_entries
                            WHERE term = %s
                            """,
                            (term,),
                        )
                rows = cur.fetchall()
                return [self._row_to_glossary_entry(row) for row in rows]

    def find_similar_terms(
        self,
        embedding: np.ndarray,
        work_id: Optional[int] = None,
        limit: int = 10,
        threshold: float = 0.8,
    ) -> List[GlossaryEntry]:
        pool = self._get_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                if work_id is not None:
                    cur.execute(
                        """
                        SELECT id, work_id, term, translation, notes, is_proper_noun, embedding,
                        1 - (embedding <=> %s) as similarity
                        FROM glossary_entries
                        WHERE work_id = %s AND embedding IS NOT NULL
                        ORDER BY embedding <=> %s
                        LIMIT %s
                        """,
                        (embedding.tolist(), work_id, embedding.tolist(), limit),
                    )
                else:
                    cur.execute(
                        """
                        SELECT id, work_id, term, translation, notes, is_proper_noun, embedding,
                        1 - (embedding <=> %s) as similarity
                        FROM glossary_entries
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
                        results.append(self._row_to_glossary_entry(row[:7]))
                return results

    def add_context(self, term_id: int, context: TermContext) -> TermContext:
        pool = self._get_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO term_contexts (term_id, context_hint, translation, example_usage)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id, term_id, context_hint, translation, example_usage
                    """,
                    (
                        term_id,
                        context.context_hint,
                        context.translation,
                        context.example_usage,
                    ),
                )
                row = cur.fetchone()
                return self._row_to_term_context(row)

    def get_contexts(self, term_id: int) -> List[TermContext]:
        pool = self._get_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, term_id, context_hint, translation, example_usage
                    FROM term_contexts
                    WHERE term_id = %s
                    ORDER BY context_hint
                    """,
                    (term_id,),
                )
                rows = cur.fetchall()
                contexts = [self._row_to_term_context(row) for row in rows]
                for ctx in contexts:
                    ctx.examples = self.get_examples(ctx.id)
                return contexts

    def update_context(self, context: TermContext) -> TermContext:
        pool = self._get_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE term_contexts
                    SET context_hint = %s, translation = %s, example_usage = %s
                    WHERE id = %s
                    RETURNING id, term_id, context_hint, translation, example_usage
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
                return self._row_to_term_context(row)

    def delete_context(self, context_id: int) -> bool:
        pool = self._get_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM term_contexts WHERE id = %s", (context_id,))
                return cur.rowcount > 0

    def add_example(self, context_id: int, example: ContextExample) -> ContextExample:
        pool = self._get_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO context_examples (context_id, original_sentence, translated_sentence, chapter_id)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id, context_id, original_sentence, translated_sentence, chapter_id
                    """,
                    (
                        context_id,
                        example.original_sentence,
                        example.translated_sentence,
                        example.chapter_id,
                    ),
                )
                row = cur.fetchone()
                return self._row_to_context_example(row)

    def get_examples(self, context_id: int) -> List[ContextExample]:
        pool = self._get_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, context_id, original_sentence, translated_sentence, chapter_id
                    FROM context_examples
                    WHERE context_id = %s
                    ORDER BY id
                    """,
                    (context_id,),
                )
                rows = cur.fetchall()
                return [self._row_to_context_example(row) for row in rows]

    def update_example(self, example: ContextExample) -> ContextExample:
        pool = self._get_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE context_examples
                    SET original_sentence = %s, translated_sentence = %s, chapter_id = %s
                    WHERE id = %s
                    RETURNING id, context_id, original_sentence, translated_sentence, chapter_id
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
                return self._row_to_context_example(row)

    def delete_example(self, example_id: int) -> bool:
        pool = self._get_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM context_examples WHERE id = %s", (example_id,))
                return cur.rowcount > 0

    def search_terms_with_rerank(
        self, query: str, work_id: int, top_n: int = 10
    ) -> List[GlossaryEntry]:
        """
        Busca términos usando fuzzy search + reranking semántico.

        Args:
            query: Consulta de búsqueda
            work_id: ID de la obra
            top_n: Número máximo de resultados

        Returns:
            Lista de términos rerankeados por relevancia
        """
        candidates = self.find_by_term(query, work_id=work_id, fuzzy=True)[: top_n * 2]

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
