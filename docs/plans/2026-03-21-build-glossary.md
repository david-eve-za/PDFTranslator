# build-glossary Command Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implementar comando CLI para construir glosario de traducción usando NER + RAG + Rerank

**Architecture:** Se extiende la base de datos con nuevas tablas (entity_blacklist, fantasy_terms) y campos en glossary_terms. Se crean servicios EntityExtractor (NLTK + regex) y GlossaryManager (pipeline completo). El comando CLI procesa capítulos/volúmenes con visualización Rich.

**Tech Stack:** Python, NLTK, PostgreSQL + pgvector, NVIDIA NIM (embeddings/rerank), Typer, Rich

---

## Task 1: Extender Modelo de Datos

**Files:**
- Create: `database/schemas/007_glossary_extensions.sql`
- Create: `database/schemas/008_entity_blacklist.sql`
- Create: `database/schemas/009_fantasy_terms.sql`
- Modify: `database/models.py`

**Step 1: Crear schema 007_glossary_extensions.sql**

```sql
-- database/schemas/007_glossary_extensions.sql
-- Extender tabla glossary_terms con campos de NER

ALTER TABLE glossary_terms
ADD COLUMN IF NOT EXISTS entity_type VARCHAR(50) DEFAULT 'other';

ALTER TABLE glossary_terms
ADD COLUMN IF NOT EXISTS do_not_translate BOOLEAN DEFAULT FALSE;

ALTER TABLE glossary_terms
ADD COLUMN IF NOT EXISTS is_verified BOOLEAN DEFAULT FALSE;

ALTER TABLE glossary_terms
ADD COLUMN IF NOT EXISTS confidence FLOAT DEFAULT 0.0;

ALTER TABLE glossary_terms
ADD COLUMN IF NOT EXISTS source_language VARCHAR(10) DEFAULT 'en';

ALTER TABLE glossary_terms
ADD COLUMN IF NOT EXISTS target_language VARCHAR(10) DEFAULT 'es';

-- Índices para los nuevos campos
CREATE INDEX IF NOT EXISTS idx_glossary_entity_type ON glossary_terms(entity_type);
CREATE INDEX IF NOT EXISTS idx_glossary_verified ON glossary_terms(is_verified);
CREATE INDEX IF NOT EXISTS idx_glossary_source_lang ON glossary_terms(source_language);
```

**Step 2: Crear schema 008_entity_blacklist.sql**

```sql
-- database/schemas/008_entity_blacklist.sql
-- Tabla para términos que nunca deben tratarse como entidades

CREATE TABLE IF NOT EXISTS entity_blacklist (
    id SERIAL PRIMARY KEY,
    term VARCHAR(200) NOT NULL UNIQUE,
    reason VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Valores iniciales: stopwords en inglés y español, metadatos
INSERT INTO entity_blacklist (term, reason) VALUES
-- Stopwords inglés
('the', 'stopword'),
('and', 'stopword'),
('or', 'stopword'),
('but', 'stopword'),
('in', 'stopword'),
('on', 'stopword'),
('at', 'stopword'),
('to', 'stopword'),
('for', 'stopword'),
('of', 'stopword'),
('a', 'stopword'),
('an', 'stopword'),
('is', 'stopword'),
('was', 'stopword'),
('be', 'stopword'),
('been', 'stopword'),
('have', 'stopword'),
('had', 'stopword'),
('do', 'stopword'),
('did', 'stopword'),
-- Verbos comunes de diálogo
('said', 'stopword'),
('asked', 'stopword'),
('replied', 'stopword'),
('thought', 'stopword'),
('felt', 'stopword'),
('knew', 'stopword'),
('saw', 'stopword'),
-- Metadatos de documento
('chapter', 'metadata'),
('volume', 'metadata'),
('part', 'metadata'),
('book', 'metadata'),
('story', 'metadata'),
('novel', 'metadata'),
-- Stopwords español
('el', 'stopword'),
('la', 'stopword'),
('los', 'stopword'),
('las', 'stopword'),
('un', 'stopword'),
('una', 'stopword'),
('de', 'stopword'),
('del', 'stopword'),
('al', 'stopword'),
-- Pronombres
('he', 'stopword'),
('she', 'stopword'),
('it', 'stopword'),
('they', 'stopword'),
('we', 'stopword'),
('i', 'stopword'),
('you', 'stopword'),
('him', 'stopword'),
('her', 'stopword'),
('them', 'stopword'),
('me', 'stopword'),
('us', 'stopword')
ON CONFLICT (term) DO NOTHING;
```

**Step 3: Crear schema 009_fantasy_terms.sql**

```sql
-- database/schemas/009_fantasy_terms.sql
-- Tabla para términos de fantasía que son palabras comunes pero nombres propios en contexto

CREATE TABLE IF NOT EXISTS fantasy_terms (
    id SERIAL PRIMARY KEY,
    term VARCHAR(200) NOT NULL UNIQUE,
    entity_type VARCHAR(50) NOT NULL,
    do_not_translate BOOLEAN DEFAULT FALSE,
    context_hint VARCHAR(500),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Términos base de fantasía
INSERT INTO fantasy_terms (term, entity_type, do_not_translate, context_hint) VALUES
-- Razas de fantasía
('slime', 'race', TRUE, 'criatura gelatinosa'),
('goblin', 'race', TRUE, 'criatura pequeña maligna'),
('orc', 'race', TRUE, 'criatura humanoide agresiva'),
('elf', 'race', TRUE, 'criatura mágica longeva'),
('dwarf', 'race', TRUE, 'criatura pequeña forjadora'),
('dragon', 'race', FALSE, 'bestia alada colosal'),
('demon', 'race', FALSE, 'criatura infernal'),
('undead', 'race', TRUE, 'criatura no-muerta'),
('vampire', 'race', TRUE, 'no-muerto sangriento'),
('werewolf', 'race', TRUE, 'hombre lobo'),
-- Organizaciones
('guild', 'organization', FALSE, 'asociación de aventureros'),
('sect', 'organization', FALSE, 'escuela de artes marciales'),
-- Lugares
('dungeon', 'place', FALSE, 'laberinto con monstruos'),
('labyrinth', 'place', FALSE, 'laberinto subterráneo'),
-- Habilidades/Conceptos
('mana', 'skill', FALSE, 'energía mágica'),
('spell', 'spell', FALSE, 'magia activa'),
('qi', 'skill', TRUE, 'energía vital china'),
('cultivation', 'skill', FALSE, 'práctica espiritual'),
-- Títulos
('adventurer', 'title', FALSE, 'profesión de explorador'),
('hero', 'title', FALSE, 'protagonista elegido'),
('sage', 'title', FALSE, 'mago anciano')
ON CONFLICT (term) DO NOTHING;
```

