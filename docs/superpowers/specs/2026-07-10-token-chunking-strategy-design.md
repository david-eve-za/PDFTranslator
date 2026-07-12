# Token Chunking Strategy for PDF Translation

## Spec Version
1.0.0

## Date
2026-07-10

## Author
David Gonzalez

## Status
Approved for Implementation

---

## 1. Problem Statement

The current PDF translation pipeline uses a severely conservative token chunking strategy:

- **Current config**: `max_output_tokens = 1,024` (NvidiaConfig default)
- **Model capacity**: `mistralai/mistral-large-3-675b-instruct-2512` supports 131,072 context window
- **Utilization**: Only **0.8%** of model output capacity is used
- **Impact**: Excessive chunking → more API calls → higher latency, cost, and fragmentation risk

The `NvidiaLLM.split_into_limit()` method currently uses `chunk_size = max_output_tokens` directly, ignoring:
- Actual prompt token count (~1,050 tokens for the translation template)
- Translation expansion ratios by language pair (EN→ES: ~1.3x, EN→ZH: ~0.6x)
- Safety margins to prevent response truncation

---

## 2. Solution Overview

Implement an **adaptive token chunking calculator** that computes optimal chunk size per translation request based on:

1. **Model limits** (context window, max output tokens)
2. **Measured prompt size** (runtime token count with formatted template)
3. **Language-pair expansion ratio** (configurable table with sensible defaults)
4. **Configurable safety margin** (default 15%)

### Formula

```python
def calculate_optimal_chunk_size(
    model_context: int,           # 131072
    prompt_tokens: int,           # ~1050 (measured)
    max_output_tokens: int,       # from config (default 8192)
    expansion_ratio: float,       # from language pair table
    safety_margin_pct: float = 0.15,
    min_chunk: int = 512,
    max_chunk: int = 32768,
) -> int:
    # Limit 1: Output budget / expansion ratio
    by_output = (max_output_tokens / expansion_ratio) * (1 - safety_margin_pct)
    
    # Limit 2: Available context - prompt - reserved output
    available_context = model_context - prompt_tokens - max_output_tokens
    by_context = available_context * (1 - safety_margin_pct)
    
    # Apply bounds
    chunk_size = int(min(by_output, by_context, max_chunk))
    return max(chunk_size, min_chunk)
```

### Expected Results (Mistral Large 3, max_output=8192)

| Language Pair | Expansion | Chunk Tokens | Approx. Pages/Chunk |
|--------------|-----------|--------------|---------------------|
| EN → ES/PT   | 1.30      | **5,357**    | ~15-20              |
| EN → FR/IT   | 1.15      | **6,054**    | ~18-22              |
| EN → DE      | 1.20      | **5,803**    | ~17-21              |
| EN → ZH/JA/KO| 0.60      | **11,605**   | ~35-45              |
| EN → AR/RU   | 1.15      | **6,054**    | ~18-22              |

**vs Current (1024)**: **5x-11x fewer chunks**, dramatically reducing API calls and latency.

---

## 3. Architecture

### New Components

```
src/pdftranslator/infrastructure/llm/
├── token_chunk_calculator.py      # NEW: Core calculation logic
├── nvidia.py                      # MODIFIED: split_into_limit() refactor
└── protocol.py                    # UNCHANGED: LLMClient interface
```

### Data Flow

```
TranslatorService.translate()
    │
    ▼
NvidiaLLM.split_into_limit(text, language)
    │
    ├── TokenChunkCalculator.measure_prompt_tokens(template, src_lang, tgt_lang)
    ├── TokenChunkCalculator.get_expansion_ratio(src_lang, tgt_lang)
    ├── TokenChunkCalculator.calculate_chunk_size(config, prompt_tokens, ratio)
    │
    ▼
NLTKTextSplitter(chunk_size=calculated, length_function=count_tokens)
    │
    ▼
List[str] chunks  ← Optimally sized for model + language pair
```

---

## 4. Configuration Changes

### NvidiaConfig (src/pdftranslator/core/config/llm.py)

```python
class NvidiaConfig(BaseModel):
    model_name: str = Field(
        default="mistralai/mistral-large-3-675b-instruct-2512"
    )
    max_output_tokens: int = Field(
        default=8192,                       # INCREASED from 1024
        ge=1024, le=131072,
        description="Max tokens reserved for model output per request"
    )
    context_size: int = Field(
        default=131072,
        frozen=True,
        description="Model context window (input + output)"
    )
    chunk_safety_margin_pct: float = Field(
        default=0.15,                       # 15% safety margin
        ge=0.05, le=0.30,
        description="Percentage margin to prevent truncation"
    )
    max_chunk_tokens: int = Field(
        default=32768,
        ge=512, le=65536,
        description="Practical upper bound per chunk"
    )
    min_chunk_tokens: int = Field(
        default=512,
        ge=128,
        description="Minimum viable chunk size"
    )
    # Optional per-language-pair overrides
    expansion_ratios: Dict[str, float] = Field(
        default_factory=dict,
        description="Custom ratios: 'en-es': 1.3, 'en-zh': 0.6, etc."
    )
```

### Default Expansion Ratios (in TokenChunkCalculator)

```python
DEFAULT_EXPANSION_RATIOS = {
    # Source-target pairs
    ("en", "es"): 1.30, ("en", "pt"): 1.25, ("en", "fr"): 1.15,
    ("en", "it"): 1.10, ("en", "de"): 1.20, ("en", "nl"): 1.15,
    ("en", "pl"): 1.20, ("en", "ru"): 1.15, ("en", "ar"): 1.15,
    ("en", "zh"): 0.55, ("en", "ja"): 0.60, ("en", "ko"): 0.65,
    ("en", "hi"): 1.10,
    # Reverse directions (approximate)
    ("es", "en"): 0.80, ("fr", "en"): 0.85, ("de", "en"): 0.85,
    ("zh", "en"): 1.80, ("ja", "en"): 1.70, ("ko", "en"): 1.60,
}
```

