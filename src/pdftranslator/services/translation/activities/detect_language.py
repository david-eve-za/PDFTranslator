"""
Translation Activities - Language Detection Stage.

CUPID Principle: Unix Philosophy - Each activity does one thing well.
"""
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


def _detect_language_heuristic(text: str) -> str:
    """Simple language detection heuristic."""
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
