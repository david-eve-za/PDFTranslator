# Design: Integración de Docling en Document Chapter Splitter

**Fecha:** 2025-04-04
**Autor:** Claude (brainstorming skill)
**Estado:** Aprobado para implementación

## Resumen Ejecutivo

Integrar Docling como motor de extracción de documentos para mejorar la precisión en la detección de secciones narrativas (prólogo, capítulos, epílogo) y reducir la dependencia del LLM para tareas de parsing estructural.

## Motivación

### Problema Actual

El `document_chapter_splitter.py` actual utiliza:

1. **PyMuPDF** para PDFs → texto plano sin estructura
2. **python-docx** para DOCX → párrafos sin jerarquía
3. **LLM** para detectar secciones → costoso, impreciso con fragmentos

Limitaciones:
- Fragmentación arbitraria de capítulos (chunks por tamaño de tokens)
- El LLM recibe fragmentos incompletos de capítulos
- Marcadores manuales (`start_marker`, `end_marker`) propensos a errores
- No soporta PDFs escaneados (sin OCR)

### Solución Propuesta

Usar **Docling** para:
- Extraer estructura jerárquica nativa (headings, secciones)
- Generar Markdown estructurado automáticamente
- OCR integrado para PDFs escaneados
- Chunks por sección completa (no por tamaño)

## Arquitectura

### Flujo de Datos

```
Documento (PDF/DOCX/EPUB)
    ↓
DoclingExtractor.extract()
    ↓
DoclingDocument (estructura jerárquica)
    ↓
SectionGrouper.group_by_sections()
    ↓
Lista de secciones [{title, level, content}]
    ↓
LLMClassifier.classify_section() (por cada sección)
    ↓
Filtrado de secciones narrativas
    ↓
ExportSection.export()
```

### Componentes Nuevos

#### 1. `infrastructure/document/docling_extractor.py`

```python
from docling.document_converter import DocumentConverter
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling_core.types.doc import DoclingDocument

class DoclingExtractor:
    """Extrae documentos usando Docling con configuración optimizada."""
    
    def __init__(self, config: DoclingConfig | None = None):
        self.config = config or DoclingConfig()
        self._converter = self._create_converter()
    
    def extract(self, filepath: str) -> DoclingDocument:
        """Extrae documento y retorna DoclingDocument estructurado."""
        result = self._converter.convert(filepath)
        return result.document
    
    def _create_converter(self) -> DocumentConverter:
        """Crea converter con pipeline configurado."""
        # Configuración específica según self.config
        ...
```

#### 2. `infrastructure/document/section_grouper.py`

```python
from docling_core.types.doc import DoclingDocument, SectionHeaderItem, TextItem

class SectionGrouper:
    """Agrupa contenido por secciones usando la jerarquía de Docling."""
    
    def group_by_sections(self, doc: DoclingDocument) -> list[dict]:
        """
        Itera sobre el documento y agrupa contenido bajo cada header.
        
        Returns:
            [{"title": str, "level": int, "content": str, "start_page": int}, ...]
        """
        sections = []
        current_section = {"title": "Untitled", "level": 0, "content": []}
        
        for item, level in doc.iterate_items():
            if isinstance(item, SectionHeaderItem):
                if current_section["content"]:
                    sections.append(self._finalize_section(current_section))
                current_section = {
                    "title": item.text,
                    "level": level,
                    "content": []
                }
            elif isinstance(item, TextItem):
                current_section["content"].append(item.text)
        
        # Agregar última sección
        if current_section["content"]:
            sections.append(self._finalize_section(current_section))
        
        return sections
    
    def _finalize_section(self, section: dict) -> dict:
        section["content"] = "\n\n".join(section["content"])
        return section
```

#### 3. `config/document.py`

```python
from pydantic import BaseModel, Field

class DoclingConfig(BaseModel):
    """Configuración para extracción con Docling."""
    
    enable_ocr: bool = Field(
        default=True,
        description="Habilitar OCR para PDFs escaneados"
    )
    ocr_languages: list[str] = Field(
        default=["en", "es"],
        description="Idiomas para OCR"
    )
    do_table_structure: bool = Field(
        default=False,
        description="Extraer estructura de tablas (no necesario para novelas)"
    )
    generate_page_images: bool = Field(
        default=False,
        description="Generar imágenes de páginas"
    )
    accelerator_device: str = Field(
        default="auto",
        description="Dispositivo de aceleración: auto, cpu, cuda, mps"
    )
```

### Modificaciones a `document_chapter_splitter.py`

| Función | Cambio |
|---------|--------|
| `extract_text()` | **Eliminar** - reemplazar por `DoclingExtractor` |
| `analyze_chunk_with_llm()` | **Refactor** - input es una sección completa, no fragmento |
| `split_into_limit()` | **Eliminar** - secciones completas son los chunks |
| `merge_sections()` | **Simplificar** - menos merge necesario |
| `export_sections()` | **Mantener** - compatible con nuevo formato |