---

## 5. Implementation Details

### TokenChunkCalculator (New Class)

```python
class TokenChunkCalculator:
    """Calculates optimal chunk size for translation requests."""
    
    DEFAULT_EXPANSION_RATIOS: ClassVar[Dict[Tuple[str, str], float]] = {...}
    
    def __init__(
        self,
        llm_client: LLMClient,
        config: NvidiaConfig,
        custom_ratios: Optional[Dict[str, float]] = None,
    ):
        self._llm = llm_client
        self._config = config
        self._ratios = {**self.DEFAULT_EXPANSION_RATIOS, **(custom_ratios or {})}
    
    def measure_prompt_tokens(
        self,
        template: str,
        source_lang: str,
        target_lang: str,
        sample_text: str = "Sample text for measurement."
    ) -> int:
        """Measure actual tokens of formatted prompt template."""
        formatted = template.format(
            text_chunk=sample_text,
            source_lang=source_lang,
            target_lang=target_lang,
        )
        return self._llm.count_tokens(formatted)
    
    def get_expansion_ratio(self, source_lang: str, target_lang: str) -> float:
        """Get expansion ratio for language pair (fallback: 1.15)."""
        return self._ratios.get((source_lang, target_lang), 1.15)
    
    def calculate_chunk_size(
        self,
        prompt_tokens: int,
        expansion_ratio: float,
    ) -> int:
        """Apply the adaptive formula with config bounds."""
        # Formula as specified in Section 2
        ...
    
    def validate_response_not_truncated(self, response: str, max_output: int) -> bool:
        """Heuristic check for truncation (uses >95% of budget)."""
        response_tokens = self._llm.count_tokens(response)
        return response_tokens < max_output * 0.95
```

### Modified NvidiaLLM.split_into_limit()

```python
def split_into_limit(
    self,
    text: str,
    language: BCP47Language = BCP47Language.ENGLISH,
    source_lang: str = "en",      # NEW
    target_lang: str = "es",      # NEW
) -> list[str]:
    # Load prompt template
    template = self._load_prompt_template()
    
    # Calculate optimal chunk size
    calculator = TokenChunkCalculator(self, self._settings.llm.nvidia)
    prompt_tokens = calculator.measure_prompt_tokens(
        template, source_lang, target_lang
    )
    expansion = calculator.get_expansion_ratio(source_lang, target_lang)
    chunk_size = calculator.calculate_chunk_size(prompt_tokens, expansion)
    
    logger.info(
        f"Chunking: prompt={prompt_tokens} tokens, "
        f"expansion={expansion:.2f}, chunk_size={chunk_size} tokens"
    )
    
    # Use NLTKTextSplitter with calculated size
    splitter = NLTKTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=0,
        language=language.to_nltk_name(),
        length_function=self.count_tokens,
    )
    return splitter.split_text(text)
```

---

## 6. Testing Strategy

### Unit Tests (tests/infrastructure/llm/test_token_chunk_calculator.py)

| Test Case | Description |
|-----------|-------------|
| `test_calculate_chunk_size_en_es` | EN→ES: 8192 output → ~5,357 chunk |
| `test_calculate_chunk_size_en_zh` | EN→ZH: 8192 output → ~11,605 chunk |
| `test_respects_min_chunk` | Below min_chunk_tokens floors to 512 |
| `test_respects_max_chunk` | Above max_chunk_tokens caps to 32768 |
| `test_prompt_token_measurement` | Actual template formatting measured |
| `test_custom_expansion_ratios` | Config override works |
| `test_fallback_ratio_unknown_pair` | Unknown pair → 1.15 default |
| `test_validate_response_truncation` | >95% budget flags warning |

### Integration Tests

| Test | Description |
|------|-------------|
| `test_split_into_limit_returns_chunks` | Chunks produced, sizes within bounds |
| `test_chunk_sizes_vary_by_language` | EN→ES vs EN→ZH produce different counts |
| `test_no_truncation_in_real_call` | Mock response validation passes |

---

## 7. Rollout Plan

### Phase 1: Core Implementation (this PR)
- [ ] Create `TokenChunkCalculator` class
- [ ] Add config fields to `NvidiaConfig`
- [ ] Refactor `NvidiaLLM.split_into_limit()`
- [ ] Add unit tests

### Phase 2: Config Defaults
- [ ] Update default `max_output_tokens` from 1024 → 8192
- [ ] Document expansion ratio table
- [ ] Add environment variable overrides

### Phase 3: Observability
- [ ] Log chunk size calculations (INFO level)
- [ ] Log truncation warnings (WARN level)
- [ ] Metrics: chunks_per_translation, avg_chunk_tokens

### Phase 4: Validation
- [ ] End-to-end translation test with sample documents
- [ ] Compare chunk counts before/after
- [ ] Verify no truncation in production logs

---

## 8. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Response truncation | Low | High | 15% safety margin + validation heuristic |
| Expansion ratio inaccurate | Medium | Medium | Configurable override + conservative fallback (1.15) |
| Prompt template changes break measurement | Low | Medium | Measure on every split_into_limit call (cached) |
| NLTK splitter edge cases | Low | Low | Existing text splitter, well-tested |
| Config migration for existing users | Medium | Low | Sensible defaults, env var overrides |

---

## 9. Approval

- [x] Design reviewed
- [x] Approved for implementation
- [ ] Implementation complete
- [ ] Tests passing
- [ ] Deployed to staging