"""Shared translation orchestration with progress callbacks."""

import logging
from dataclasses import dataclass
from typing import Callable, Optional

from pdftranslator.core.models.work import Chapter, GlossaryEntry, Volume
from pdftranslator.database.repositories.chapter_repository import ChapterRepository
from pdftranslator.database.repositories.glossary_repository import GlossaryRepository
from pdftranslator.database.repositories.translation_job_repository import (
    TranslationJob,
    TranslationJobRepository,
)
from pdftranslator.database.repositories.volume_repository import VolumeRepository

logger = logging.getLogger(__name__)


@dataclass
class TranslationProgress:
    completed_chapters: int = 0
    total_chapters: int = 0
    current_chapter: Optional[str] = None
    chapter_id: Optional[int] = None
    chapter_title: Optional[str] = None
    chapter_status: Optional[str] = None


def _get_chapter_sort_key(chapter: Chapter) -> tuple:
    title_lower = (chapter.title or "").lower()
    if chapter.chapter_number is None:
        if "prologue" in title_lower:
            return (0, 0)
        elif "epilogue" in title_lower:
            return (2, 0)
        else:
            return (1, 0)
    else:
        return (1, chapter.chapter_number)


def _format_chapter_display(chapter: Chapter) -> str:
    if chapter.chapter_number is None:
        return chapter.title or "Unknown"
    else:
        title_part = f" - {chapter.title}" if chapter.title else ""
        return f"Chapter {chapter.chapter_number}{title_part}"


