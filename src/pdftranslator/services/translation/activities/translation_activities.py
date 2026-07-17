"""
Translation Activities for Temporal Workflows.

CUPID Principle: Unix Philosophy - Each activity does one thing well.
CUPID Principle: Predictable - Deterministic activities with explicit inputs/outputs.
"""

import re
import time
from dataclasses import dataclass

from temporalio import activity


@dataclass
class DetectLanguageInput:
    """Input for detect language activity."""
    text: str
    job_id: int
    work_id: int


@dataclass
class DetectLanguageOutput:
    """Output for detect language activity."""
    detected_lang: str
    confidence: float
    text_stats: dict


@activity.defn
async def detect_language_activity(input_data: DetectLanguageInput) -> DetectLanguageOutput:
    """
    Stage 1: Detect source language and analyze text properties.

    CUPID: Composable - Pure function with explicit input/output.
    CUPID: Unix Philosophy - Single responsibility: language detection.
    """
    text = input_data.text.strip()
    char_count = len(text)
    word_count = len(text.split())
    line_count = text.count('\n') + 1

    # Simple heuristic detection (production would use langdetect or similar)
    detected_lang = _detect_language_heuristic(text)
    confidence = 0.85

    return DetectLanguageOutput(
        detected_lang=detected_lang,
        confidence=confidence,
        text_stats={
            "char_count": char_count,
            "word_count": word_count,
            "line_count": line_count,
            "avg_word_length": char_count / word_count if word_count > 0 else 0,
        }
    )


def _detect_language_heuristic(text: str) -> str:
    """Simple language detection heuristic (matches TranslationService._detect_language_heuristic)."""
    spanish_words = {
        'el', 'la', 'de', 'que', 'y', 'en', 'un', 'es', 'se', 'no', 'te', 'lo', 'le',
        'da', 'su', 'por', 'son', 'con', 'para', 'al', 'del', 'los', 'las', 'una',
        'como', 'mas', 'pero', 'sus', 'ya', 'o', 'este', 'si', 'porque', 'esta',
        'entre', 'cuando', 'muy', 'sin', 'sobre', 'tambien', 'me', 'hasta', 'hay',
        'donde', 'han', 'quien', 'estan', 'estado', 'desde', 'todo', 'nos', 'durante',
        'todos', 'uno', 'les', 'ni', 'contra', 'otros', 'ese', 'eso', 'ante', 'ellos',
        'e', 'esto', 'mi', 'antes', 'algunos', 'unos', 'yo', 'otro', 'otras',
        'otra', 'tanto', 'esa', 'estos', 'mucho', 'quienes', 'nada', 'muchos',
        'cual', 'poco', 'ella', 'estar', 'estas', 'algunas', 'algo', 'nosotros',
        'mis', 'tu', 'ti', 'tus', 'ellas', 'nosotras', 'vosotros', 'vosotras', 'os',
        'mio', 'mia', 'mios', 'mias', 'tuyo', 'tuya', 'tuyos', 'tuyas', 'suyo',
        'suya', 'suyos', 'suyas', 'nuestro', 'nuestra', 'nuestros', 'nuestras',
        'vuestro', 'vuestra', 'vuestros', 'vuestras'
    }
    english_words = {
        'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have', 'i', 'it', 'for',
        'not', 'on', 'with', 'he', 'as', 'you', 'do', 'at', 'this', 'but', 'his', 'by',
        'from', 'they', 'we', 'say', 'her', 'she', 'or', 'an', 'will', 'my', 'one',
        'all', 'would', 'there', 'their', 'what', 'so', 'up', 'out', 'if', 'about',
        'who', 'get', 'which', 'go', 'me'
    }
    words = text.lower().split()
    spanish_count = sum(1 for w in words if w in spanish_words)
    english_count = sum(1 for w in words if w in english_words)

    if spanish_count > len(words) * 0.15:
        return "es"
    if english_count > len(words) * 0.15:
        return "en"
    return "en"


@dataclass
class SegmentTextInput:
    """Input for segment text activity."""
    text: str
    job_id: int
    max_segment_length: int = 5000
    split_by_sentences: bool = True


@dataclass
class SegmentTextOutput:
    """Output for segment text activity."""
    segments: list[dict]
    total_segments: int
    total_chars: int


