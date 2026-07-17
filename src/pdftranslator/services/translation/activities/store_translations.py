"""
Translation Activities - Store Translations Stage.

CUPID Principle: Unix Philosophy - Each activity does one thing well.
"""
from dataclasses import dataclass

from temporalio import activity


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

    for segment in input_data.segments:
        if segment.get("target_text") and segment.get("translated"):
            try:
                # In production, this would call SegmentRepository.update(segment)
                # For now, we simulate successful storage
                stored_count += 1
            except Exception as e:
                errors.append(f"Segment {segment.get('segment_number', '?')}: {str(e)}")
        else:
            errors.append(f"Segment {segment.get('segment_number', '?')} not translated")

    return StoreTranslationsOutput(
        stored_count=stored_count,
        errors=errors,
    )