**Step 4: Extender models.py con nuevos dataclasses**

Añadir al final de `database/models.py`:

```python
@dataclass
class EntityBlacklist:
    id: Optional[int]
    term: str
    reason: Optional[str] = None


@dataclass
class FantasyTerm:
    id: Optional[int]
    term: str
    entity_type: str
    do_not_translate: bool = False
    context_hint: Optional[str] = None


@dataclass
class EntityCandidate:
    text: str
    entity_type: str
    frequency: int = 1
    contexts: List[str] = field(default_factory=list)
    confidence: float = 0.0
    source_language: str = "en"

    def add_context(self, context: str):
        if context not in self.contexts:
            self.contexts.append(context[:300])

    def best_context(self) -> str:
        return self.contexts[0] if self.contexts else ""

    def to_embed_text(self) -> str:
        return f"{self.text} {self.entity_type} {self.best_context()}"


@dataclass
class BuildResult:
    extracted: int
    new: int
    skipped: int
    entities_by_type: Dict[str, int] = field(default_factory=dict)
```

**Step 5: Extender GlossaryEntry con nuevos campos**

Modificar el dataclass `GlossaryEntry` en `database/models.py`:

```python
@dataclass
class GlossaryEntry:
    id: Optional[int]
    work_id: int
    term: str
    translation: Optional[str]
    is_proper_noun: bool = False
    notes: Optional[str] = None
    contexts: List[TermContext] = field(default_factory=list)
    embedding: Optional[np.ndarray] = None
    # NUEVOS CAMPOS
    entity_type: str = "other"
    do_not_translate: bool = False
    is_verified: bool = False
    confidence: float = 0.0
    source_language: str = "en"
    target_language: str = "es"
```

**Step 6: Commit**

```bash
git add database/schemas/007_glossary_extensions.sql \
        database/schemas/008_entity_blacklist.sql \
        database/schemas/009_fantasy_terms.sql \
        database/models.py
git commit -m "feat: add entity_blacklist, fantasy_terms tables and extend GlossaryEntry model"
```

---

## Task 2: Crear EntityBlacklistRepository

**Files:**
- Create: `database/repositories/entity_blacklist_repository.py`
- Modify: `database/repositories/__init__.py`

**Step 1: Crear EntityBlacklistRepository**

```python
# database/repositories/entity_blacklist_repository.py
from typing import Optional, Set

from database.connection import DatabasePool
from database.repositories.base import BaseRepository
from database.models import EntityBlacklist


class EntityBlacklistRepository(BaseRepository[EntityBlacklist]):
    def __init__(self, pool: Optional[DatabasePool] = None):
        self._pool = pool or DatabasePool.get_instance()

    def _row_to_entity_blacklist(self, row: tuple) -> EntityBlacklist:
        return EntityBlacklist(
            id=row[0],
            term=row[1],
            reason=row[2] if len(row) > 2 else None,
        )

    def get_by_id(self, id: int) -> Optional[EntityBlacklist]:
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, term, reason FROM entity_blacklist WHERE id = %s",
                    (id,),
                )
                row = cur.fetchone()
                return self._row_to_entity_blacklist(row) if row else None

    def get_all(self) -> list[EntityBlacklist]:
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id, term, reason FROM entity_blacklist ORDER BY term")
                rows = cur.fetchall()
                return [self._row_to_entity_blacklist(row) for row in rows]

    def get_all_terms(self) -> Set[str]:
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT term FROM entity_blacklist")
                return {row[0].lower() for row in cur.fetchall()}

    def create(self, entity: EntityBlacklist) -> EntityBlacklist:
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO entity_blacklist (term, reason)
                    VALUES (%s, %s)
                    RETURNING id, term, reason
                    """,
                    (entity.term.lower(), entity.reason),
                )
                row = cur.fetchone()
                return self._row_to_entity_blacklist(row)

    def add(self, term: str, reason: Optional[str] = None) -> EntityBlacklist:
        return self.create(EntityBlacklist(id=None, term=term, reason=reason))

    def delete(self, id: int) -> bool:
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM entity_blacklist WHERE id = %s", (id,))
                return cur.rowcount > 0

    def remove(self, term: str) -> bool:
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM entity_blacklist WHERE LOWER(term) = LOWER(%s)", (term,))
                return cur.rowcount > 0

    def exists(self, term: str) -> bool:
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT 1 FROM entity_blacklist WHERE LOWER(term) = LOWER(%s)",
                    (term,),
                )
                return cur.fetchone() is not None
```

**Step 2: Actualizar __init__.py**

Añadir a `database/repositories/__init__.py`:

```python
from database.repositories.entity_blacklist_repository import EntityBlacklistRepository

__all__ = [
    # ... existentes
    "EntityBlacklistRepository",
]
```

**Step 3: Commit**

```bash
git add database/repositories/entity_blacklist_repository.py \
        database/repositories/__init__.py
git commit -m "feat: add EntityBlacklistRepository"
```

---

## Task 3: Crear FantasyTermRepository

**Files:**
- Create: `database/repositories/fantasy_term_repository.py`
- Modify: `database/repositories/__init__.py`

**Step 1: Crear FantasyTermRepository**

