# Design: Comando `build-glossary`

## Resumen

Nuevo comando CLI para construir el glosario de traducción usando NER + RAG + Rerank. Extrae entidades de capítulos/volúmenes, genera embeddings, sugiere traducciones con LLM y almacena todo en la base de datos.

## Arquitectura General

```
cli/commands/build_glossary.py          # Comando CLI
database/
├── models.py                           # EXTENDER: GlossaryEntry + EntityBlacklist + FantasyTerm
├── repositories/
│   ├── glossary_repository.py          # EXTENDER: nuevos métodos
│   ├── entity_blacklist_repository.py  # NUEVO
│   └── fantasy_term_repository.py      # NUEVO
├── schemas/
│   ├── 007_glossary_extensions.sql     # NUEVO: ALTER TABLE
│   ├── 008_entity_blacklist.sql        # NUEVO
│   └── 009_fantasy_terms.sql           # NUEVO
└── services/
    ├── entity_extractor.py             # NUEVO: NER + heurísticas
    ├── glossary_manager.py             # NUEVO: pipeline completo
    └── vector_store.py                 # EXTENDER: embed_entities_for_glossary
```

## Flujo de Datos

```
Texto del Capítulo
       │
       ▼
┌─────────────────────┐
│  EntityExtractor    │
│  - NLTK NER         │
│  - Regex patterns   │
│  - POS frequency    │
└─────────────────────┘
       │
       ▼
┌─────────────────────┐
│  Filtrado           │
│  - min_freq >= 2    │
│  - blacklist DB     │
│  - len >= 2         │
└─────────────────────┘
       │
       ▼
┌─────────────────────┐
│  Enriquecimiento    │
│  - fantasy_terms DB │
│  - calcular conf.   │
└─────────────────────┘
       │
       ▼
┌─────────────────────┐
│  Duplicados check   │
│  (glossary_terms)   │
└─────────────────────┘
       │
       ▼
┌─────────────────────┐
│  VectorStoreService │
│  - Embeddings batch │
└─────────────────────┘
       │
       ▼
┌─────────────────────┐
│  LLM Sugerencia     │
│  de traducción      │
└─────────────────────┘
       │
       ▼
┌─────────────────────┐
│  Guardar en DB      │
│  (is_verified=false)│
└─────────────────────┘
```

## Modelo de Datos

### Extensión de `glossary_terms`

```sql
ALTER TABLE glossary_terms
ADD COLUMN IF NOT EXISTS entity_type VARCHAR(50) DEFAULT 'other';
ADD COLUMN IF NOT EXISTS do_not_translate BOOLEAN DEFAULT FALSE;
ADD COLUMN IF NOT EXISTS is_verified BOOLEAN DEFAULT FALSE;
ADD COLUMN IF NOT EXISTS confidence FLOAT DEFAULT 0.0;
ADD COLUMN IF NOT EXISTS source_language VARCHAR(10) DEFAULT 'en';
ADD COLUMN IF NOT EXISTS target_language VARCHAR(10) DEFAULT 'es';
```

### Nueva tabla `entity_blacklist`

Palabras que NUNCA deben tratarse como entidades propias (stopwords, metadatos, etc.).

```sql
CREATE TABLE entity_blacklist (
    id SERIAL PRIMARY KEY,
    term VARCHAR(200) NOT NULL UNIQUE,
    reason VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);
```

Valores iniciales: the, and, or, but, in, on, at, to, for, of, a, an, is, was, chapter, volume, part, book, story, novel, el, la, los, las, un, una, de, del, al.

### Nueva tabla `fantasy_terms`

Términos de fantasía que son palabras comunes pero en contexto son nombres propios.

```sql
CREATE TABLE fantasy_terms (
    id SERIAL PRIMARY KEY,
    term VARCHAR(200) NOT NULL UNIQUE,
    entity_type VARCHAR(50) NOT NULL,
    do_not_translate BOOLEAN DEFAULT FALSE,
    context_hint VARCHAR(500),
    created_at TIMESTAMP DEFAULT NOW()
);
```

Valores iniciales: slime, goblin, orc, elf, dwarf, dragon, demon, undead, vampire, werewolf, guild, adventurer, dungeon, labyrinth, mana, spell, qi, cultivation, sect.

### Modelos Python

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
class GlossaryEntry:
    # Campos existentes
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

@dataclass
class EntityCandidate:
    text: str
    entity_type: str
    frequency: int = 1
    contexts: List[str] = field(default_factory=list)
    confidence: float = 0.0
    source_language: str = "en"
