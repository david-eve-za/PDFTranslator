# Split Text Block Parsing Extension Design

## Overview
Extiende el comando `split-text` para parsear bloques estructurados del texto editado, creando Chapters automáticamente basándose en marcadores especiales.

## Block Format

```
[===Type="Prologue"===]
Texto del prólogo...
[===End Block===]

[===Type="Chapter" Title="Meet the King"===]
Texto del capítulo 1...
[===End Block===]

[===Type="Epilogue"===]
Texto del epílogo...
[===End Block===]
```

## Architecture

### New Components

#### `ParsedBlock` (dataclass)
```python
@dataclass
class ParsedBlock:
    block_type: str  # "Prologue", "Chapter", "Epilogue"
    title: Optional[str]
    content: str
    start_line: int
    end_line: int
```

#### `BlockParseError` (exception)
```python
class BlockParseError(Exception):
    def __init__(self, message: str, line_number: int):
        self.message = message
        self.line_number = line_number
        super().__init__(f"Line {line_number}: {message}")
```

### Functions

#### `build_template_header() -> str`
Genera el comentario inicial con instrucciones y ejemplos de formato.

#### `parse_blocks(text: str) -> List[ParsedBlock]`
Parsea el texto completo y retorna lista de bloques estructurados.
- Detecta marcadores `[===Type="..." Title="..."===]` y `[===End Block===]`
- Valida que los tipos sean válidos: Prologue, Chapter, Epilogue
- Lanza `BlockParseError` con línea específica si hay errores

#### `validate_and_create_chapters(volume_id: int, blocks: List[ParsedBlock], chapter_repo: ChapterRepository) -> int`
- Elimina todos los chapters existentes del volumen
- Crea nuevos chapters con numeración apropiada:
  - Prologue: `chapter_number = None`
  - Chapter: numerados secuencialmente 1, 2, 3...
  - Epilogue: `chapter_number = None`
- Retorna el número de chapters creados

### Modified Flow

1. **Create temp file** → Add template header with instructions
2. **Open editor** → User edits and closes
3. **Read edited text** → Strip instruction header
4. **Parse blocks** → Extract structured data
5. **Validate format** → Abort with detailed error if invalid
6. **Update Volume** → Save full_text to database
7. **Delete existing chapters** → Clear old chapters for this volume
8. **Create new chapters** → Insert parsed blocks as Chapter records

## Error Handling

### Block Format Errors
- **Missing end marker**: "Block starting at line X has no matching [===End Block===]"
- **Invalid type**: "Line X: Type must be 'Prologue', 'Chapter', or 'Epilogue'"
- **Malformed attributes**: "Line X: Invalid attribute format, expected Type=\"value\""
- **Unclosed block**: "File ends with unclosed block starting at line X"

### Error Display
```
[red]Error parsing blocks:[/red]
[red]  Line 45: Block starting at line 45 has no matching [===End Block===[/red]
[yellow]Please fix the format and try again.[/yellow]
```

## Template Header Example

```
# ============================================================
# INSTRUCCIONES DE FORMATO - NO MODIFIQUE ESTA SECCIÓN
# ============================================================
# Use los siguientes marcadores para dividir el texto:
#
# [===Type="Prologue"===]
# Texto del prólogo...
# [===End Block===]
#
# [===Type="Chapter" Title="Nombre opcional"===]
# Texto del capítulo...
# [===End Block===]
#
# [===Type="Epilogue"===]
# Texto del epílogo...
# [===End Block===]
#
# Tipos válidos: Prologue, Chapter, Epilogue
# El atributo Title es opcional
# ============================================================

[Original volume text here...]
```

## Chapter Numbering

| Block Type | chapter_number | title |
|------------|----------------|-------|
| Prologue | NULL | Optional title or NULL |
| Chapter | 1, 2, 3... | Optional title or NULL |
| Epilogue | NULL | Optional title or NULL |

## Dependencies

- `ChapterRepository` from `database/repositories/chapter_repository.py`
- `Chapter` model from `database/models.py`
- Regex for block parsing
- `re` module for pattern matching

## Implementation Notes

- Strip the instruction header before parsing (everything before the first non-comment line or after the header separator)
- Use regex pattern: `r'\[===Type="(\w+)"(?:\s+Title="([^"]*)")?===\]'`
- Track line numbers for meaningful error messages
- Trim whitespace from block content
- Empty blocks (no content between markers) are valid
- Text outside blocks is ignored (not an error)