@activity.defn
async def segment_text_activity(input_data: SegmentTextInput) -> SegmentTextOutput:
    """
    Stage 2: Segment text into translation units.

    CUPID: Composable - Pure function with explicit input/output.
    CUPID: Unix Philosophy - Single responsibility: text segmentation.
    """
    text = input_data.text.strip()
    segments = []

    sentences = _split_sentences(text) if input_data.split_by_sentences else [text]

    segment_number = 1
    current_segment = ""

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        if current_segment and len(current_segment) + len(sentence) + 1 > input_data.max_segment_length:
            if current_segment.strip():
                segments.append({
                    "segment_number": segment_number,
                    "source_text": current_segment.strip(),
                    "target_text": None,
                })
                segment_number += 1
            current_segment = sentence
        else:
            if current_segment:
                current_segment += " " + sentence
            else:
                current_segment = sentence

    if current_segment.strip():
        segments.append({
            "segment_number": segment_number,
            "source_text": current_segment.strip(),
            "target_text": None,
        })

    total_chars = sum(len(s["source_text"] or "") for s in segments)

    return SegmentTextOutput(
        segments=segments,
        total_segments=len(segments),
        total_chars=total_chars,
    )


def _split_sentences(text: str) -> list[str]:
    """Simple sentence splitting (matches TranslationService._split_sentences)."""
    pattern = r'(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚÑ])'
    sentences = re.split(pattern, text)
    return [s.strip() for s in sentences if s.strip()]


@dataclass
class TranslateSegmentsInput:
    """Input for translate segments activity."""
    segments: list[dict]
    source_lang: str
    target_lang: str
    llm_provider: str
    model_name: str
    temperature: float
    max_tokens: int


@dataclass
class TranslateSegmentsOutput:
    """Output for translate segments activity."""
    translated_segments: list[dict]
    translated_count: int
    failed_count: int
    errors: list[str]
    duration_ms: int


@activity.defn
async def translate_segments_activity(input_data: TranslateSegmentsInput) -> TranslateSegmentsOutput:
    """
    Stage 3: Translate segments using LLM.

    CUPID: Composable - Pure function with explicit input/output.
    CUPID: Unix Philosophy - Single responsibility: LLM translation.
    """
    start_time = time.time()
    translated_count = 0
    failed_count = 0
    errors = []
    translated_segments = []

    for segment in input_data.segments:
        source_text = segment.get("source_text", "")
        if not source_text:
            failed_count += 1
            errors.append(f"Segment {segment.get('segment_number', '?')}: empty source text")
            translated_segments.append({**segment, "target_text": None, "error": "empty source"})
            continue

        try:
            # In production, call actual LLM infrastructure
            # For now, return placeholder translation
            translated_text = await _translate_segment_via_llm(
                source_text=source_text,
                source_lang=input_data.source_lang,
                target_lang=input_data.target_lang,
                llm_provider=input_data.llm_provider,
                model_name=input_data.model_name,
                temperature=input_data.temperature,
                max_tokens=input_data.max_tokens,
            )

            translated_segments.append({
                **segment,
                "target_text": translated_text,
                "error": None,
            })
            translated_count += 1

        except Exception as e:
            failed_count += 1
            errors.append(f"Segment {segment.get('segment_number', '?')}: {str(e)}")
            translated_segments.append({**segment, "target_text": None, "error": str(e)})

    duration_ms = int((time.time() - start_time) * 1000)

    return TranslateSegmentsOutput(
        translated_segments=translated_segments,
        translated_count=translated_count,
        failed_count=failed_count,
        errors=errors,
        duration_ms=duration_ms,
    )


async def _translate_segment_via_llm(
    source_text: str,
    source_lang: str,
    target_lang: str,
    llm_provider: str,
    model_name: str,
    temperature: float,
    max_tokens: int,
) -> str:
    """
    Translate a single segment using LLM.

    This is a placeholder - real implementation would call LLM infrastructure.
    """
    # Placeholder - real implementation would call LLM service
    return f"[{target_lang}] {source_text}"


@dataclass
class QualityCheckInput:
    """Input for quality check activity."""
    segments: list[dict]
    source_lang: str
    target_lang: str
    check_types: list[str]
    threshold: float


@dataclass
class QualityCheckOutput:
    """Output for quality check activity."""
    checked_count: int
    passed_count: int
    failed_count: int
    issues: list[dict]
    overall_score: float


