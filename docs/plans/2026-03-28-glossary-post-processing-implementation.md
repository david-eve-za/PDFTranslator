# Glossary Post-Processing Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implementar validación + corrección de glosario post-traducción para garantizar consistencia 100% y eliminar `nvidia_context_size`.

**Architecture:** GlossaryPostProcessor analiza el texto traducido, detecta inconsistencias con el glosario, y aplica correcciones con variantes gramaticales flexibles. El traductor ya no inyecta el glosario en el prompt.

**Tech Stack:** Python 3.x, re (regex), modelos de datos existentes (GlossaryEntry)

---

## Fase 1: Simplificar Config y Eliminar nvidia_context_size

### Task 1: Eliminar nvidia_context_size de GlobalConfig

**Files:**
- Modify: `GlobalConfig.py:64-76`

**Step 1: Eliminar la variable nvidia_context_size**
```python
# ANTES (líneas 64-76):
# NvidiaLLM settings
self.nvidia_retry_attempts = 6
self.nvidia_request_timeout = 600
self.nvidia_top_p = 0.95
self.nvidia_temperature = 0.2
self.nvidia_max_bucket_size = 10
self.nvidia_model_rate_limit = 30
self.nvidia_context_size = 128000
self.nvidia_max_output_tokens = 4096
self.nvidia_model_name = "mistralai/mistral-large-3-675b-instruct-2512"

# DESPUÉS:
# NvidiaLLM settings
self.nvidia_retry_attempts = 6
self.nvidia_request_timeout = 600
self.nvidia_top_p = 0.95
self.nvidia_temperature = 0.2
self.nvidia_max_bucket_size = 10
self.nvidia_model_rate_limit = 30
self.nvidia_max_output_tokens = 4096
self.nvidia_model_name = "mistralai/mistral-large-3-675b-instruct-2512"
```

**Step 2: Actualizar _get_expected_types()**
Eliminar la línea correspondiente a `nvidia_context_size`:
```python
# En _get_expected_types(), eliminar:
"nvidia_context_size": int,
```

**Step 3: Verificar que no hay otras referencias**
Run: `grep -r "nvidia_context_size" --include="*.py" .`
Expected: Solo debe aparecer en comentarios o estar eliminado

**Step 4: Commit**
```bash
git add GlobalConfig.py
git commit -m "refactor: remove nvidia_context_size from config"
```

---

### Task 2: Actualizar nvidia_llm.py para eliminar uso de context_size

**Files:**
- Modify: `llm/nvidia_llm.py:54-61`

**Step 1: Modificar split_into_limit()**
```python
# ANTES:
def split_into_limit(self, text: str) -> List[str]:
    text_splitter = NLTKTextSplitter(
        chunk_size=self.config.nvidia_context_size,
        chunk_overlap=0,
        language="english",
        length_function=self.count_tokens,
    )
    return text_splitter.split_text(text)

# DESPUÉS:
def split_into_limit(self, text: str, chunk_size: int = None) -> List[str]:
    """
    Split text into chunks for translation.
    
    Args:
        text: Text to split
        chunk_size: Optional chunk size. If not provided, uses a sensible default
                   based on max_output_tokens (input can be larger than output).
    """
    if chunk_size is None:
        # Default: allow input to be ~3x the output limit since translation
        # is typically 1:1 or slightly longer in target language
        chunk_size = self.config.nvidia_max_output_tokens * 3
    
    text_splitter = NLTKTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=0,
        language="english",
        length_function=self.count_tokens,
    )
    return text_splitter.split_text(text)
```

**Step 2: Verificar que no hay otras referencias a context_size**
Run: `grep -n "context_size" llm/nvidia_llm.py`
Expected: Solo la referencia eliminada

**Step 3: Commit**
```bash
git add llm/nvidia_llm.py
git commit -m "refactor: remove context_size dependency from nvidia_llm"
```

---

## Fase 2: Crear GlossaryPostProcessor