```python
# database/repositories/fantasy_term_repository.py
from typing import Optional, Dict

from database.connection import DatabasePool
from database.repositories.base import BaseRepository
from database.models import FantasyTerm


class FantasyTermRepository(BaseRepository[FantasyTerm]):
    def __init__(self, pool: Optional[DatabasePool] = None):
        self._pool = pool or DatabasePool.get_instance()

    def _row_to_fantasy_term(self, row: tuple) -> FantasyTerm:
        return FantasyTerm(
            id=row[0],
            term=row[1],
            entity_type=row[2],
            do_not_translate=row[3],
            context_hint=row[4] if len(row) > 4 else None,
        )

    def get_by_id(self, id: int) -> Optional[FantasyTerm]:
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, term, entity_type, do_not_translate, context_hint FROM fantasy_terms WHERE id = %s",
                    (id,),
                )
                row = cur.fetchone()
                return self._row_to_fantasy_term(row) if row else None

    def get_all(self) -> list[FantasyTerm]:
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, term, entity_type, do_not_translate, context_hint FROM fantasy_terms ORDER BY term"
                )
                rows = cur.fetchall()
                return [self._row_to_fantasy_term(row) for row in rows]

    def get_all_terms(self) -> Dict[str, FantasyTerm]:
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, term, entity_type, do_not_translate, context_hint FROM fantasy_terms"
                )
                rows = cur.fetchall()
                return {row[1].lower(): self._row_to_fantasy_term(row) for row in rows}

    def get_by_term(self, term: str) -> Optional[FantasyTerm]:
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, term, entity_type, do_not_translate, context_hint
                    FROM fantasy_terms
                    WHERE LOWER(term) = LOWER(%s)
                    """,
                    (term,),
                )
                row = cur.fetchone()
                return self._row_to_fantasy_term(row) if row else None

    def create(self, entity: FantasyTerm) -> FantasyTerm:
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO fantasy_terms (term, entity_type, do_not_translate, context_hint)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id, term, entity_type, do_not_translate, context_hint
                    """,
                    (entity.term.lower(), entity.entity_type, entity.do_not_translate, entity.context_hint),
                )
                row = cur.fetchone()
                return self._row_to_fantasy_term(row)

    def update(self, entity: FantasyTerm) -> FantasyTerm:
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE fantasy_terms
                    SET entity_type = %s, do_not_translate = %s, context_hint = %s
                    WHERE id = %s
                    RETURNING id, term, entity_type, do_not_translate, context_hint
                    """,
                    (entity.entity_type, entity.do_not_translate, entity.context_hint, entity.id),
                )
                row = cur.fetchone()
                return self._row_to_fantasy_term(row) if row else None

    def delete(self, id: int) -> bool:
        pool = self._pool.get_sync_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM fantasy_terms WHERE id = %s", (id,))
                return cur.rowcount > 0
```

**Step 2: Actualizar __init__.py**

Añadir a `database/repositories/__init__.py`:

```python
from database.repositories.fantasy_term_repository import FantasyTermRepository

__all__ = [
    # ... existentes
    "FantasyTermRepository",
]
```

**Step 3: Commit**

```bash
git add database/repositories/fantasy_term_repository.py \
        database/repositories/__init__.py
git commit -m "feat: add FantasyTermRepository"
```

---

## Task 4: Extender GlossaryRepository

**Files:**
- Modify: `database/repositories/glossary_repository.py`

**Step 1: Actualizar _row_to_glossary_entry**

Modificar el método para incluir nuevos campos:

```python
def _row_to_glossary_entry(self, row: tuple) -> GlossaryEntry:
    return GlossaryEntry(
        id=row[0],
        work_id=row[1],
        term=row[2],
        translation=row[3],
        notes=row[4],
        is_proper_noun=row[5],
        embedding=row[6] if len(row) > 6 and row[6] is not None else None,
        entity_type=row[7] if len(row) > 7 else "other",
        do_not_translate=row[8] if len(row) > 8 else False,
        is_verified=row[9] if len(row) > 9 else False,
        confidence=row[10] if len(row) > 10 else 0.0,
        source_language=row[11] if len(row) > 11 else "en",
        target_language=row[12] if len(row) > 12 else "es",
        contexts=[],
    )
```

**Step 2: Actualizar queries existentes**

Modificar `get_by_id`, `get_all`, `get_by_work`, `find_by_term`, `find_similar_terms` para incluir nuevos campos:

```python
def get_by_id(self, id: int) -> Optional[GlossaryEntry]:
    pool = self._pool.get_sync_pool()
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, work_id, term, translation, notes, is_proper_noun, embedding,
                       entity_type, do_not_translate, is_verified, confidence, source_language, target_language
                FROM glossary_terms
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
```

**Step 3: Añadir método filter_new_entities**

```python
def filter_new_entities(
    self, candidates: list, work_id: int
) -> list:
    """Filtra candidatos que ya existen en el glosario."""
    existing_terms = self._get_existing_terms(work_id)
    return [c for c in candidates if c.text.lower() not in existing_terms]

def _get_existing_terms(self, work_id: int) -> set:
    """Obtiene todos los términos existentes para una obra."""
    pool = self._pool.get_sync_pool()
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT LOWER(term) FROM glossary_terms WHERE work_id = %s",
                (work_id,),
            )
            return {row[0] for row in cur.fetchall()}
```

**Step 4: Añadir método batch_create_with_embeddings**

```python
def batch_create_with_embeddings(
    self,
    entries: list,
    work_id: int,
    source_language: str,
    target_language: str,
) -> list[GlossaryEntry]:
    """Crea múltiples entradas con embeddings en batch."""
    pool = self._pool.get_sync_pool()
    results = []
    with pool.connection() as conn:
        with conn.cursor() as cur:
            for entry, embedding in entries:
                cur.execute(
                    """
                    INSERT INTO glossary_terms (
                        work_id, term, translation, notes, is_proper_noun,
                        entity_type, do_not_translate, is_verified, confidence,
                        source_language, target_language, embedding
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id, work_id, term, translation, notes, is_proper_noun, embedding,
                              entity_type, do_not_translate, is_verified, confidence, source_language, target_language
                    """,
                    (
                        work_id,
                        entry.text,
                        entry.translation if hasattr(entry, 'translation') else None,
                        None,
                        False,
                        entry.entity_type,
                        entry.do_not_translate if hasattr(entry, 'do_not_translate') else False,
                        False,
                        entry.confidence,
                        source_language,
                        target_language,
                        embedding.tolist() if hasattr(embedding, 'tolist') else embedding,
                    ),
                )
                row = cur.fetchone()
                results.append(self._row_to_glossary_entry(row))
        conn.commit()
    return results
```