#### Nuevo Prompt para LLM

```python
SECTION_CLASSIFICATION_PROMPT = """
Eres un clasificador de secciones de libros narrativos.

Tu tarea es clasificar una sección como:
- "prologue": Prólogo o prefacio del autor
- "chapter": Capítulo numerado o titulado
- "epilogue": Epílogo o postfacio
- "other": Índice, agradecimientos, derechos, publicidad, etc.

INPUT:
Título: {title}
Primeras 300 caracteres del contenido:
{content_preview}

Responde SOLO con JSON válido:
{{"type": "prologue"|"chapter"|"epilogue"|"other", "number": <int|null>}}

Ejemplos:
Input: "Capítulo 5: La batalla" → {{"type": "chapter", "number": 5}}
Input: "Prólogo" → {{"type": "prologue", "number": null}}
Input: "Índice" → {{"type": "other", "number": null}}
"""
```

## Dependencias

### Ya Instaladas

Docling ya está en `environment.yml`:
```yaml
- docling
- docling-core
```

### Dependencias Transitorias

Docling instala automáticamente:
- PyTorch (para modelos de layout)
- transformers (para modelos HuggingFace)
- Pillow (manejo de imágenes)

## Plan de Implementación

### Fase 1: Implementación en Paralelo (Sin Romper)

1. Crear `infrastructure/document/docling_extractor.py`
2. Crear `infrastructure/document/section_grouper.py`
3. Crear `config/document.py` con `DoclingConfig`
4. Tests unitarios para nuevos componentes

### Fase 2: Integración con Feature Flag

5. Modificar `document_chapter_splitter.py`:
   - Añadir parámetro `use_docling: bool = True`
   - Mantener path antiguo para retrocompatibilidad
6. Tests de integración

### Fase 3: Deprecación

7. Marcar `extract_text()` como deprecated
8. Documentar migración
9. Remover código legacy después de validación

## Tests

### Tests Unitarios

```python
# tests/infrastructure/document/test_docling_extractor.py

def test_extract_pdf_returns_docling_document():
    extractor = DoclingExtractor()
    doc = extractor.extract("tests/fixtures/sample.pdf")
    assert isinstance(doc, DoclingDocument)
    assert len(doc.pages) > 0

def test_extract_docx_preserves_headings():
    extractor = DoclingExtractor()
    doc = extractor.extract("tests/fixtures/sample.docx")
    
    headers = [
        item for item, _ in doc.iterate_items()
        if isinstance(item, SectionHeaderItem)
    ]
    assert len(headers) > 0

# tests/infrastructure/document/test_section_grouper.py

def test_group_by_sections_creates_sections():
    grouper = SectionGrouper()
    sections = grouper.group_by_sections(mock_docling_document)
    
    assert len(sections) > 0
    assert all("title" in s and "content" in s for s in sections)

def test_nested_headers_increase_level():
    grouper = SectionGrouper()
    sections = grouper.group_by_sections(doc_with_nested_headers)
    
    assert sections[0]["level"] < sections[1]["level"]
```

### Tests de Integración

```python
# tests/test_document_chapter_splitter_docling.py

def test_split_document_with_docling_produces_narrative_sections():
    split_document("tests/fixtures/novel.pdf", output_dir="./test_output")
    
    # Verificar que se exportaron solo secciones narrativas
    output_files = list(Path("./test_output").glob("*.txt"))
    assert any("chapter" in f.name for f in output_files)

def test_docling_vs_legacy_produces_similar_results():
    # Comparar resultados de ambos enfoques
    ...
```

## Métricas de Éxito

| Métrica | Actual | Objetivo |
|---------|--------|----------|
| Precisión detección de capítulos | ~70% | >95% |
| Tokens enviados al LLM | 100% | <30% (solo clasificación) |
| Tiempo de procesamiento | Baseline | ±20% |
| Soporte PDFs escaneados | No | Sí |

## Riesgos y Mitigaciones

### Riesgo 1: Dependencias Pesadas

**Problema:** Docling instala PyTorch (~2GB)
**Mitigación:** Ya está en el environment; evaluar CPU-only si es necesario

### Riesgo 2: Overhead de Procesamiento

**Problema:** Docling puede ser más lento que PyMuPDF puro
**Mitigación:** Cachear resultados de extracción; usar modo FAST para documentos simples

### Riesgo 3: Falso Negativos en Headings

**Problema:** Novelas sin headings explícitos (ej: solo "1", "2" como número)
**Mitigación:** Heurística adicional para detectar patrones numéricos como capítulos

## Alternativas Consideradas

1. **PyMuPDF + Regex:** Más rápido pero menos preciso
2. **Unstructured:** Similar a Docling, pero menos integración con LLM ecosystem
3. **Marker:** Solo PDF a Markdown, sin estructura jerárquica

## Referencias

- [Docling Documentation](https://github.com/docling-project/docling)
- [Docling Core Types](https://github.com/docling-project/docling-core)
- Context7 Query Results (ver historial de investigación)