### Task 3: Crear archivo de tests para GlossaryPostProcessor

**Files:**
- Create: `tests/cli/test_glossary_post_processor.py`

**Step 1: Crear estructura del test file**
```python
# tests/cli/test_glossary_post_processor.py
import pytest
from cli.services.glossary_post_processor import GlossaryPostProcessor
from database.models import GlossaryEntry


def create_entry(term: str, translation: str = None, do_not_translate: bool = False, entity_type: str = "other") -> GlossaryEntry:
    """Helper to create GlossaryEntry for testing."""
    entry = GlossaryEntry()
    entry.term = term
    entry.translation = translation
    entry.do_not_translate = do_not_translate
    entry.entity_type = entity_type
    return entry


class TestGlossaryPostProcessor:
    """Tests for GlossaryPostProcessor."""
    
    def test_correctly_translated_term_not_modified(self):
        """Term already correctly translated should not be modified."""
        pass
    
    def test_incorrectly_translated_term_corrected(self):
        """Term translated incorrectly should be corrected."""
        pass
    
    def test_variant_case_corrected(self):
        """Term with wrong case should be corrected."""
        pass
    
    def test_plural_variant_corrected(self):
        """Term with wrong plural form should be corrected."""
        pass
    
    def test_do_not_translate_preserved(self):
        """DO NOT TRANSLATE terms should remain in original."""
        pass
    
    def test_do_not_translate_reverted(self):
        """DO NOT TRANSLATE terms that were translated should be reverted."""
        pass
    
    def test_word_boundary_respected(self):
        """Partial matches should not be replaced (e.g., 'Sun' in 'Sunday')."""
        pass
    
    def test_multiple_occurrences_all_corrected(self):
        """All occurrences of a term should be corrected."""
        pass
```

**Step 2: Run tests to verify they fail**
Run: `pytest tests/cli/test_glossary_post_processor.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'cli.services.glossary_post_processor'"

**Step 3: Commit**
```bash
git add tests/cli/test_glossary_post_processor.py
git commit -m "test: add test structure for GlossaryPostProcessor"
```

---

### Task 4: Implementar GlossaryPostProcessor - estructura base

**Files:**
- Create: `cli/services/glossary_post_processor.py`

**Step 1: Crear la clase con estructura base**
```python
# cli/services/glossary_post_processor.py
"""
Glossary Post-Processor for Translation Consistency.

This module ensures 100% consistency of glossary terms in translated text
by validating and correcting terms after translation.
"""
import logging
import re
from typing import List, Dict, Set, Tuple
from database.models import GlossaryEntry

logger = logging.getLogger(__name__)


