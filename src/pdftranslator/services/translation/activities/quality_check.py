"""
Translation Activities - Quality Check Stage.

CUPID Principle: Unix Philosophy - Each activity does one thing well.
"""
from dataclasses import dataclass

from temporalio import activity


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


async def _run_quality_check(
    segment: dict,
    check_type: str,
    source_lang: str,
    target_lang: str,
    threshold: float,
) -> tuple[bool, str]:
    """Run a single quality check on a segment."""
    source = segment.get("source_text", "") or ""
    target = segment.get("target_text", "") or ""

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
        checked_count += 1
        segment_passed = True

        for check_type in input_data.check_types:
            passed, message = await _run_quality_check(
                segment, check_type, input_data.source_lang, input_data.target_lang, input_data.threshold
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