**Step 5: Commit**

```bash
git add database/repositories/glossary_repository.py
git commit -m "feat: extend GlossaryRepository with filter_new_entities and batch_create"
```

---

## Task 5: Crear EntityExtractor Service

**Files:**
- Create: `database/services/entity_extractor.py`
- Modify: `database/services/__init__.py`

**Step 1: Crear EntityExtractor**

```python
# database/services/entity_extractor.py
"""
Entity extraction service using NLTK NER + regex patterns.

Detects entities that need special treatment in translation:
- Characters (PERSON)
- Places (LOCATION, GPE)
- Organizations (ORGANIZATION)
- Skills/Powers (SKILL) - fantasy specific
- Items/Artifacts (ITEM)
- Titles/Ranks (TITLE/RANK)
"""
from __future__ import annotations

import re
import logging
from collections import Counter
from typing import Dict, List, Optional, Set

import nltk
from nltk import word_tokenize, pos_tag, ne_chunk, sent_tokenize
from nltk.tree import Tree

from database.models import EntityCandidate
from database.repositories.entity_blacklist_repository import EntityBlacklistRepository
from database.repositories.fantasy_term_repository import FantasyTermRepository
from database.connection import DatabasePool

logger = logging.getLogger(__name__)

NLTK_PACKAGES = [
    "punkt",
    "punkt_tab",
    "averaged_perceptron_tagger",
    "maxent_ne_chunker",
    "words",
    "maxent_ne_chunker_tab",
]

for pkg in NLTK_PACKAGES:
    try:
        nltk.download(pkg, quiet=True)
    except Exception:
        pass

ENTITY_TYPES = {
    "PERSON": "character",
    "GPE": "place",
    "LOCATION": "place",
    "ORGANIZATION": "faction",
    "FACILITY": "place",
}

SKILL_PATTERN = re.compile(
    r'(?:'
    r'【([^】]{2,60})】'
    r'|《([^》]{2,60})》'
    r'|\[([^\]]{2,60})\]'
    r'|<([^>]{2,60})>'
    r'|"([A-Z][A-Za-z\s\'-]{2,50})"'
    r'|\'([A-Z][A-Za-z\s\'-]{2,50})\''
    r')'
)

TITLE_PATTERN = re.compile(
    r'(?:'
    r'Lord|Lady|Sir|Duke|Duchess|Baron|Count|Countess|'
    r'Prince|Princess|King|Queen|Emperor|Empress|'
    r'Elder|Sect\s*Master|Grand\s*Master|Overlord|'
    r'Demon\s*King|Hero|Sage|Archmage'
    r')\s+([A-Z][A-Za-z\s\'-]{1,50})',
    re.IGNORECASE
)


class EntityExtractor:
    def __init__(
        self,
        pool: Optional[DatabasePool] = None,
        min_frequency: int = 2,
    ):
        self._pool = pool or DatabasePool.get_instance()
        self._blacklist_repo = EntityBlacklistRepository(pool)
        self._fantasy_repo = FantasyTermRepository(pool)
        self.min_frequency = min_frequency
        self._blacklist: Optional[Set[str]] = None
        self._fantasy_terms: Optional[Dict[str, any]] = None

    def _ensure_loaded(self):
        if self._blacklist is None:
            self._blacklist = self._blacklist_repo.get_all_terms()
        if self._fantasy_terms is None:
            self._fantasy_terms = self._fantasy_repo.get_all_terms()

    def extract(self, text: str, source_language: str = "en") -> List[EntityCandidate]:
        self._ensure_loaded()
        entity_counts: Dict[str, EntityCandidate] = {}

        if source_language in ("en", "en-US", "en-GB"):
            nltk_entities = self._extract_nltk(text)
            for ent in nltk_entities:
                key = ent.text.lower()
                if key in entity_counts:
                    entity_counts[key].frequency += ent.frequency
                    for ctx in ent.contexts:
                        entity_counts[key].add_context(ctx)
                else:
                    entity_counts[key] = ent

        pattern_entities = self._extract_patterns(text)
        for ent in pattern_entities:
            key = ent.text.lower()
            if key in entity_counts:
                entity_counts[key].frequency += ent.frequency
            else:
                entity_counts[key] = ent

        if source_language in ("en", "en-US", "en-GB"):
            pos_entities = self._extract_by_pos_frequency(text)
            for ent in pos_entities:
                key = ent.text.lower()
                if key not in entity_counts:
                    entity_counts[key] = ent

        filtered = [
            ent for ent in entity_counts.values()
            if (
                ent.frequency >= self.min_frequency
                and ent.text.lower() not in self._blacklist
                and len(ent.text) >= 2
            )
        ]

        for ent in filtered:
            if ent.text.lower() in self._fantasy_terms:
                ft = self._fantasy_terms[ent.text.lower()]
                ent.entity_type = ft.entity_type
                if ft.do_not_translate and not ent.contexts:
                    ent.add_context(ft.context_hint or "")
            ent.confidence = self._calculate_confidence(ent)

        priority_order = {
            "character": 0, "place": 1, "skill": 2,
            "item": 3, "faction": 4, "title": 5, "race": 6, "other": 9
        }
        filtered.sort(
            key=lambda e: (priority_order.get(e.entity_type, 9), -e.frequency)
        )

        logger.info(f"Extraídas {len(filtered)} entidades del texto ({len(text)} chars)")
        return filtered

    def _extract_nltk(self, text: str) -> List[EntityCandidate]:
        candidates: Dict[str, EntityCandidate] = {}
        sentences = sent_tokenize(text)

        for sent in sentences:
            try:
                tokens = word_tokenize(sent)
                tagged = pos_tag(tokens)
                tree = ne_chunk(tagged, binary=False)

                for subtree in tree:
                    if isinstance(subtree, Tree):
                        label = subtree.label()
                        name = " ".join(w for w, t in subtree.leaves())

                        if len(name) < 2 or name.lower() in self._blacklist:
                            continue

                        etype = ENTITY_TYPES.get(label, "other")
                        key = name.lower()

                        idx = sent.find(name)
                        ctx = sent[max(0, idx - 50):idx + len(name) + 50]

                        if key in candidates:
                            candidates[key].frequency += 1
                            candidates[key].add_context(ctx)
                        else:
                            candidates[key] = EntityCandidate(
                                text=name,
                                entity_type=etype,
                                frequency=1,
                                contexts=[ctx],
                                source_language="en",
                            )
            except Exception as e:
                logger.debug(f"Error NLTK NER en oración: {e}")
                continue

        return list(candidates.values())

    def _extract_patterns(self, text: str) -> List[EntityCandidate]:
        candidates: Dict[str, EntityCandidate] = {}

        for m in SKILL_PATTERN.finditer(text):
            name = next((g for g in m.groups() if g), None)
            if name and len(name) >= 2:
                key = name.lower()
                ctx = text[max(0, m.start() - 40):m.end() + 40]
                if key in candidates:
                    candidates[key].frequency += 1
                else:
                    candidates[key] = EntityCandidate(
                        text=name.strip(),
                        entity_type="skill",
                        frequency=1,
                        contexts=[ctx],
                        confidence=0.85,
                        source_language="en",
                    )

        for m in TITLE_PATTERN.finditer(text):
            full = m.group(0).strip()
            name = m.group(1).strip()
            key = full.lower()
            if key not in candidates and len(name) >= 2:
                ctx = text[max(0, m.start() - 30):m.end() + 30]
                candidates[key] = EntityCandidate(
                    text=full,
                    entity_type="title",
                    frequency=1,
                    contexts=[ctx],
                    confidence=0.75,
                    source_language="en",
                )

        return list(candidates.values())

    def _extract_by_pos_frequency(self, text: str) -> List[EntityCandidate]:
        candidates: Dict[str, EntityCandidate] = {}
        word_pos_counts: Counter = Counter()

        sentences = sent_tokenize(text)
        for sent in sentences:
            try:
                tokens = word_tokenize(sent)
                tagged = pos_tag(tokens)
                for word, pos in tagged:
                    if pos in ("NNP", "NNPS") and len(word) >= 2:
                        word_pos_counts[word] += 1
            except Exception:
                continue

        for word, count in word_pos_counts.items():
            if (
                count >= self.min_frequency
                and word.lower() not in self._blacklist
                and not word.isnumeric()
                and len(word) >= 2
            ):
                key = word.lower()
                if key not in candidates:
                    candidates[key] = EntityCandidate(
                        text=word,
                        entity_type="character",
                        frequency=count,
                        confidence=0.5,
                        source_language="en",
                    )

        return list(candidates.values())

    def _calculate_confidence(self, ent: EntityCandidate) -> float:
        score = 0.5

        if ent.frequency >= 10:
            score += 0.3
        elif ent.frequency >= 5:
            score += 0.2
        elif ent.frequency >= 3:
            score += 0.1

        if ent.entity_type in ("skill", "item"):
            score += 0.2

        if ent.contexts:
            score += 0.1

        if len(ent.text) <= 2:
            score -= 0.2

        return min(1.0, max(0.0, score))
```