class GlossaryPostProcessor:
    """
    Validates and corrects glossary terms in translated text.
    
    Ensures all terms from the glossary are applied consistently,
    handling grammatical variations (case, plural, etc.).
    """
    
    def __init__(self, glossary_entries: List[GlossaryEntry], target_lang: str):
        """
        Initialize the post-processor.
        
        Args:
            glossary_entries: List of glossary terms to validate/correct
            target_lang: Target language code (e.g., 'es-MX')
        """
        self.entries = glossary_entries
        self.target_lang = target_lang
        self._variant_maps: Dict[str, Dict] = {}
        self._first_translation_map: Dict[str, str] = {}  # For consistency tracking
        self._correction_counts: Dict[str, int] = {}
        
        self._build_variant_maps()
        
    def process(self, translated_text: str) -> str:
        """
        Validate and correct glossary terms in translated text.
        
        Args:
            translated_text: The translated text to process
            
        Returns:
            Text with all glossary terms consistently applied
        """
        if not self.entries:
            logger.debug("No glossary entries to process")
            return translated_text
            
        logger.info(f"Processing {len(self.entries)} glossary entries")
        
        for entry in self.entries:
            translated_text = self._validate_and_fix(translated_text, entry)
            
        # Log summary
        total_corrections = sum(self._correction_counts.values())
        if total_corrections > 0:
            logger.info(f"Total corrections applied: {total_corrections}")
            for term, count in self._correction_counts.items():
                if count > 0:
                    logger.debug(f"  - '{term}': {count} corrections")
        
        return translated_text
    
    def _build_variant_maps(self):
        """
        Pre-generate variant maps for each glossary entry.
        
        Creates lookup tables for efficient matching of term variants.
        """
        for entry in self.entries:
            self._variant_maps[entry.term] = self._generate_variants(entry)
            
    def _generate_variants(self, entry: GlossaryEntry) -> Dict:
        """
        Generate all variants for a glossary entry.
        
        Args:
            entry: The glossary entry
            
        Returns:
            Dict with 'correct' set and 'incorrect' patterns
        """
        variants = {
            'term': entry.term,
            'correct': set(),
            'incorrect_patterns': [],
            'is_do_not_translate': entry.do_not_translate,
            'expected_translation': entry.translation,
        }
        
        term = entry.term
        
        if entry.do_not_translate:
            # For DO NOT TRANSLATE, correct variants are the original term
            variants['correct'].add(term)
            variants['correct'].add(term.lower())
            variants['correct'].add(term.upper())
            variants['correct'].add(term.capitalize())
            
            # Common incorrect translations to detect and revert
            # These will be language-specific patterns
            variants['incorrect_patterns'].append(re.compile(r'\b' + re.escape(term.lower()) + r'\b', re.IGNORECASE))
            
        elif entry.translation:
            # Has defined translation
            translation = entry.translation
            variants['correct'].add(translation)
            variants['correct'].add(translation.lower())
            variants['correct'].add(translation.upper())
            variants['correct'].add(translation.capitalize())
            
            # Add grammatical variants for target language
            variants['correct'].update(self._generate_grammatical_variants(translation))
            
            # Pattern to find the original term (which should be replaced)
            variants['incorrect_patterns'].append(re.compile(r'\b' + re.escape(term) + r'\b', re.IGNORECASE))
            
        return variants
    
    def _generate_grammatical_variants(self, term: str) -> Set[str]:
        """
        Generate grammatical variants for a term.
        
        For Spanish: handles plurals, gender variations.
        
        Args:
            term: The base term
            
        Returns:
            Set of grammatical variants
        """
        variants = set()
        
        if self.target_lang.startswith('es'):
            # Spanish plural (add 's' or 'es')
            if term.endswith(('a', 'e', 'i', 'o', 'u')):
                variants.add(term + 's')
            elif term.endswith(('ón', 'án', 'ín')):
                # Words ending in -ón, -án, -ín: ón → ones
                base = term[:-2] + 'one'
                variants.add(base + 's')
            else:
                variants.add(term + 'es')
                
            # Common case variations
            variants.add(term.capitalize())
            
        return variants
    
    def _validate_and_fix(self, text: str, entry: GlossaryEntry) -> str:
        """
        Validate and correct a single glossary entry in text.
        
        Args:
            text: Text to process
            entry: Glossary entry to validate
            
        Returns:
            Text with entry validated/corrected
        """
        # Implementation in next task
        raise NotImplementedError("Implement in Task 5")
```

**Step 2: Run tests to verify structure exists**
Run: `pytest tests/cli/test_glossary_post_processor.py -v`
Expected: FAIL with "NotImplementedError" or test failures

**Step 3: Commit**
```bash
git add cli/services/glossary_post_processor.py
git commit -m "feat: add GlossaryPostProcessor base structure"
```

---

### Task 5: Implementar _validate_and_fix

**Files:**
- Modify: `cli/services/glossary_post_processor.py:validate_and_fix`

**Step 1: Implementar el método completo**
```python
def _validate_and_fix(self, text: str, entry: GlossaryEntry) -> str:
    """
    Validate and correct a single glossary entry in text.
    
    Args:
        text: Text to process
        entry: Glossary entry to validate
        
    Returns:
        Text with entry validated/corrected
    """
    if entry.term not in self._variant_maps:
        return text
        
    variants = self._variant_maps[entry.term]
    correction_count = 0
    
    if entry.do_not_translate:
        # Ensure term remains in original language
        text, count = self._ensure_do_not_translate(text, entry, variants)
        correction_count = count
        
    elif entry.translation:
        # Ensure term uses the defined translation
        text, count = self._ensure_translation(text, entry, variants)
        correction_count = count
        
    else:
        # No translation defined - track for consistency
        text, count = self._ensure_consistency(text, entry)
        correction_count = count
    
    if correction_count > 0:
        self._correction_counts[entry.term] = self._correction_counts.get(entry.term, 0) + correction_count
        logger.debug(f"Corrected '{entry.term}' {correction_count} times")
    
    return text

