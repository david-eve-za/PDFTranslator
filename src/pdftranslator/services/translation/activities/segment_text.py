"""
Translation Activities - Text Segmentation Stage.

CUPID Principle: Unix Philosophy - Each activity does one thing well.
"""
import re
from dataclasses import dataclass

from temporalio import activity


@dataclass
class SegmentTextInput:
    """Input for segment text activity."""
    text: str
    source_lang: str
    target_lang: str
    job_id: int
    max_segment_length: int = 2000
    split_by_sentences: bool = True


@dataclass
class SegmentTextOutput:
    """Output for segment text activity."""
    segments: list[dict]
    total_segments: int
    total_chars: int


def _split_sentences(text: str) -> list[str]:
    """Simple sentence splitting (matches TranslationService._split_sentences)."""
    # Split on common sentence endings followed by space and capital letter
    pattern = r'(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚÑ])'
    sentences = re.split(pattern, text)
    return [s.strip() for s in sentences if s.strip()]


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

        # Check if adding this sentence exceeds max length
        if current_segment and len(current_segment) + len(sentence) + 1 > input_data.max_segment_length:
            # Save current segment
            if current_segment.strip():
                segments.append({
                    "job_id": input_data.job_id,
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

    # Don't forget the last segment
    if current_segment.strip():
        segments.append({
            "job_id": input_data.job_id,
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