**Step 2: Actualizar __init__.py**

Añadir a `database/services/__init__.py`:

```python
from database.services.entity_extractor import EntityExtractor

__all__ = [
    "VectorStoreService",
    "EntityExtractor",
]
```

**Step 3: Commit**

```bash
git add database/services/entity_extractor.py \
        database/services/__init__.py
git commit -m "feat: add EntityExtractor service with NLTK NER and regex patterns"
```

---

## Task 6: Extender VectorStoreService

**Files:**
- Modify: `database/services/vector_store.py`

**Step 1: Añadir método embed_entities_for_glossary**

```python
def embed_entities_for_glossary(
    self,
    entities: List,
) -> List[tuple]:
    """
    Genera embeddings para entidades candidatas.

    El texto a embeddear combina: término + tipo + contexto

    Args:
        entities: Lista de EntityCandidate

    Returns:
        Lista de tuplas (EntityCandidate, embedding)
    """
    if not entities:
        return []

    texts = [
        f"{e.text} {e.entity_type} {e.best_context()}"
        for e in entities
    ]

    embeddings = self.embedder.embed_documents(texts)
    return list(zip(entities, embeddings))
```

**Step 2: Commit**

```bash
git add database/services/vector_store.py
git commit -m "feat: add embed_entities_for_glossary method to VectorStoreService"
```

---

## Task 7: Crear GlossaryManager Service

**Files:**
- Create: `database/services/glossary_manager.py`
- Modify: `database/services/__init__.py`

**Step 1: Crear GlossaryManager**