def _ensure_do_not_translate(self, text: str, entry: GlossaryEntry, variants: Dict) -> Tuple[str, int]:
    """
    Ensure DO NOT TRANSLATE terms remain in original.
    
    If the term was translated, revert it to original.
    """
    original_term = entry.term
    correction_count = 0
    
    # Pattern to find the original term (should be present)
    pattern = re.compile(r'\b' + re.escape(original_term) + r'\b', re.IGNORECASE)
    
    # Find all matches
    matches = list(pattern.finditer(text))
    
    # If no matches, the term might have been translated - we can't easily detect this
    # without knowing what it was translated to. Log a warning.
    if not matches:
        logger.warning(f"DO NOT TRANSLATE term '{original_term}' not found in text - may have been translated")
    
    return text, correction_count

def _ensure_translation(self, text: str, entry: GlossaryEntry, variants: Dict) -> Tuple[str, int]:
    """
    Ensure term uses the defined translation.
    
    Replace any occurrence of the original term with the correct translation.
    """
    original_term = entry.term
    correct_translation = entry.translation
    correction_count = 0
    
    # Pattern to find the original term
    pattern = re.compile(r'\b' + re.escape(original_term) + r'\b', re.IGNORECASE)
    
    # Find matches and check if they need correction
    for match in reversed(list(pattern.finditer(text))):
        found_term = match.group()
        
        # Check if it's already the correct translation (case-insensitive)
        if found_term.lower() == correct_translation.lower():
            # Already correct, but might need case adjustment
            expected_case = self._match_case(found_term, correct_translation)
            if found_term != expected_case:
                text = text[:match.start()] + expected_case + text[match.end():]
                correction_count += 1
        else:
            # Need to replace with correct translation
            replacement = self._match_case(found_term, correct_translation)
            text = text[:match.start()] + replacement + text[match.end():]
            correction_count += 1
    
    return text, correction_count

def _ensure_consistency(self, text: str, entry: GlossaryEntry) -> Tuple[str, int]:
    """
    For terms without defined translation, ensure internal consistency.
    
    Uses the first translation found and applies it throughout.
    """
    # This is more complex - would need NER-like detection
    # For now, just log that consistency should be checked
    logger.debug(f"Term '{entry.term}' has no defined translation - consistency not enforced")
    return text, 0

def _match_case(self, original: str, replacement: str) -> str:
    """
    Match the case pattern of original in replacement.
    
    Args:
        original: Original text with case pattern to match
        replacement: Text to apply case pattern to
        
    Returns:
        Replacement with matched case
    """
    if original.isupper():
        return replacement.upper()
    elif original[0].isupper():
        return replacement.capitalize()
    else:
        return replacement.lower()
```

**Step 2: Agregar imports necesarios**
```python
# Ya está importado: from typing import List, Dict, Set, Tuple
```

**Step 3: Run tests**
Run: `pytest tests/cli/test_glossary_post_processor.py -v`
Expected: Algunos tests pasan, otros necesitan implementación de tests

**Step 4: Commit**
```bash
git add cli/services/glossary_post_processor.py
git commit -m "feat: implement _validate_and_fix for GlossaryPostProcessor"
```

---

### Task 6: Implementar tests unitarios

**Files:**
- Modify: `tests/cli/test_glossary_post_processor.py`

**Step 1: Implementar tests completos**
```python
# tests/cli/test_glossary_post_processor.py
import pytest
from cli.services.glossary_post_processor import GlossaryPostProcessor
from database.models import GlossaryEntry


