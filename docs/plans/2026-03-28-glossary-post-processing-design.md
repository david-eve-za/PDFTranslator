# Diseño: Sustitución de Glosario Post-Traducción

**Fecha:** 2026-03-28  
**Objetivo:** Garantizar consistencia 100% de términos del glosario mediante validación + corrección post-traducción

## Motivación

El enfoque actual inyecta el glosario en el prompt de traducción, lo que:
- Consume tokens del contexto
- No garantiza aplicación exacta de traducciones
- Requiere cálculo de overhead para chunking

El nuevo enfoque elimina el glosario del prompt y aplica validación + corrección después de la traducción.

## Arquitectura

### Flujo de Traducción Actualizado

```
Texto original → Chunking simple → Traducción por chunks → Post-procesamiento de glosario → Texto final
```

### Componentes Nuevos

#### `GlossaryPostProcessor` (`cli/services/glossary_post_processor.py`)

```python
class GlossaryPostProcessor:
    def __init__(self, glossary_entries: List[GlossaryEntry], target_lang: str)
    def process(self, translated_text: str) -> str
    def _build_variant_maps(self)
    def _validate_and_fix(self, text: str, entry: GlossaryEntry) -> str
    def _apply_grammatical_variants(self, base_translation: str) -> List[str]
```

### Componentes Modificados

#### `GlobalConfig.py`
- ❌ Eliminar `nvidia_context_size`
- ✅ Mantener `nvidia_max_output_tokens = 4096`

#### `GlossaryAwareTranslator` (`cli/commands/translate_chapter.py`)
- Simplificar `split_text_with_overhead()` → eliminar overhead de glosario
- Modificar `translate_text()` para usar post-procesamiento
- Eliminar métodos de inyección de glosario: `_calculate_prompt_overhead()`, `_build_glossary_section()`

#### `nvidia_llm.py`
- Eliminar uso de `context_size` en `split_into_limit()`
- Usar solo `max_output_tokens` como referencia

## Generación de Variantes Flexibles

### Reglas de Variación

1. **Términos con traducción definida** (`dragon → dragón`):
   - Buscar: `dragón`, `dragon`, `Dragón`, `DRAGÓN`, `dragones`, `Dragones`
   - Corregir variantes incorrectas a la traducción canónica

2. **Términos "DO NOT TRANSLATE"**:
   - Verificar que el término original aparece exactamente
   - Detectar traducciones erróneas (ej: `ki` traducido como `energía`)
   - Revertir al término original

3. **Términos sin traducción definida**:
   - Identificar traducción elegida por el modelo en primera aparición
   - Usar esa para las siguientes apariciones (consistencia interna)

### Concordancia Gramatical (Español)

Generar variantes morfológicas automáticamente:
- Singular/plural: `dragón` → `dragones`
- Mayúsculas: `Dragón`, `DRAGÓN`
- Con artículo: `el dragón` → `los dragones`

## Edge Cases

| Caso | Solución |
|------|----------|
| Término en contexto diferente | Usar word boundaries (`\b`) en regex |
| Término parcialmente contenido | Word boundaries evitan reemplazos parciales |
| Primera aparición sin traducción | Registrar traducción del modelo, usar para siguientes |
| Concordancia gramatical | Generar variantes morfológicas |

## Logging

- **DEBUG:** Cada corrección realizada
- **INFO:** Contador de correcciones por término
- **WARNING:** Si hay muchas inconsistencias (posible problema)

## Plan de Implementación

### Fase 1: Simplificar Config
1. Eliminar `nvidia_context_size` de `GlobalConfig.py`
2. Actualizar `_get_expected_types()`
3. Modificar `nvidia_llm.py` para no usar `context_size`

### Fase 2: Crear GlossaryPostProcessor
1. Crear `cli/services/glossary_post_processor.py`
2. Implementar `_build_variant_maps()`
3. Implementar `process()` con validación flexible
4. Implementar `_validate_and_fix()` con word boundaries

### Fase 3: Modificar GlossaryAwareTranslator
1. Simplificar `split_text_with_overhead()`
2. Modificar `translate_text()` para usar post-procesamiento
3. Eliminar código de inyección de glosario

### Fase 4: Tests
1. Tests unitarios para `GlossaryPostProcessor`
2. Tests de integración de traducción completa

### Fase 5: Cleanup
1. Eliminar funciones/métodos obsoletos
2. Actualizar docstrings

## Métricas de Éxito

- ✅ 100% de términos del glosario aplicados consistentemente
- ✅ Reducción de chunks (mismo texto, menos llamadas API)
- ✅ Tiempo total de traducción reducido