```python
# database/services/glossary_manager.py
"""
Glossary management service with RAG capabilities.

Main pipeline:
1. Extract entities from text (EntityExtractor)
2. Filter duplicates against existing glossary
3. Generate embeddings (VectorStoreService)
4. Suggest translations with LLM
5. Store in database
"""
from __future__ import annotations

import json
import logging
from typing import Dict, List, Optional

from database.connection import DatabasePool
from database.models import EntityCandidate, BuildResult, GlossaryEntry
from database.repositories.glossary_repository import GlossaryRepository
from database.services.entity_extractor import EntityExtractor
from database.services.vector_store import VectorStoreService
from llm.nvidia_llm import NvidiaLLM

logger = logging.getLogger(__name__)


class GlossaryManager:
    def __init__(self, pool: Optional[DatabasePool] = None):
        self._pool = pool or DatabasePool.get_instance()
        self._extractor = EntityExtractor(pool)
        self._glossary_repo = GlossaryRepository(pool)
        self._vector_service = VectorStoreService()
        self._llm_client: Optional[NvidiaLLM] = None

    def _ensure_llm(self):
        if self._llm_client is None:
            self._llm_client = NvidiaLLM()

    def build_from_text(
        self,
        text: str,
        work_id: int,
        source_lang: str = "en",
        target_lang: str = "es",
        suggest_translations: bool = True,
    ) -> BuildResult:
        """
        Build glossary from text with full pipeline.

        Args:
            text: Source text to analyze
            work_id: Work ID for glossary association
            source_lang: Source language code
            target_lang: Target language code
            suggest_translations: Whether to suggest translations with LLM

        Returns:
            BuildResult with extraction statistics
        """
        candidates = self._extractor.extract(text, source_lang)

        entities_by_type: Dict[str, int] = {}
        for c in candidates:
            entities_by_type[c.entity_type] = entities_by_type.get(c.entity_type, 0) + 1

        new_entities = self._glossary_repo.filter_new_entities(candidates, work_id)

        if not new_entities:
            return BuildResult(
                extracted=len(candidates),
                new=0,
                skipped=len(candidates),
                entities_by_type=entities_by_type,
            )

        entity_embeddings = self._vector_service.embed_entities_for_glossary(new_entities)

        translations: Dict[str, str] = {}
        if suggest_translations and entity_embeddings:
            translations = self._suggest_translations(new_entities, source_lang, target_lang)

        saved = self._save_entities(
            entity_embeddings,
            translations,
            work_id,
            source_lang,
            target_lang,
        )

        return BuildResult(
            extracted=len(candidates),
            new=len(saved),
            skipped=len(candidates) - len(new_entities),
            entities_by_type=entities_by_type,
        )

    def _suggest_translations(
        self,
        entities: List[EntityCandidate],
        source_lang: str,
        target_lang: str,
    ) -> Dict[str, str]:
        """
        Suggest translations using LLM.

        Args:
            entities: List of entities to translate
            source_lang: Source language
            target_lang: Target language

        Returns:
            Dict mapping entity text to suggested translation
        """
        self._ensure_llm()

        terms = [e.text for e in entities]

        prompt = f"""You are a translation assistant for fantasy literature.
Translate the following terms from {source_lang} to {target_lang}.

Rules:
- For proper names of characters and places: keep original OR adapt phonetically if appropriate
- For skills, items, titles: translate meaningfully
- For races/species that are proper nouns in this context: keep original
- Respond ONLY with a JSON object, no explanation

Terms: {json.dumps(terms)}

Response format: {{"original_term": "translation"}}"""

        try:
            response = self._llm_client.call_model(prompt)
            if response:
                return json.loads(response)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse LLM translation response: {e}")
        except Exception as e:
            logger.error(f"Error getting translations from LLM: {e}")

        return {}

    def _save_entities(
        self,
        entity_embeddings: List[tuple],
        translations: Dict[str, str],
        work_id: int,
        source_lang: str,
        target_lang: str,
    ) -> List[GlossaryEntry]:
        """
        Save entities to database.

        Args:
            entity_embeddings: List of (EntityCandidate, embedding) tuples
            translations: Dict of suggested translations
            work_id: Work ID
            source_lang: Source language
            target_lang: Target language

        Returns:
            List of saved GlossaryEntry objects
        """
        entries_to_save = []
        for entity, embedding in entity_embeddings:
            translation = translations.get(entity.text)
            setattr(entity, 'translation', translation)
            entries_to_save.append((entity, embedding))

        return self._glossary_repo.batch_create_with_embeddings(
            entries_to_save,
            work_id,
            source_lang,
            target_lang,
        )

    def get_glossary_for_work(self, work_id: int) -> List[GlossaryEntry]:
        """Get all glossary entries for a work."""
        return self._glossary_repo.get_by_work(work_id)
```

**Step 2: Actualizar __init__.py**

Añadir a `database/services/__init__.py`:

```python
from database.services.glossary_manager import GlossaryManager

__all__ = [
    "VectorStoreService",
    "EntityExtractor",
    "GlossaryManager",
]
```

**Step 3: Commit**

```bash
git add database/services/glossary_manager.py \
        database/services/__init__.py
git commit -m "feat: add GlossaryManager service with full extraction pipeline"
```

---

## Task 8: Crear Comando CLI build_glossary

**Files:**
- Create: `cli/commands/build_glossary.py`
- Modify: `cli/app.py`

**Step 1: Crear build_glossary.py**