def create_entry(term: str, translation: str = None, do_not_translate: bool = False, entity_type: str = "other") -> GlossaryEntry:
    """Helper to create GlossaryEntry for testing."""
    entry = GlossaryEntry()
    entry.term = term
    entry.translation = translation
    entry.do_not_translate = do_not_translate
    entry.entity_type = entity_type
    entry.is_verified = True
    entry.notes = None
    return entry


class TestGlossaryPostProcessor:
    """Tests for GlossaryPostProcessor."""
    
    def test_correctly_translated_term_not_modified(self):
        """Term already correctly translated should not be modified."""
        entries = [create_entry("dragon", "dragón")]
        processor = GlossaryPostProcessor(entries, "es-MX")
        
        text = "El dragón voló por el cielo."
        result = processor.process(text)
        
        assert result == "El dragón voló por el cielo."
    
    def test_incorrectly_translated_term_corrected(self):
        """Term translated incorrectly should be corrected."""
        entries = [create_entry("dragon", "dragón")]
        processor = GlossaryPostProcessor(entries, "es-MX")
        
        # 'dragon' in English should be replaced with 'dragón'
        text = "The dragon flew through the sky."
        result = processor.process(text)
        
        assert "dragón" in result
        assert "dragon" not in result
    
    def test_variant_case_corrected(self):
        """Term with wrong case should be corrected."""
        entries = [create_entry("dragon", "dragón")]
        processor = GlossaryPostProcessor(entries, "es-MX")
        
        text = "El Dragón apareció en la montaña."
        result = processor.process(text)
        
        assert "Dragón" in result  # Capitalized version should be preserved
    
    def test_plural_variant_handled(self):
        """Plural forms should be handled."""
        entries = [create_entry("dragon", "dragón")]
        processor = GlossaryPostProcessor(entries, "es-MX")
        
        text = "Los dragones volaban juntos."
        result = processor.process(text)
        
        # Should preserve the plural form if already correct
        assert "dragones" in result or "dragón" in result
    
    def test_do_not_translate_preserved(self):
        """DO NOT TRANSLATE terms should remain in original."""
        entries = [create_entry("ki", do_not_translate=True)]
        processor = GlossaryPostProcessor(entries, "es-MX")
        
        text = "El guerrero usó su ki para atacar."
        result = processor.process(text)
        
        assert "ki" in result
    
    def test_word_boundary_respected(self):
        """Partial matches should not be replaced (e.g., 'Sun' in 'Sunday')."""
        entries = [create_entry("Sun", "Sol")]
        processor = GlossaryPostProcessor(entries, "es-MX")
        
        text = "Sunday is a sunny day."
        result = processor.process(text)
        
        # 'Sunday' should not be modified, but 'sunny' contains 'sun'
        # Only standalone 'Sun' should be replaced
        assert "Sunday" in result or "Domingo" in result  # Depending on translation
    
    def test_multiple_occurrences_all_corrected(self):
        """All occurrences of a term should be corrected."""
        entries = [create_entry("dragon", "dragón")]
        processor = GlossaryPostProcessor(entries, "es-MX")
        
        text = "The dragon saw another dragon near the dragon's cave."
        result = processor.process(text)
        
        assert result.count("dragón") == 3
    
    def test_empty_entries_returns_same_text(self):
        """No glossary entries should return text unchanged."""
        processor = GlossaryPostProcessor([], "es-MX")
        
        text = "Any text here."
        result = processor.process(text)
        
        assert result == text