@activity.defn
async def quality_check_activity(input_data: QualityCheckInput) -> QualityCheckOutput:
    """
    Stage 4: Quality check translations.

    CUPID: Composable - Pure function with explicit input/output.
    CUPID: Unix Philosophy - Single responsibility: quality validation.
    """
    checked_count = 0
    passed_count = 0
    failed_count = 0
    issues = []

    for segment in input_data.segments:
        if not segment.get("target_text"):
            continue

        checked_count += 1
        segment_passed = True

        for check_type in input_data.check_types:
            passed, message = await _run_quality_check(
                segment, check_type, input_data.source_lang,
                input_data.target_lang, input_data.threshold
            )
            if not passed:
                segment_passed = False
                issues.append({
                    "segment_id": segment.get("segment_number"),
                    "segment_number": segment.get("segment_number"),
                    "check_type": check_type,
                    "severity": "error",
                    "message": message,
                })

        if segment_passed:
            passed_count += 1
        else:
            failed_count += 1

    overall_score = passed_count / checked_count if checked_count > 0 else 1.0

    return QualityCheckOutput(
        checked_count=checked_count,
        passed_count=passed_count,
        failed_count=failed_count,
        issues=issues,
        overall_score=overall_score,
    )


async def _run_quality_check(
    segment: dict,
    check_type: str,
    source_lang: str,
    target_lang: str,
    threshold: float,
) -> tuple[bool, str]:
    """Run a single quality check on a segment (matches TranslationService._run_quality_check)."""
    source = segment.get("source_text", "")
    target = segment.get("target_text", "")

    if check_type == "completeness":
        if not target or not target.strip():
            return False, "Translation is empty"
        ratio = len(target) / len(source) if source else 0
        if ratio < 0.1 or ratio > 10:
            return False, f"Length ratio {ratio:.2f} outside expected range"
        return True, ""

    elif check_type == "terminology":
        # Check for untranslated glossary terms (placeholder)
        return True, ""

    elif check_type == "fluency":
        words = target.split()
        if len(words) < 2:
            return False, "Translation too short"
        if len(set(words)) / len(words) < 0.3:
            return False, "Excessive word repetition detected"
        return True, ""

    elif check_type == "consistency":
        # Check consistent terminology within job (placeholder)
        return True, ""

    elif check_type == "formatting":
        # Check if formatting preserved (placeholder)
        return True, ""

    return True, ""


@dataclass
class StoreTranslationsInput:
    """Input for store translations activity."""
    job_id: int
    segments: list[dict]
    pipeline_id: str


@dataclass
class StoreTranslationsOutput:
    """Output for store translations activity."""
    stored_count: int
    errors: list[str]


@activity.defn
async def store_translations_activity(input_data: StoreTranslationsInput) -> StoreTranslationsOutput:
    """
    Stage 5: Store translated segments and update job status.

    CUPID: Composable - Pure function with explicit input/output.
    CUPID: Unix Philosophy - Single responsibility: persistence.
    """
    stored_count = 0
    errors = []

    # In real implementation, this would persist to database
    for segment in input_data.segments:
        if segment.get("target_text"):
            try:
                # Placeholder: actual persistence would happen here
                # await segment_repo.update(segment)
                stored_count += 1
            except Exception as e:
                errors.append(f"Segment {segment.get('segment_number')}: {str(e)}")
        else:
            errors.append(f"Segment {segment.get('segment_number')} not translated")

    return StoreTranslationsOutput(
        stored_count=stored_count,
        errors=errors,
    )


# Import and re-export generate_audio_activity
from pdftranslator.services.translation.activities.generate_audio import (
    GenerateAudioInput,
    GenerateAudioOutput,
    generate_audio_activity,
    generate_audio_activity_wrapper,
)

__all__ = [
    "detect_language_activity",
    "segment_text_activity",
    "translate_segments_activity",
    "quality_check_activity",
    "store_translations_activity",
    "generate_audio_activity",
    "generate_audio_activity_wrapper",
    "DetectLanguageInput",
    "DetectLanguageOutput",
    "SegmentTextInput",
    "SegmentTextOutput",
    "TranslateSegmentsInput",
    "TranslateSegmentsOutput",
    "QualityCheckInput",
    "QualityCheckOutput",
    "StoreTranslationsInput",
    "StoreTranslationsOutput",
    "GenerateAudioInput",
    "GenerateAudioOutput",
]