```python
# cli/commands/build_glossary.py
import logging
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
)
from rich.table import Table

from cli.app import app, console, setup_logging
from database.connection import DatabasePool
from database.repositories.book_repository import BookRepository, WorkRepository
from database.repositories.chapter_repository import ChapterRepository
from database.repositories.volume_repository import VolumeRepository
from database.services.glossary_manager import GlossaryManager

logger = logging.getLogger(__name__)


def _get_work_info(work_id: int) -> Optional[dict]:
    """Get work information from database."""
    work_repo = WorkRepository()
    work = work_repo.get_by_id(work_id)
    if not work:
        return None
    return {
        "id": work.id,
        "title": work.title,
        "title_translated": work.title_translated,
    }


def _get_volumes_to_process(work_id: int, volume_number: Optional[int]) -> list:
    """Get volumes to process based on filters."""
    volume_repo = VolumeRepository()
    if volume_number:
        volume = volume_repo.get_by_work_and_number(work_id, volume_number)
        return [volume] if volume else []
    return volume_repo.get_by_work(work_id)


def _print_summary_table(extracted: int, new: int, skipped: int, dry_run: bool):
    """Print summary table with extraction results."""
    table = Table(title="Resumen de Extracción", show_header=True, header_style="bold magenta")
    table.add_column("Métrica", style="cyan")
    table.add_column("Cantidad", justify="right", style="green")

    table.add_row("Entidades detectadas", str(extracted))
    table.add_row("Entidades nuevas", str(new))
    table.add_row("Duplicados (ignorados)", str(skipped))

    if dry_run:
        table.add_row("Modo", "[yellow]DRY-RUN (no guardado)[/yellow]")

    console.print()
    console.print(table)


def _print_entity_distribution_chart(entities_by_type: dict):
    """Print bar chart with entity distribution by type."""
    if not entities_by_type:
        return

    console.print("\n[bold]Distribución por tipo de entidad:[/bold]\n")

    max_count = max(entities_by_type.values()) if entities_by_type else 1

    type_labels = {
        "character": "Personajes",
        "place": "Lugares",
        "skill": "Habilidades",
        "item": "Objetos",
        "spell": "Hechizos",
        "faction": "Organizaciones",
        "title": "Títulos",
        "race": "Razas",
        "other": "Otros",
    }

    for etype, count in sorted(entities_by_type.items(), key=lambda x: -x[1]):
        label = type_labels.get(etype, etype)
        bar_width = int((count / max_count) * 30) if max_count > 0 else 0
        bar = "█" * bar_width
        console.print(f"  {label:<15} {bar} {count}")


@app.command("build-glossary")
def build_glossary(
    work_id: int = typer.Option(..., "--work-id", "-w", help="ID de la obra"),
    volume_number: Optional[int] = typer.Option(
        None, "--volume-number", "-v", help="Número de volumen a procesar"
    ),
    chapter_number: Optional[int] = typer.Option(
        None, "--chapter-number", "-c", help="Número de capítulo (requiere --volume-number)"
    ),
    all_volumes: bool = typer.Option(
        False, "--all", "-a", help="Procesar toda la obra"
    ),
    min_frequency: int = typer.Option(
        2, "--min-frequency", "-m", help="Frecuencia mínima de entidades"
    ),
    source_lang: str = typer.Option("en", "--source-lang", "-s", help="Idioma origen"),
    target_lang: str = typer.Option("es", "--target-lang", "-t", help="Idioma destino"),
    dry_run: bool = typer.Option(
        False, "--dry-run", "-d", help="Solo mostrar entidades sin guardar"
    ),
):
    """
    Construye el glosario de traducción extrayendo entidades con NER + RAG.

    Ejemplos:
        pdftranslator build-glossary -w 1
        pdftranslator build-glossary -w 1 -v 1
        pdftranslator build-glossary -w 1 -v 1 -c 5
        pdftranslator build-glossary -w 1 --all
    """
    setup_logging()

    if chapter_number and not volume_number:
        console.print("[red]Error: --chapter-number requiere --volume-number[/red]")
        raise typer.Exit(1)

    work_info = _get_work_info(work_id)
    if not work_info:
        console.print(f"[red]Obra no encontrada: {work_id}[/red]")
        raise typer.Exit(1)

    title_display = work_info["title"]
    if work_info["title_translated"]:
        title_display += f"\n[dim]({work_info['title_translated']})[/dim]"

    console.print(Panel.fit(f"[bold blue]{title_display}[/bold blue]"))

    pool = DatabasePool.get_instance()
    manager = GlossaryManager(pool)

    volumes = _get_volumes_to_process(work_id, volume_number)

    if not volumes:
        console.print("[yellow]No se encontraron volúmenes para procesar[/yellow]")
        raise typer.Exit(0)

    total_extracted = 0
    total_new = 0
    total_skipped = 0
    all_entities_by_type = {}

    chapter_repo = ChapterRepository()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        for vol in volumes:
            vol_task = progress.add_task(
                f"[cyan]Volumen {vol.volume_number}", total=None
            )

            chapters = chapter_repo.get_by_volume(vol.id)

            if chapter_number:
                chapters = [ch for ch in chapters if ch.chapter_number == chapter_number]

            for ch in chapters:
                ch_label = ch.chapter_number if ch.chapter_number else "Especial"
                progress.update(vol_task, description=f"[cyan]Capítulo {ch_label}")

                if not ch.original_text:
                    continue

                result = manager.build_from_text(
                    text=ch.original_text,
                    work_id=work_id,
                    source_lang=source_lang,
                    target_lang=target_lang,
                    suggest_translations=not dry_run,
                )

                total_extracted += result.extracted
                total_new += result.new
                total_skipped += result.skipped

                for etype, count in result.entities_by_type.items():
                    all_entities_by_type[etype] = all_entities_by_type.get(etype, 0) + count

                progress.advance(vol_task)

    _print_summary_table(total_extracted, total_new, total_skipped, dry_run)
    _print_entity_distribution_chart(all_entities_by_type)

    if dry_run:
        console.print("\n[yellow]Modo dry-run: Los cambios no fueron guardados[/yellow]")
    else:
        console.print(f"\n[green]Glosario actualizado: {total_new} nuevas entidades[/green]")
```

**Step 2: Registrar comando en app.py**

Añadir al final de `cli/app.py`:

```python
from cli.commands import process, add_to_database, split_text, reset_database, build_glossary
```

**Step 3: Commit**

```bash
git add cli/commands/build_glossary.py \
        cli/app.py
git commit -m "feat: add build-glossary CLI command with Rich visualization"
```

---

## Task 9: Actualizar GlobalConfig

**Files:**
- Modify: `GlobalConfig.py`

**Step 1: Añadir configuración de NER**

Añadir al `__init__` de GlobalConfig:

```python
# NER / Entity extraction settings
self.ner_min_frequency: int = 2
self.ner_confidence_threshold: float = 0.5
```

Añadir a `_get_expected_types`:

```python
"ner_min_frequency": int,
"ner_confidence_threshold": float,
```

**Step 2: Commit**

```bash
git add GlobalConfig.py
git commit -m "feat: add NER configuration to GlobalConfig"
```

---

## Task 10: Tests