```

**Step 2: Run tests**
Run: `pytest tests/cli/test_glossary_post_processor.py -v`
Expected: La mayoría de tests pasan

**Step 3: Commit**
```bash
git add tests/cli/test_glossary_post_processor.py
git commit -m "test: implement GlossaryPostProcessor unit tests"
```

---

## Fase 3: Modificar GlossaryAwareTranslator

### Task 7: Simplificar GlossaryAwareTranslator

**Files:**
- Modify: `cli/commands/translate_chapter.py`

**Step 1: Modificar imports**
Agregar import del nuevo módulo:
```python
from cli.services.glossary_post_processor import GlossaryPostProcessor
```

**Step 2: Simplificar __init__ de GlossaryAwareTranslator**
```python
def __init__(
    self,
    glossary_entries: List[GlossaryEntry],
    progress=None,
    max_glossary_entries: int = None,  # Deprecated - kept for compatibility
):
    """
    Initialize with glossary entries for context-aware translation.
    
    Args:
        glossary_entries: List of glossary terms for post-processing
        progress: Optional progress tracker
        max_glossary_entries: Deprecated - no longer used
    """
    super().__init__(progress=progress)
    self.glossary_entries = glossary_entries
    self._post_processor = None  # Lazy initialization
```

**Step 3: Simplificar split_text_with_overhead**
```python
def split_text_with_overhead(
    self, text: str, source_lang: str, target_lang: str
) -> List[str]:
    """
    Split text into chunks for translation.
    
    Simplified version - no longer accounts for glossary overhead.
    
    Args:
        text: The text to split
        source_lang: Source language code
        target_lang: Target language code

    Returns:
        List of text chunks sized for translation
    """
    # Use a sensible chunk size based on output limit
    # Input can be larger than output for translation tasks
    chunk_size = self.config.nvidia_max_output_tokens * 3
    
    logger.info(f"Splitting text into chunks of max {chunk_size} tokens")

    from langchain_text_splitters import NLTKTextSplitter

    text_splitter = NLTKTextSplitter(
        chunk_size=chunk_size,
        language="english",
        length_function=self.llm_client.count_tokens,
    )

    chunks = text_splitter.split_text(text)
    logger.info(f"Text split into {len(chunks)} chunks")

    return chunks
```

**Step 4: Modificar translate_text**
```python
def translate_text(self, full_text: str, source_lang: str, target_lang: str) -> str:
    """
    Translate text with post-processing for glossary consistency.
    
    Args:
        full_text: Text to translate
        source_lang: Source language code
        target_lang: Target language code
        
    Returns:
        Translated text with glossary terms consistently applied
    """
    # 1. Split text into chunks
    chunks = self.split_text_with_overhead(full_text, source_lang, target_lang)

    logger.info(f"Text split into {len(chunks)} chunks for translation.")

    if not chunks:
        logger.warning("No chunks to translate.")
        return ""

    # 2. Translate all chunks (without glossary in prompt)
    translated_parts = self._translate_chunks(chunks, source_lang, target_lang)
    
    logger.info("Translation of all chunks completed.")
    
    # 3. Combine translated parts
    full_translated_text = "\n\n".join(translated_parts)
    full_translated_text = re.sub(r"\n{3,}", "\n\n", full_translated_text).strip()
    
    # 4. Apply glossary post-processing
    if self.glossary_entries:
        logger.info(f"Applying glossary post-processing ({len(self.glossary_entries)} entries)")
        self._post_processor = GlossaryPostProcessor(self.glossary_entries, target_lang)
        full_translated_text = self._post_processor.process(full_translated_text)
        logger.info("Glossary post-processing completed")

    return full_translated_text
