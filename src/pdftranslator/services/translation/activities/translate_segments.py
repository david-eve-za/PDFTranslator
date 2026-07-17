"""
Translation Activities - LLM Translation Stage.

CUPID Principle: Unix Philosophy - Each activity does one thing well.
"""
import time
from dataclasses import dataclass

from temporalio import activity


@dataclass
class TranslateSegmentsInput:
    """Input for translate segments activity."""
    job_id: int
    segments: list[dict]
    source_lang: str
    target_lang: str
    llm_provider: str
    model_name: str
    temperature: float = 0.3
    max_tokens: int = 4000


@dataclass
class TranslateSegmentsOutput:
    """Output for translate segments activity."""
    translated_count: int
    failed_count: int
    errors: list[str]
    duration_ms: int
    segments: list[dict]  # Return updated segments


async def _translate_segment(
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

    In production, this calls the LLM infrastructure.
    For now, returns placeholder translation.
    """
    # Placeholder - real implementation would call LLM infrastructure
    # Example: await self._llm_client.translate(...)
    return f"[{target_lang}] {source_text}"


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
    updated_segments = []

    for segment in input_data.segments:
        try:
            if not segment.get("source_text"):
                continue

            source_text = segment["source_text"]

            translated_text = await _translate_segment(
                source_text=source_text,
                source_lang=input_data.source_lang,
                target_lang=input_data.target_lang,
                llm_provider=input_data.llm_provider,
                model_name=input_data.model_name,
                temperature=input_data.temperature,
                max_tokens=input_data.max_tokens,
            )

            # Update segment with translation
            segment["target_text"] = translated_text
            segment["translated"] = True
            translated_count += 1

        except Exception as e:
            failed_count += 1
            errors.append(f"Segment {segment.get('segment_number', '?')}: {str(e)}")

        updated_segments.append(segment)

    duration_ms = int((time.time() - start_time) * 1000)

    return TranslateSegmentsOutput(
        translated_count=translated_count,
        failed_count=failed_count,
        errors=errors,
        duration_ms=duration_ms,
        segments=updated_segments,
    )