```

## EntityExtractor

### Responsabilidades

1. **NLTK NER**: Extraer PERSON, GPE, ORGANIZATION, LOCATION, FACILITY
2. **Patrones regex**: Skills (【】, 《》, []), Títulos (Lord, Duke, King, etc.)
3. **POS frequency**: Detectar nombres propios por NNP/NNPS frecuentes
4. **Filtrado**: min_frequency=2, blacklist, len>=2

### Patrones Regex

```python
SKILL_PATTERN = re.compile(
    r'(?:'
    r'【([^】]{2,60})】'     # 【Skill Name】
    r'|《([^》]{2,60})》'    # 《Spell Name》
    r'|\[([^\]]{2,60})\]'   # [Skill Name]
    r'|<([^>]{2,60})>'      # <Technique>
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
```

### Cálculo de Confianza

```python
def _calculate_confidence(self, ent: EntityCandidate) -> float:
    score = 0.5
    # Boost por frecuencia
    if ent.frequency >= 10: score += 0.3
    elif ent.frequency >= 5: score += 0.2
    elif ent.frequency >= 3: score += 0.1
    # Boost por tipo específico
    if ent.entity_type in ("skill", "item"): score += 0.2
    # Boost si tiene contexto
    if ent.contexts: score += 0.1
    # Penalización si es muy corto
    if len(ent.text) <= 2: score -= 0.2
    return min(1.0, max(0.0, score))
```

## GlossaryManager

### Pipeline Completo

```python
def build_from_text(
    self,
    text: str,
    work_id: int,
    source_lang: str,
    target_lang: str
) -> BuildResult:
    # 1. Extraer entidades
    candidates = self._extractor.extract(text, source_lang)
    
    # 2. Filtrar duplicados
    new_entities = self._glossary_repo.filter_new_entities(candidates, work_id)
    
    # 3. Generar embeddings
    entity_embeddings = self._vector_service.embed_entities_for_glossary(new_entities)
    
    # 4. Sugerir traducciones con LLM
    translations = self._suggest_translations(new_entities, source_lang, target_lang)
    
    # 5. Guardar en DB
    saved = self._save_entities(entity_embeddings, translations, work_id)
    
    return BuildResult(
        extracted=len(candidates),
        new=len(saved),
        skipped=len(candidates) - len(new_entities),
        entities_by_type=self._count_by_type(candidates)
    )
```

### Sugerencia de Traducción

```python
def _suggest_translations(
    self,
    entities: List[EntityCandidate],
    source_lang: str,
    target_lang: str
) -> Dict[str, str]:
    prompt = f"""
    Traduce los siguientes términos de {source_lang} a {target_lang}.
    
    Para nombres propios de personajes/lugares fantásticos:
    - Mantén el original si es un nombre propio único
    - Adapta fonéticamente si es apropiado
    
    Términos: {json.dumps([e.text for e in entities])}
    
    Responde SOLO con JSON: {{"termino_original": "traducción"}}
    """
    response = self._llm_client.call_model(prompt)
    return json.loads(response)
```

## Comando CLI

### Interfaz

```bash
pdftranslator build-glossary --work-id 1 [OPTIONS]

Opciones:
  --work-id INT         Obligatorio. ID de la obra
  --volume-number INT   Opcional. Número de volumen
  --chapter-number INT  Opcional. Número de capítulo (requiere --volume-number)
  --all                 Procesar toda la obra
  --min-frequency INT   Mínimo de ocurrencias (default: 2)
  --source-lang TEXT    Idioma origen (default: en)
  --target-lang TEXT    Idioma destino (default: es)
  --dry-run             Solo mostrar entidades sin guardar
```

### Visualización

```
╭──────────────────────────────────────────╮
│  The Beginning After The End             │
│  Título traducido: El Principio del Fin  │
╰──────────────────────────────────────────╯

⠋ Procesando Volumen 1... ━━━━━━━━━━━━━━━━━━━━━━━━━━ 100%

╭─────────────── Resumen de Extracción ───────────────╮
│ Métrica                      Cantidad               │
├─────────────────────────────────────────────────────┤
│ Entidades detectadas              47                 │
│ Entidades nuevas                  32                 │
│ Duplicados (ignorados)            15                 │
╰─────────────────────────────────────────────────────╯

Distribución por tipo de entidad:

 Personajes     ████████████████████ 18
 Lugares        ████████████ 8
 Habilidades    ████████ 4
 Obetos         ████ 2
```

## Dependencias

```txt
nltk>=3.8.0
```

### Recursos NLTK (descarga automática)

- punkt, punkt_tab
- averaged_perceptron_tagger
- maxent_ne_chunker
- words

## Archivos a Crear/Modificar

### Nuevos archivos

| Archivo | Descripción |
|---------|-------------|
| `database/schemas/007_glossary_extensions.sql` | ALTER TABLE glossary_terms |
| `database/schemas/008_entity_blacklist.sql` | Tabla entity_blacklist |
| `database/schemas/009_fantasy_terms.sql` | Tabla fantasy_terms |
| `database/repositories/entity_blacklist_repository.py` | Repositorio CRUD |
| `database/repositories/fantasy_term_repository.py` | Repositorio CRUD |
| `database/services/entity_extractor.py` | NER + heurísticas |
| `database/services/glossary_manager.py` | Pipeline completo |
| `cli/commands/build_glossary.py` | Comando CLI |

### Archivos a modificar

| Archivo | Cambio |
|---------|--------|
| `database/models.py` | Añadir EntityBlacklist, FantasyTerm, campos GlossaryEntry |
| `database/repositories/glossary_repository.py` | Nuevos métodos |
| `database/repositories/__init__.py` | Exportar nuevos repositorios |
| `database/services/vector_store.py` | Método embed_entities_for_glossary |
| `database/services/__init__.py` | Exportar nuevos servicios |
| `cli/app.py` | Registrar comando build_glossary |
| `GlobalConfig.py` | Añadir config NER |

## Consideraciones

1. **Frecuencia mínima fija = 2**: Descarta entidades que aparecen solo una vez
2. **Listas dinámicas en DB**: entity_blacklist y fantasy_terms son editables
3. **is_verified=False**: Todas las entradas nuevas requieren verificación manual
4. **Embeddings automáticos**: Se generan para todas las entidades nuevas
5. **Traducción sugerida**: LLM propone traducción, pero queda pendiente verificación
