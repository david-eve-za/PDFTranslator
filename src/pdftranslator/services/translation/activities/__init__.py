"""
Translation Activities for Temporal Workflows.

CUPID Principle: Unix Philosophy - Each activity does one thing well.
CUPID Principle: Predictable - Deterministic activities with explicit inputs/outputs.
"""

from pdftranslator.services.translation.activities.detect_language import (
    DetectLanguageInput,
    DetectLanguageOutput,
    detect_language_activity,
)
from pdftranslator.services.translation.activities.generate_audio import (
    GenerateAudioInput,
    GenerateAudioOutput,
    generate_audio_activity,
    generate_audio_activity_wrapper,
)
from pdftranslator.services.translation.activities.publish_events import (
    PublishEventInput,
    PublishEventOutput,
    publish_event_activity,
    publish_job_started_activity,
    publish_job_completed_activity,
    publish_job_failed_activity,
    publish_step_completed_activity,
    publish_audiobook_generated_activity,
    shutdown_publisher,
)
from pdftranslator.services.translation.activities.quality_check import (
    QualityCheckInput,
    QualityCheckOutput,
    quality_check_activity,
)
from pdftranslator.services.translation.activities.segment_text import (
    SegmentTextInput,
    SegmentTextOutput,
    segment_text_activity,
)
from pdftranslator.services.translation.activities.store_translations import (
    StoreTranslationsInput,
    StoreTranslationsOutput,
    store_translations_activity,
)
from pdftranslator.services.translation.activities.translate_segments import (
    TranslateSegmentsInput,
    TranslateSegmentsOutput,
    translate_segments_activity,
)

__all__ = [
    # Detect Language
    "detect_language_activity",
    "DetectLanguageInput",
    "DetectLanguageOutput",
    # Segment Text
    "segment_text_activity",
    "SegmentTextInput",
    "SegmentTextOutput",
    # Translate Segments
    "translate_segments_activity",
    "TranslateSegmentsInput",
    "TranslateSegmentsOutput",
    # Quality Check
    "quality_check_activity",
    "QualityCheckInput",
    "QualityCheckOutput",
    # Store Translations
    "store_translations_activity",
    "StoreTranslationsInput",
    "StoreTranslationsOutput",
    # Generate Audio
    "generate_audio_activity",
    "generate_audio_activity_wrapper",
    "GenerateAudioInput",
    "GenerateAudioOutput",
    # Event Publishing
    "publish_event_activity",
    "PublishEventInput",
    "PublishEventOutput",
    "publish_job_started_activity",
    "publish_job_completed_activity",
    "publish_job_failed_activity",
    "publish_step_completed_activity",
    "publish_audiobook_generated_activity",
    "shutdown_publisher",
]