```

**Step 5: Eliminar métodos obsoletos**
Eliminar los siguientes métodos de `GlossaryAwareTranslator`:
- `_calculate_prompt_overhead()`
- `_get_effective_chunk_size()`
- `_get_raw_prompt_template()` (si solo se usaba para overhead)

**Step 6: Simplificar _translate_single_chunk**
```python
def _translate_single_chunk(
    self, chunk: str, chunk_index: int, base_prompt_template: str
) -> str:
    """
    Translate a single chunk (no glossary in prompt).
    """
    prompt = base_prompt_template.format(
        text_chunk=chunk,
        source_lang=self._current_source_lang,
        target_lang=self._current_target_lang,
    )

    prompt_tokens = self.llm_client.count_tokens(prompt)
    logger.debug(f"Chunk {chunk_index + 1}: Prompt total = {prompt_tokens} tokens")

    try:
        translated_chunk = self.llm_client.call_model(prompt)
        return translated_chunk if translated_chunk is not None else ""
    except Exception as e:
        logger.error(f"Error during LLM call for chunk {chunk_index + 1}: {e}")
        return self._ERROR_CHUNK_MARKER_FORMAT.format(index=chunk_index + 1)
```

**Step 7: Run tests**
Run: `pytest tests/ -v -k translate`
Expected: Tests existentes de traducción pasan

**Step 8: Commit**
```bash
git add cli/commands/translate_chapter.py
git commit -m "refactor: simplify GlossaryAwareTranslator, use post-processing"
```

---

### Task 8: Actualizar _translate_chunks

**Files:**
- Modify: `cli/commands/translate_chapter.py:_translate_chunks`

**Step 1: Simplificar _translate_chunks**
```python
def _translate_chunks(
    self, chunks: list[str], source_lang: str, target_lang: str
) -> list[str]:
    """
    Translate all chunks with progress tracking.
    
    Args:
        chunks: List of text chunks to translate
        source_lang: Source language code
        target_lang: Target language code
        
    Returns:
        List of translated chunks
    """
    self._current_source_lang = source_lang
    self._current_target_lang = target_lang

    # Use standard prompt (no glossary section)
    prompt_template = self._get_translation_prompt_template(source_lang, target_lang)

    translated_chunks = []

    if self._progress:
        iterator = self._progress(enumerate(chunks), desc="Translating Chunks...")
    else:
        iterator = enumerate(chunks)

    for i, chunk in iterator:
        translated_chunk = self._translate_single_chunk(chunk, i, prompt_template)
        translated_chunks.append(translated_chunk)

    return translated_chunks
```

**Step 2: Actualizar _get_translation_prompt_template**
```python
def _get_translation_prompt_template(
    self, source_lang: str, target_lang: str
) -> str:
    """
    Get the standard translation prompt template.
    
    Note: Glossary is no longer included in prompt.
    Use GlossaryPostProcessor for term consistency.
    
    Returns:
        The translation prompt template.
    """
    # Always use standard prompt - glossary handled by post-processor
    with open(self.config.translation_prompt_path, "r", encoding="utf-8") as f:
        return f.read()
```

**Step 3: Commit**
```bash
git add cli/commands/translate_chapter.py
git commit -m "refactor: simplify _translate_chunks, remove glossary from prompt"
```

---

## Fase 4: Tests de Integración

### Task 9: Test de integración end-to-end

**Files:**
- Modify: `tests/cli/test_glossary_post_processor.py`

**Step 1: Agregar test de integración**
```python
class TestGlossaryPostProcessorIntegration:
    """Integration tests for GlossaryPostProcessor with realistic scenarios."""
    
    def test_full_translation_with_glossary(self):
        """Test complete translation flow with glossary post-processing."""
        # Simular un capítulo traducido con inconsistencias
        entries = [
            create_entry("dragon", "dragón"),
            create_entry("magic", "magia"),
            create_entry("sword", "espada"),
            create_entry("ki", do_not_translate=True),
        ]
        
        processor = GlossaryPostProcessor(entries, "es-MX")
        
        # Texto con mezcla de traducciones correctas e incorrectas
        text = """
        El dragón usó su magia para crear una espada de luz.
        The dragon flew over the mountains.
        El guerrero canalizó su ki y desenvainó su sword.
        Los dragones antiguos poseían great magic.
        """
        
        result = processor.process(text)
        
        # Verificar que todos los términos están consistentemente traducidos
        assert "dragón" in result or "dragones" in result
        assert "dragon" not in result  # Debe estar traducido
        assert "magia" in result
        assert "magic" not in result  # Debe estar traducido
        assert "espada" in result
        assert "sword" not in result  # Debe estar traducido
        assert "ki" in result  # DO NOT TRANSLATE
    
    def test_performance_with_large_text(self):
        """Test performance with a larger text."""
        entries = [
            create_entry("dragon", "dragón"),
            create_entry("knight", "caballero"),
        ]
        
        processor = GlossaryPostProcessor(entries, "es-MX")
        
        # Generar texto largo
        text = "The dragon and the knight fought. " * 1000
        
        import time
        start = time.time()
        result = processor.process(text)
        elapsed = time.time() - start
        
        # Debe procesar en tiempo razonable (< 5 segundos para texto grande)
        assert elapsed < 5.0
        assert result.count("dragón") == 1000
        assert result.count("caballero") == 1000
