# Adaptive Token Chunking Configuration Guide

## Overview

PDFTranslator now uses **adaptive token chunking** for translation requests. Instead of a fixed 1,024 token chunk size, the system dynamically calculates the optimal chunk size per translation request based on:

1. **Model capacity** - Mistral Large 3 (131,072 context window, 8,192 default output)
2. **Prompt size** - Actual measured tokens of the formatted translation prompt
3. **Language-pair expansion ratio** - How much text grows/shrinks when translating (e.g., EN→ES: 1.3x, EN→ZH: 0.55x)
4. **Safety margin** - Configurable buffer (default 15%) to prevent response truncation

This typically results in **5–11× fewer API calls** compared to the old fixed strategy.

---

## Configuration Options

### Environment Variables (in `.env`)

```bash
# ── NVIDIA NIM Token Chunking ───────────────────────────────────

# Max tokens reserved for model output per request
# Higher = fewer chunks but more context used for output
# Default: 8192 (model supports up to 131072)
LLM__NVIDIA__MAX_OUTPUT_TOKENS=8192

# Safety margin percentage (0.05–0.30) to prevent truncation
# Higher = more conservative, fewer truncations
# Default: 0.15 (15%)
LLM__NVIDIA__CHUNK_SAFETY_MARGIN_PCT=0.15

# Practical upper bound per chunk (in tokens)
# Prevents excessively large chunks that NLTK may not split well
# Default: 32768
LLM__NVIDIA__MAX_CHUNK_TOKENS=32768

# Minimum viable chunk size (in tokens)
# Floor for highly expansive language pairs
# Default: 512
LLM__NVIDIA__MIN_CHUNK_TOKENS=512

# Custom expansion ratios as JSON string
# Maps "source-target" to ratio (output_tokens / input_tokens)
# Overrides built-in defaults for specific pairs
# Default: {} (uses built-in table)
# Example: '{"en-es": 1.25, "en-zh": 0.55, "fr-en": 0.85}'
LLM__NVIDIA__EXPANSION_RATIOS='{}'
```

---

## Built-in Expansion Ratios

The system includes sensible defaults for common language pairs:

| Source → Target | Ratio | Direction |
|----------------|-------|-----------|
| EN → ES/PT | 1.30 | Expansion |
| EN → FR | 1.15 | Expansion |
| EN → IT | 1.10 | Expansion |
| EN → DE/NL | 1.15–1.20 | Expansion |
| EN → PL/RU/AR | 1.15–1.20 | Expansion |
| EN → ZH | 0.55 | Contraction |
| EN → JA | 0.60 | Contraction |
| EN → KO | 0.65 | Contraction |
| EN → HI | 1.10 | Expansion |
| Reverse (→EN) | 0.80–1.80 | Varies |

**Fallback**: Unknown pairs default to **1.15** (slightly conservative expansion).

---

## Chunk Size Formula

```python
def calculate_chunk_size(
    prompt_tokens: int,      # Measured at runtime
    expansion_ratio: float,  # From language pair table
    config: NvidiaConfig,
) -> int:
    # Limit 1: Output budget / expansion
    by_output = (config.max_output_tokens / expansion_ratio) * (1 - config.chunk_safety_margin_pct)
    
    # Limit 2: Available context - prompt - reserved output
    available_context = config.context_size - prompt_tokens - config.max_output_tokens
    by_context = max(0, available_context) * (1 - config.chunk_safety_margin_pct)
    
    # Apply bounds
    chunk_size = min(by_output, by_context, config.max_chunk_tokens)
    return max(int(chunk_size), config.min_chunk_tokens)
```

---

## Expected Chunk Sizes (Default Config)

| Language Pair | Expansion | Chunk Tokens | Approx. Pages/Chunk |
|--------------|-----------|--------------|---------------------|
| EN → ES/PT | 1.30 | **5,357** | 15–20 |
| EN → FR/IT | 1.10–1.15 | **6,054–6,338** | 18–22 |
| EN → DE | 1.20 | **5,803** | 17–21 |
| EN → ZH/JA/KO | 0.55–0.65 | **11,605–12,657** | 35–45 |
| EN → AR/RU | 1.15 | **6,054** | 18–22 |

**vs. Old Fixed (1,024)**: **5.2× – 12.4× fewer chunks**

---

## Tuning Guide

### Increase `MAX_OUTPUT_TOKENS` if:
- You want even fewer chunks per translation
- Translations are being truncated (check logs for "Possible truncation" warnings)
- You have sufficient quota for larger outputs

### Increase `CHUNK_SAFETY_MARGIN_PCT` if:
- Seeing truncation warnings in logs
- Translations end mid-sentence
- Using language pairs with variable expansion

### Decrease `MAX_CHUNK_TOKENS` if:
- NLTK text splitter struggles with very large chunks
- Memory issues during translation
- Want more granular progress reporting

### Override `EXPANSION_RATIOS` if:
- Specific domain has different expansion characteristics
- Built-in ratios don't match your content type
- Translating between unsupported language pairs

---

## Logging & Observability

The system logs chunking decisions at **INFO level**:

```
INFO - Adaptive chunking: prompt=1047 tokens, expansion=1.30 (en->es), chunk_size=5357 tokens
```

And truncation warnings at **WARN level**:

```
WARNING - Possible truncation: response=7950 tokens > 7782.4 threshold (95% of max_output=8192)
```

---

## Migration from Fixed Chunking

No breaking changes required:
- Old `max_output_tokens=1024` → New default `8192`
- Existing `.env` files without new vars will use sensible defaults
- All existing code paths work unchanged; adaptive chunking activates when `source_lang`/`target_lang` are provided

---

## Testing Your Configuration

```bash
# Run unit tests
pytest tests/infrastructure/llm/test_token_chunk_calculator.py -v

# Run integration tests
pytest tests/integration/test_token_chunking_e2e.py -v

# Manual verification
python -c "
from pdftranslator.infrastructure.llm.token_chunk_calculator import TokenChunkCalculator
from pdftranslator.infrastructure.llm.nvidia import NvidiaLLM
# ... test your specific config
"
```