class TranslationOrchestrator:
    def __init__(
        self,
        chapter_repo: ChapterRepository,
        glossary_repo: GlossaryRepository,
        volume_repo: Optional[VolumeRepository] = None,
        job_repo: Optional[TranslationJobRepository] = None,
    ):
        self._chapter_repo = chapter_repo
        self._glossary_repo = glossary_repo
        self._volume_repo = volume_repo
        self._job_repo = job_repo
        self._glossary_entries: list[GlossaryEntry] = []
        self._translator = None

    def _load_glossary(self, work_id: int) -> list[GlossaryEntry]:
        self._glossary_entries = self._glossary_repo.get_by_work(work_id)
        if self._glossary_entries:
            logger.info(
                f"Loaded {len(self._glossary_entries)} glossary entries for work {work_id}"
            )
        else:
            logger.warning(f"No glossary entries found for work {work_id}")
        return self._glossary_entries

    def _get_translator(self):
        if self._translator is None:
            from pdftranslator.cli.commands.translate_chapter import GlossaryAwareTranslator

            self._translator = GlossaryAwareTranslator(
                glossary_entries=self._glossary_entries,
            )
        return self._translator

    def translate_chapter(
        self,
        chapter_id: int,
        source_lang: str,
        target_lang: str,
        on_progress: Optional[Callable[[TranslationProgress], None]] = None,
    ) -> bool:
        chapter = self._chapter_repo.get_by_id(chapter_id)
        if chapter is None:
            logger.error(f"Chapter {chapter_id} not found")
            return False

        if not chapter.original_text:
            logger.warning(f"Chapter {chapter_id} has no original text, skipping")
            return False

        if not chapter.id:
            logger.error("Chapter has no ID")
            return False

        ch_display = _format_chapter_display(chapter)

        if on_progress:
            on_progress(TranslationProgress(
                current_chapter=ch_display,
                chapter_id=chapter.id,
                chapter_title=ch_display,
            ))

        try:
            translator = self._get_translator()
            translated_text = translator.translate_text(
                chapter.original_text, source_lang, target_lang
            )

            if translated_text:
                chapter.translated_text = translated_text
                self._chapter_repo.update(chapter)
                if on_progress:
                    on_progress(TranslationProgress(
                        current_chapter=ch_display,
                        chapter_id=chapter.id,
                        chapter_title=ch_display,
                        chapter_status="success",
                    ))
                return True
            else:
                logger.error(f"Empty translation for chapter {chapter_id}")
                if on_progress:
                    on_progress(TranslationProgress(
                        current_chapter=ch_display,
                        chapter_id=chapter.id,
                        chapter_title=ch_display,
                        chapter_status="failure",
                    ))
                return False

        except Exception as e:
            logger.error(f"Error translating chapter {chapter_id}: {e}")
            if on_progress:
                on_progress(TranslationProgress(
                    current_chapter=ch_display,
                    chapter_id=chapter.id,
                    chapter_title=ch_display,
                    chapter_status="failure",
                ))
            return False

    def translate_volume(
        self,
        volume_id: int,
        source_lang: str,
        target_lang: str,
        skip_translated: bool = True,
        on_progress: Optional[Callable[[TranslationProgress], None]] = None,
    ) -> tuple[int, int]:
        chapters = self._chapter_repo.get_by_volume(volume_id)
        if not chapters:
            logger.warning(f"No chapters found for volume {volume_id}")
            return (0, 0)

        total = len(chapters)
        success = 0
        failure = 0
        skipped = 0

        for i, chapter in enumerate(sorted(chapters, key=_get_chapter_sort_key)):
            ch_display = _format_chapter_display(chapter)

            if skip_translated and chapter.translated_text:
                logger.info(f"Skipping already translated: {ch_display}")
                skipped += 1
                if on_progress:
                    on_progress(TranslationProgress(
                        completed_chapters=i + 1,
                        total_chapters=total,
                        current_chapter=f"{ch_display} (skipped)",
                        chapter_id=chapter.id,
                        chapter_title=ch_display,
                        chapter_status="skipped",
                    ))
                continue

            def make_progress_callback(idx, tot, outer_cb):
                def callback(p):
                    augmented = TranslationProgress(
                        completed_chapters=idx + 1,
                        total_chapters=tot,
                        current_chapter=p.current_chapter,
                        chapter_id=p.chapter_id,
                        chapter_title=p.chapter_title,
                        chapter_status=p.chapter_status,
                    )
                    if outer_cb:
                        outer_cb(augmented)
                return callback

            result = self.translate_chapter(
                chapter_id=chapter.id,
                source_lang=source_lang,
                target_lang=target_lang,
                on_progress=make_progress_callback(i, total, on_progress),
            )

            if result:
                success += 1
            else:
                failure += 1

        logger.info(
            f"Volume {volume_id}: success={success}, failure={failure}, skipped={skipped}"
        )
        return (success, failure)

    def translate_book(
        self,
        work_id: int,
        source_lang: str,
        target_lang: str,
        skip_translated: bool = True,
        on_progress: Optional[Callable[[TranslationProgress], None]] = None,
    ) -> tuple[int, int]:
        if self._volume_repo is None:
            logger.error("VolumeRepository not provided")
            return (0, 0)

        volumes = self._volume_repo.get_by_work_id(work_id)
        if not volumes:
            logger.warning(f"No volumes found for work {work_id}")
            return (0, 0)

        total_success = 0
        total_failure = 0

        for volume in sorted(volumes, key=lambda v: v.volume_number):
            logger.info(f"Processing Volume {volume.volume_number}")

            success, failure = self.translate_volume(
                volume_id=volume.id,
                source_lang=source_lang,
                target_lang=target_lang,
                skip_translated=skip_translated,
                on_progress=on_progress,
            )

            total_success += success
            total_failure += failure

        return (total_success, total_failure)

    def execute_job(self, job: TranslationJob) -> None:
        if self._job_repo is None:
            logger.error("TranslationJobRepository not provided")
            return

        self._load_glossary(job.work_id)

        job.status = "in_progress"
        self._job_repo.update(job)

        def on_progress(progress: TranslationProgress) -> None:
            job.current_chapter_info = progress.current_chapter
            if progress.chapter_status == "success":
                job.success_count += 1
                job.completed_chapters += 1
            elif progress.chapter_status == "failure":
                job.failure_count += 1
                job.completed_chapters += 1
            elif progress.chapter_status == "skipped":
                job.completed_chapters += 1
            self._job_repo.update(job)

        try:
            if job.scope == "all_book":
                if self._volume_repo is None:
                    raise ValueError("VolumeRepository required for all_book scope")
                chapters_count = self._count_book_chapters(job.work_id)
                job.total_chapters = chapters_count
                self._job_repo.update(job)

                success, failure = self.translate_book(
                    work_id=job.work_id,
                    source_lang=job.source_lang,
                    target_lang=job.target_lang,
                    skip_translated=job.skip_translated,
                    on_progress=on_progress,
                )
                job.success_count = success
                job.failure_count = failure

            elif job.scope == "all_volume":
                if job.volume_id is None:
                    raise ValueError("volume_id required for all_volume scope")
                chapters = self._chapter_repo.get_by_volume(job.volume_id)
                job.total_chapters = len(chapters)
                self._job_repo.update(job)

                success, failure = self.translate_volume(
                    volume_id=job.volume_id,
                    source_lang=job.source_lang,
                    target_lang=job.target_lang,
                    skip_translated=job.skip_translated,
                    on_progress=on_progress,
                )
                job.success_count = success
                job.failure_count = failure

            elif job.scope == "single_chapter":
                if job.chapter_id is None:
                    raise ValueError("chapter_id required for single_chapter scope")
                job.total_chapters = 1
                self._job_repo.update(job)

                result = self.translate_chapter(
                    chapter_id=job.chapter_id,
                    source_lang=job.source_lang,
                    target_lang=job.target_lang,
                    on_progress=on_progress,
                )
                job.success_count = 1 if result else 0
                job.failure_count = 0 if result else 1

            job.status = "completed"
            job.current_chapter_info = None

        except Exception as e:
            logger.error(f"Translation job {job.id} failed: {e}")
            job.status = "error"
            job.error_message = str(e)

        self._job_repo.update(job)

    def _count_book_chapters(self, work_id: int) -> int:
        if self._volume_repo is None:
            return 0
        volumes = self._volume_repo.get_by_work_id(work_id)
        total = 0
        for v in volumes:
            chapters = self._chapter_repo.get_by_volume(v.id)
            total += len(chapters)
        return total