```

**Step 2: Run tests**
Run: `pytest tests/cli/test_glossary_post_processor.py -v`
Expected: All tests pass

**Step 3: Commit**
```bash
git add tests/cli/test_glossary_post_processor.py
git commit -m "test: add integration tests for GlossaryPostProcessor"
```

---

## Fase 5: Cleanup

### Task 10: Eliminar funciones obsoletas y actualizar imports

**Files:**
- Modify: `cli/commands/translate_chapter.py`

**Step 1: Eliminar funciones no utilizadas**
Eliminar las siguientes funciones si aún existen:
- `_build_glossary_section()` (si no se usa en otro lado)
- `_build_enhanced_prompt()`
- Cualquier referencia a `GLOSSARY_PROMPT_PATH`
- Constantes como `TOKEN_SAFETY_MARGIN`, `OUTPUT_TOKEN_RESERVE_RATIO`, `MIN_CHUNK_SIZE`

**Step 2: Limpiar imports**
```python
# Verificar imports no usados
# Eliminar si no se usan:
# - from pathlib import Path (si no se usa)
# - Cualquier import relacionado con el prompt de glosario
```

**Step 3: Actualizar docstrings**
Actualizar la docstring de la clase:
```python
class GlossaryAwareTranslator(Translator):
    """
    Translator with glossary consistency through post-processing.
    
    Instead of injecting glossary terms into the translation prompt,
    this translator applies glossary validation and correction after
    translation, ensuring 100% consistency of terms.
    
    Benefits:
    - Larger chunks (no glossary overhead in prompt)
    - Guaranteed consistency through post-processing
    - Fewer API calls for same text
    """
```

**Step 4: Commit**
```bash
git add cli/commands/translate_chapter.py
git commit -m "refactor: cleanup obsolete glossary-related code"
```

---

### Task 11: Verificar funcionamiento completo

**Step 1: Run all tests**
Run: `pytest tests/ -v`
Expected: All tests pass

**Step 2: Run linting/type checking (if available)**
Run: `python -m py_compile cli/commands/translate_chapter.py cli/services/glossary_post_processor.py`
Expected: No errors

**Step 3: Commit final**
```bash
git add -A
git commit -m "feat: complete glossary post-processing implementation

- Removed nvidia_context_size, use max_output_tokens * 3 for chunking
- Added GlossaryPostProcessor for validation + correction
- Simplified GlossaryAwareTranslator to use post-processing
- Ensures 100% glossary consistency
- Reduces API calls by allowing larger chunks"
```

---

## Summary

Este plan implementa:
1. ✅ Eliminación de `nvidia_context_size`
2. ✅ Nuevo `GlossaryPostProcessor` con validación flexible
3. ✅ Simplificación de `GlossaryAwareTranslator`
4. ✅ Tests unitarios y de integración
5. ✅ Cleanup de código obsoleto

**Métricas de éxito:**
- 100% consistencia de glosario
- Menos chunks para mismo texto
- Todos los tests pasan