**Files:**
- Create: `tests/database/test_entity_blacklist_repository.py`
- Create: `tests/database/test_fantasy_term_repository.py`
- Create: `tests/database/test_entity_extractor.py`
- Create: `tests/database/test_glossary_manager.py`

**Step 1: Crear test para EntityBlacklistRepository**

```python
# tests/database/test_entity_blacklist_repository.py
import pytest
from database.repositories.entity_blacklist_repository import EntityBlacklistRepository
from database.models import EntityBlacklist


class TestEntityBlacklistRepository:
    def test_get_all_terms_returns_set(self, test_pool):
        repo = EntityBlacklistRepository(test_pool)
        terms = repo.get_all_terms()

        assert isinstance(terms, set)
        assert "the" in terms
        assert "chapter" in terms

    def test_add_and_remove(self, test_pool):
        repo = EntityBlacklistRepository(test_pool)

        added = repo.add("test_term_123", "test reason")
        assert added.term == "test_term_123"

        assert repo.exists("test_term_123")

        removed = repo.remove("test_term_123")
        assert removed is True

        assert not repo.exists("test_term_123")
```

**Step 2: Crear test para FantasyTermRepository**

```python
# tests/database/test_fantasy_term_repository.py
import pytest
from database.repositories.fantasy_term_repository import FantasyTermRepository
from database.models import FantasyTerm


class TestFantasyTermRepository:
    def test_get_all_terms_returns_dict(self, test_pool):
        repo = FantasyTermRepository(test_pool)
        terms = repo.get_all_terms()

        assert isinstance(terms, dict)
        assert "slime" in terms
        assert terms["slime"].entity_type == "race"

    def test_get_by_term(self, test_pool):
        repo = FantasyTermRepository(test_pool)

        term = repo.get_by_term("dragon")
        assert term is not None
        assert term.entity_type == "race"

    def test_get_by_term_case_insensitive(self, test_pool):
        repo = FantasyTermRepository(test_pool)

        term = repo.get_by_term("DRAGON")
        assert term is not None
```

**Step 3: Crear test para EntityExtractor**

```python
# tests/database/test_entity_extractor.py
import pytest
from database.services.entity_extractor import EntityExtractor, SKILL_PATTERN, TITLE_PATTERN


class TestEntityExtractor:
    def test_skill_pattern_brackets(self):
        text = "He used 【Fireball】 to attack."
        matches = SKILL_PATTERN.findall(text)
        assert len(matches) > 0

    def test_title_pattern(self):
        text = "Lord Arthur entered the room."
        matches = TITLE_PATTERN.findall(text)
        assert len(matches) > 0

    def test_extract_finds_person(self, test_pool):
        extractor = EntityExtractor(test_pool, min_frequency=1)

        text = "Alice went to the market. Alice bought apples. Alice returned home."
        entities = extractor.extract(text)

        alice_entities = [e for e in entities if e.text.lower() == "alice"]
        assert len(alice_entities) > 0

    def test_extract_filters_blacklist(self, test_pool):
        extractor = EntityExtractor(test_pool, min_frequency=1)

        text = "The chapter was long. The chapter continued."
        entities = extractor.extract(text)

        chapter_entities = [e for e in entities if e.text.lower() == "chapter"]
        assert len(chapter_entities) == 0

    def test_min_frequency_filters_single_occurrence(self, test_pool):
        extractor = EntityExtractor(test_pool, min_frequency=2)

        text = "Xylophone appeared once in this text."
        entities = extractor.extract(text)

        xylophone_entities = [e for e in entities if "xylophone" in e.text.lower()]
        assert len(xylophone_entities) == 0
```

**Step 4: Crear test para GlossaryManager**

```python
# tests/database/test_glossary_manager.py
import pytest
from unittest.mock import Mock, patch
from database.services.glossary_manager import GlossaryManager


class TestGlossaryManager:
    def test_build_from_text_returns_result(self, test_pool):
        manager = GlossaryManager(test_pool)

        text = "Alice went to Wonderland. Alice met the Queen. The Queen was angry."
        result = manager.build_from_text(
            text=text,
            work_id=1,
            source_lang="en",
            target_lang="es",
            suggest_translations=False,
        )

        assert result.extracted > 0
        assert hasattr(result, "new")
        assert hasattr(result, "skipped")
        assert hasattr(result, "entities_by_type")

    @patch("database.services.glossary_manager.NvidiaLLM")
    def test_suggest_translations_returns_dict(self, mock_llm_class, test_pool):
        mock_llm = Mock()
        mock_llm.call_model.return_value = '{"Alice": "Alicia"}'
        mock_llm_class.return_value = mock_llm

        manager = GlossaryManager(test_pool)
        manager._llm_client = mock_llm

        from database.models import EntityCandidate
        entities = [
            EntityCandidate(text="Alice", entity_type="character", frequency=2)
        ]

        translations = manager._suggest_translations(entities, "en", "es")

        assert isinstance(translations, dict)
```

**Step 5: Commit**

```bash
git add tests/database/test_entity_blacklist_repository.py \
        tests/database/test_fantasy_term_repository.py \
        tests/database/test_entity_extractor.py \
        tests/database/test_glossary_manager.py
git commit -m "test: add tests for entity extraction and glossary management"
```

---

## Summary

| Task | Description | Files |
|------|-------------|-------|
| 1 | Extender modelo de datos | schemas + models.py |
| 2 | Crear EntityBlacklistRepository | entity_blacklist_repository.py |
| 3 | Crear FantasyTermRepository | fantasy_term_repository.py |
| 4 | Extender GlossaryRepository | glossary_repository.py |
| 5 | Crear EntityExtractor | entity_extractor.py |
| 6 | Extender VectorStoreService | vector_store.py |
| 7 | Crear GlossaryManager | glossary_manager.py |
| 8 | Crear comando CLI | build_glossary.py + app.py |
| 9 | Actualizar GlobalConfig | GlobalConfig.py |
| 10 | Tests | test_*.py |

Total: 10 tasks, ~17 files created/modified
