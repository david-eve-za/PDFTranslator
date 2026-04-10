# cli/commands/translate_chapter.py
"""
Comando interactivo para traducción de capítulos con integración de glosario.

Permite seleccionar libro, volumen y capítulo, y utiliza el glosario existente
para proporcionar contexto de traducción más preciso.
"""

import logging
import re
from typing import List, Optional

import questionary
import typer
from rich.panel import Panel
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
)
from rich.table import Table

from pdftranslator.cli.app import app, console, setup_logging
from pdftranslator.cli.services.glossary_post_processor import GlossaryPostProcessor
from pdftranslator.database.models import Work, Volume, Chapter, GlossaryEntry
from pdftranslator.database.repositories.book_repository import BookRepository
from pdftranslator.database.repositories.chapter_repository import ChapterRepository
from pdftranslator.database.repositories.volume_repository import VolumeRepository
from pdftranslator.database.repositories.glossary_repository import GlossaryRepository
from pdftranslator.infrastructure.llm.base import BCP47Language
from pdftranslator.tools.Translator import Translator
from pdftranslator.core.config.settings import Settings

logger = logging.getLogger(__name__)

# Scope constants
SCOPE_ALL_BOOK = "All Book"
SCOPE_ALL_VOLUME = "All Volume"
SCOPE_SINGLE_CHAPTER = "Single Chapter"


def _get_chapter_sort_key(chapter: Chapter) -> tuple:
    """
    Get a sort key for chapter ordering.

    Order: Prologue first, then numbered chapters, then Epilogue.

    Returns:
        Tuple for sorting: (order_type, number)
        - order_type: 0 for Prologue, 1 for numbered chapters, 2 for Epilogue
        - number: chapter number or position within type
    """
    if chapter.chapter_number is None:
        # Determine if it's a prologue or epilogue based on title
        title_lower = (chapter.title or "").lower()
        if "prologue" in title_lower:
            return (0, 0)  # Prologue - first
        elif "epilogue" in title_lower:
            return (2, 0)  # Epilogue - last
        else:
            return (1, 0)  # Unknown unnumbered - middle
    else:
        return (
            1,
            chapter.chapter_number,
        )  # Numbered chapters - middle, sorted by number


def _format_chapter_display(chapter: Chapter) -> str:
    """
    Format a chapter for display, handling prologues and epilogues.

    - Prologue/Epilogue: Show type as title (chapter_number is None)
    - Regular chapters: Show "Chapter {number}" with optional title

    Returns:
        Formatted string for display
    """
    if chapter.chapter_number is None:
        # This is a prologue or epilogue - use title as the type
        chapter_type = chapter.title or "Unknown"
        return f"{chapter_type}"
    else:
        # Regular numbered chapter
        title_part = f" - {chapter.title}" if chapter.title else ""
        return f"Chapter {chapter.chapter_number}{title_part}"


def _select_work_interactive(work_repo: BookRepository) -> Optional[Work]:
    """Interactive selection of a work from the database."""
    works = work_repo.find_all()
    if not works:
        console.print("[yellow]No works found in database.[/yellow]")
        return None

    work_choices = [questionary.Choice(title=w.title, value=w) for w in works]

    selected_work: Optional[Work] = questionary.select(
        "Select a work:",
        choices=work_choices,
    ).ask()

    return selected_work


def _display_work_structure(
    work: Work,
    volume_repo: VolumeRepository,
    chapter_repo: ChapterRepository,
) -> dict:
    """
    Display the structure of a work (volumes and chapters) with translation status.
    Returns a dict with volume and chapter counts.
    """
    if work.id is None:
        return {"volumes": 0, "chapters": 0, "translated": 0, "pending": 0}

    volumes = volume_repo.get_by_work_id(work.id)
    if not volumes:
        console.print(f"[yellow]No volumes found for '{work.title}'.[/yellow]")
        return {"volumes": 0, "chapters": 0, "translated": 0, "pending": 0}

    total_chapters = 0
    total_translated = 0
    total_pending = 0

    console.print(f"\n[bold]📚 {work.title}[/bold]\n")

    for volume in sorted(volumes, key=lambda v: v.volume_number):
        chapters = chapter_repo.get_by_volume(volume.id) if volume.id else []
        translated = sum(1 for ch in chapters if ch.translated_text)
        pending = len(chapters) - translated

        total_chapters += len(chapters)
        total_translated += translated
        total_pending += pending

        vol_title = f" - {volume.title}" if volume.title else ""
        status = ""
        if translated == len(chapters) and len(chapters) > 0:
            status = "[green] ✓[/green]"
        elif translated > 0:
            status = f"[yellow] ({translated}/{len(chapters)} translated)[/yellow]"
        elif len(chapters) > 0:
            status = "[dim] (pending)[/dim]"

        console.print(
            f"  [cyan]Volume {volume.volume_number}{vol_title}[/cyan]{status}"
        )

        # Show chapter status for this volume
        for ch in sorted(chapters, key=_get_chapter_sort_key)[:5]:
            ch_status = "[green]✓[/green]" if ch.translated_text else "[dim]○[/dim]"
            ch_display = _format_chapter_display(ch)
            console.print(f"    {ch_status} {ch_display}")

        if len(chapters) > 5:
            console.print(f"    [dim]... and {len(chapters) - 5} more chapters[/dim]")

    console.print(
        f"\n[dim]Total: {len(volumes)} volumes, {total_chapters} chapters[/dim]"
    )
    console.print(
        f"[dim]    [green]{total_translated} translated[/green], {total_pending} pending[/dim]\n"
    )

    return {
        "volumes": len(volumes),
        "chapters": total_chapters,
        "translated": total_translated,
        "pending": total_pending,
    }


def _select_scope_with_context(
    work: Work,
    volume_repo: VolumeRepository,
    chapter_repo: ChapterRepository,
) -> Optional[str]:
    """
    Interactive selection of processing scope with context about the work.
    Shows the work structure before asking for scope.
    """
    stats = _display_work_structure(work, volume_repo, chapter_repo)

    if stats["chapters"] == 0:
        console.print("[yellow]No chapters available to translate.[/yellow]")
        return None

    # Build dynamic choices based on available content
    choices = []

    # All Book option (if more than one volume or all pending)
    if stats["volumes"] > 1 or stats["pending"] > 0:
        pending_desc = f" ({stats['pending']} pending)" if stats["pending"] > 0 else ""
        choices.append(
            questionary.Choice(
                title=f"All Book - Translate all volumes and chapters{pending_desc}",
                value=SCOPE_ALL_BOOK,
            )
        )

    # All Volume option
    if stats["volumes"] >= 1:
        choices.append(
            questionary.Choice(
                title="All Volume - Select a volume to translate entirely",
                value=SCOPE_ALL_VOLUME,
            )
        )

    # Single Chapter option
    if stats["chapters"] >= 1:
        choices.append(
            questionary.Choice(
                title="Single Chapter - Select a specific chapter",
                value=SCOPE_SINGLE_CHAPTER,
            )
        )

    return questionary.select(
        "Select translation scope:",
        choices=choices,
    ).ask()


def _select_scope() -> Optional[str]:
    """Interactive selection of processing scope."""
    return questionary.select(
        "Select translation scope:",
        choices=[
            questionary.Choice(
                title="All Book (translate all volumes and chapters)",
                value=SCOPE_ALL_BOOK,
            ),
            questionary.Choice(
                title="All Volume (translate all chapters of a volume)",
                value=SCOPE_ALL_VOLUME,
            ),
            questionary.Choice(
                title="Single Chapter",
                value=SCOPE_SINGLE_CHAPTER,
            ),
        ],
    ).ask()


def _select_volume_interactive(
    work: Work, volume_repo: VolumeRepository
) -> Optional[Volume]:
    """Interactive selection of a volume from a work."""
    if work.id is None:
        console.print("[red]Work has no ID.[/red]")
        return None
    volumes = volume_repo.get_by_work_id(work.id)
    if not volumes:
        console.print(f"[yellow]No volumes found for '{work.title}'.[/yellow]")
        return None

    volume_choices = [
        questionary.Choice(
            title=f"Volume {v.volume_number}" + (f" - {v.title}" if v.title else ""),
            value=v,
        )
        for v in sorted(volumes, key=lambda vol: vol.volume_number)
    ]

    selected_volume: Optional[Volume] = questionary.select(
        f"Select a volume from '{work.title}':",
        choices=volume_choices,
    ).ask()

    return selected_volume


def _select_chapter_interactive(
    volume: Volume, chapter_repo: ChapterRepository, show_status: bool = True
) -> Optional[Chapter]:
    """Interactive selection of a chapter from a volume."""
    if volume.id is None:
        console.print("[red]Volume has no ID.[/red]")
        return None
    chapters = chapter_repo.get_by_volume(volume.id)
    if not chapters:
        console.print(
            f"[yellow]No chapters found for Volume {volume.volume_number}.[/yellow]"
        )
        return None

    chapter_choices = []
    for ch in sorted(chapters, key=_get_chapter_sort_key):
        status = ""
        if show_status:
            if ch.translated_text:
                status = " [green](✓ translated)[/green]"
            else:
                status = " [dim](○ pending)[/dim]"

        ch_display = _format_chapter_display(ch)
        display = f"{ch_display}{status}"
        chapter_choices.append(questionary.Choice(title=display, value=ch))

    selected_chapter: Optional[Chapter] = questionary.select(
        f"Select a chapter from Volume {volume.volume_number}:",
        choices=chapter_choices,
    ).ask()

    return selected_chapter


class GlossaryAwareTranslator(Translator):
    """
    Translator with glossary consistency through post-processing.

    Instead of injecting glossary terms into the translation prompt,
    this translator applies glossary validation and correction after
    translation, ensuring 100% consistency of terms.

    Benefits:
    - Larger chunks (no glossary overhead in prompt)
    - Guaranteed consistency through post-processing
    - Fewer API calls for same text
    """

    def __init__(
        self,
        glossary_entries: List[GlossaryEntry],
        progress=None,
    ):
        """
        Initialize with glossary entries for context-aware translation.

        Args:
            glossary_entries: List of glossary terms for post-processing
            progress: Optional progress tracker
        """
        super().__init__(progress=progress)
        self.glossary_entries = glossary_entries
        self._post_processor = None

    def _get_translation_prompt_template(
        self, source_lang: str, target_lang: str
    ) -> str:
        """
        Get the standard translation prompt template.

        Note: Glossary is no longer included in prompt.
        Use GlossaryPostProcessor for term consistency.

        Returns:
            The translation prompt template.
        """
        with open(
            self._settings.paths.translation_prompt_path, "r", encoding="utf-8"
        ) as f:
            return f.read()

    def _get_language_for_split(self, source_lang: str) -> BCP47Language:
        """Map source language to BCP47Language enum."""
        lang_map = {
            "en": BCP47Language.ENGLISH,
            "es": BCP47Language.SPANISH,
            "zh": BCP47Language.CHINESE,
            "ja": BCP47Language.JAPANESE,
            "ko": BCP47Language.KOREAN,
            "fr": BCP47Language.FRENCH,
            "de": BCP47Language.GERMAN,
            "it": BCP47Language.ITALIAN,
            "pt": BCP47Language.PORTUGUESE,
            "ru": BCP47Language.RUSSIAN,
            "ar": BCP47Language.ARABIC,
            "hi": BCP47Language.HINDI,
        }
        return lang_map.get(source_lang.lower(), BCP47Language.ENGLISH)

    def translate_text(self, full_text: str, source_lang: str, target_lang: str) -> str:
        """
        Translate text with post-processing for glossary consistency.

        Args:
            full_text: Text to translate
            source_lang: Source language code
            target_lang: Target language code

        Returns:
            Translated text with glossary terms consistently applied
        """
        split_lang = self._get_language_for_split(source_lang)
        chunks = self.llm_client.split_into_limit(full_text, language=split_lang)

        logger.info(f"Text split into {len(chunks)} chunks for translation.")

        if not chunks:
            logger.warning("No chunks to translate.")
            return ""

        translated_parts = self._translate_chunks(chunks, source_lang, target_lang)

        logger.info("Translation of all chunks completed.")

        full_translated_text = "\n\n".join(translated_parts)
        full_translated_text = re.sub(r"\n{3,}", "\n\n", full_translated_text).strip()

        if self.glossary_entries:
            logger.info(
                f"Applying glossary post-processing ({len(self.glossary_entries)} entries)"
            )
            self._post_processor = GlossaryPostProcessor(
                self.glossary_entries, target_lang
            )
            full_translated_text = self._post_processor.process(full_translated_text)
            logger.info("Glossary post-processing completed")

        return full_translated_text

    def _translate_single_chunk(
        self, chunk: str, chunk_index: int, base_prompt_template: str
    ) -> str:
        """
        Translate a single chunk (no glossary in prompt).

        Args:
            chunk: Text chunk to translate
            chunk_index: Index of the chunk (for logging)
            base_prompt_template: Prompt template to use

        Returns:
            Translated chunk or error marker
        """
        prompt = base_prompt_template.format(
            text_chunk=chunk,
            source_lang=self._current_source_lang,
            target_lang=self._current_target_lang,
        )

        prompt_tokens = self.llm_client.count_tokens(prompt)
        logger.debug(f"Chunk {chunk_index + 1}: Prompt total = {prompt_tokens} tokens")

        try:
            translated_chunk = self.llm_client.call_model(prompt)
            return translated_chunk if translated_chunk is not None else ""
        except Exception as e:
            logger.error(f"Error during LLM call for chunk {chunk_index + 1}: {e}")
            return self._ERROR_CHUNK_MARKER_FORMAT.format(index=chunk_index + 1)

    def _translate_chunks(
        self, chunks: list[str], source_lang: str, target_lang: str
    ) -> list[str]:
        """Translate all chunks with progress tracking."""
        self._current_source_lang = source_lang
        self._current_target_lang = target_lang

        translated_chunks = []
        prompt_template = self._get_translation_prompt_template(
            source_lang, target_lang
        )

        if self._progress:
            iterator = self._progress(enumerate(chunks), desc="Translating Chunks...")
        else:
            iterator = enumerate(chunks)

        for i, chunk in iterator:
            translated_chunk = self._translate_single_chunk(chunk, i, prompt_template)
            translated_chunks.append(translated_chunk)

        return translated_chunks


def _translate_chapter(
    chapter: Chapter,
    translator: GlossaryAwareTranslator,
    source_lang: str,
    target_lang: str,
    chapter_repo: ChapterRepository,
    progress: Progress,
    task_id,
) -> bool:
    """
    Translate a single chapter and save to database.

    Returns True on success, False on failure.
    """
    if not chapter.original_text:
        progress.update(task_id, description="[dim]No original text, skipping[/dim]")
        return False

    if not chapter.id:
        progress.update(task_id, description="[red]Chapter has no ID[/red]")
        return False

    try:
        translated_text = translator.translate_text(
            chapter.original_text, source_lang, target_lang
        )

        if translated_text:
            chapter.translated_text = translated_text
            chapter_repo.update(chapter)
            progress.update(task_id, description="[green]✓ Translated[/green]")
            return True
        else:
            progress.update(task_id, description="[red]Empty translation[/red]")
            return False

    except Exception as e:
        logger.error(f"Error translating chapter {chapter.chapter_number}: {e}")
        progress.update(task_id, description=f"[red]Error: {str(e)[:30]}[/red]")
        return False


def _translate_volume(
    volume: Volume,
    work: Work,
    translator: GlossaryAwareTranslator,
    chapter_repo: ChapterRepository,
    source_lang: str,
    target_lang: str,
    skip_translated: bool = True,
) -> tuple[int, int]:
    """
    Translate all chapters in a volume.

    Returns tuple of (success_count, failure_count).
    """
    if volume.id is None:
        console.print("[red]Volume has no ID.[/red]")
        return (0, 0)

    chapters = chapter_repo.get_by_volume(volume.id)
    if not chapters:
        console.print("[yellow]No chapters found in volume.[/yellow]")
        return (0, 0)

    success = 0
    failure = 0
    skipped = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        for chapter in sorted(chapters, key=_get_chapter_sort_key):
            ch_display = _format_chapter_display(chapter)
            task_id = progress.add_task(f"[cyan]{ch_display}", total=None)

            # Skip already translated chapters if requested
            if skip_translated and chapter.translated_text:
                progress.update(
                    task_id,
                    description=f"[dim]{ch_display} (already translated, skipping)[/dim]",
                )
                skipped += 1
                progress.advance(task_id)
                continue

            if _translate_chapter(
                chapter,
                translator,
                source_lang,
                target_lang,
                chapter_repo,
                progress,
                task_id,
            ):
                success += 1
            else:
                failure += 1

            progress.advance(task_id)

    if skipped > 0:
        console.print(f"[dim]Skipped {skipped} already translated chapter(s)[/dim]")

    return (success, failure)


def _translate_book(
    work: Work,
    translator: GlossaryAwareTranslator,
    volume_repo: VolumeRepository,
    chapter_repo: ChapterRepository,
    source_lang: str,
    target_lang: str,
    skip_translated: bool = True,
) -> tuple[int, int]:
    """
    Translate all volumes and chapters in a book.

    Returns tuple of (success_count, failure_count).
    """
    if work.id is None:
        console.print("[red]Work has no ID.[/red]")
        return (0, 0)

    volumes = volume_repo.get_by_work_id(work.id)
    if not volumes:
        console.print("[yellow]No volumes found in book.[/yellow]")
        return (0, 0)

    total_success = 0
    total_failure = 0

    for volume in sorted(volumes, key=lambda v: v.volume_number):
        console.print(f"\n[bold]Processing Volume {volume.volume_number}[/bold]")

        success, failure = _translate_volume(
            volume,
            work,
            translator,
            chapter_repo,
            source_lang,
            target_lang,
            skip_translated=skip_translated,
        )

        total_success += success
        total_failure += failure

    return (total_success, total_failure)


def _print_translation_summary(success: int, failure: int, dry_run: bool = False):
    """Print summary table with translation results."""
    table = Table(
        title="Translation Summary", show_header=True, header_style="bold magenta"
    )
    table.add_column("Status", style="cyan")
    table.add_column("Count", justify="right", style="green")

    table.add_row("Successfully translated", str(success))
    table.add_row("Failed", str(failure))
    if dry_run:
        table.add_row("Mode", "[yellow]DRY-RUN (no saving)[/yellow]")

    console.print()
    console.print(table)


@app.command("translate")
def translate_chapter(
    source_lang: str = typer.Option(
        "en", "--source-lang", "-s", help="Source language"
    ),
    target_lang: str = typer.Option(
        "es", "--target-lang", "-t", help="Target language"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", "-d", help="Show what would be translated without saving"
    ),
    skip_translated: bool = typer.Option(
        True,
        "--skip-translated/--no-skip-translated",
        help="Skip already translated chapters (use --no-skip-translated to retranslate)",
    ),
):
    """
    Translate book chapters with glossary-aware context.

    Interactive command that guides through:
    1. Work selection
    2. Scope selection (All Book / All Volume / Single Chapter)
    3. Volume/Chapter selection as needed
    4. Translation with glossary context

    The glossary provides consistent translation for proper nouns,
    specialized terms, and entity names.

    Examples:
        pdftranslator translate
        pdftranslator translate --source-lang ja --target-lang es
        pdftranslator translate --dry-run
    """
    setup_logging()

    work_repo = BookRepository()
    volume_repo = VolumeRepository()
    chapter_repo = ChapterRepository()
    glossary_repo = GlossaryRepository()

    # Select work
    selected_work = _select_work_interactive(work_repo)
    if not selected_work:
        raise typer.Exit(0)

    console.print(Panel.fit(f"[bold blue]{selected_work.title}[/bold blue]"))

    # Select scope with context
    selected_scope = _select_scope_with_context(
        selected_work, volume_repo, chapter_repo
    )
    if not selected_scope:
        raise typer.Exit(0)

    # Get work_id for glossary
    work_id = selected_work.id
    if work_id is None:
        console.print("[red]Work has no ID.[/red]")
        raise typer.Exit(1)

    # Load glossary entries for the work
    console.print("[cyan]Loading glossary entries...[/cyan]")
    glossary_entries = glossary_repo.get_by_work(work_id)

    if glossary_entries:
        console.print(f"[green]Found {len(glossary_entries)} glossary entries[/green]")
    else:
        console.print("[yellow]No glossary entries found for this work[/yellow]")
        console.print(
            "[dim]Consider running 'build-glossary' first for better translations[/dim]"
        )

    # Use work's language settings if available
    effective_source = selected_work.source_lang or source_lang
    effective_target = selected_work.target_lang or target_lang

    console.print(
        f"[dim]Translating from {effective_source} to {effective_target}[/dim]"
    )

    translator = GlossaryAwareTranslator(glossary_entries=glossary_entries)

    total_success = 0
    total_failure = 0

    if selected_scope == SCOPE_ALL_BOOK:
        total_success, total_failure = _translate_book(
            work=selected_work,
            translator=translator,
            volume_repo=volume_repo,
            chapter_repo=chapter_repo,
            source_lang=effective_source,
            target_lang=effective_target,
            skip_translated=skip_translated,
        )

    elif selected_scope == SCOPE_ALL_VOLUME:
        selected_volume = _select_volume_interactive(selected_work, volume_repo)
        if not selected_volume:
            raise typer.Exit(0)

        total_success, total_failure = _translate_volume(
            volume=selected_volume,
            work=selected_work,
            translator=translator,
            chapter_repo=chapter_repo,
            source_lang=effective_source,
            target_lang=effective_target,
            skip_translated=skip_translated,
        )

    elif selected_scope == SCOPE_SINGLE_CHAPTER:
        selected_volume = _select_volume_interactive(selected_work, volume_repo)
        if not selected_volume:
            raise typer.Exit(0)

        selected_chapter = _select_chapter_interactive(selected_volume, chapter_repo)
        if not selected_chapter:
            raise typer.Exit(0)

        if selected_chapter.translated_text and skip_translated:
            console.print(
                "[yellow]Chapter already translated. Use --no-skip-translated to retranslate.[/yellow]"
            )
            raise typer.Exit(0)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task_id = progress.add_task("[cyan]Translating...", total=None)

            if dry_run:
                progress.update(
                    task_id, description="[yellow]DRY-RUN: Would translate[/yellow]"
                )
                total_success = 1
            else:
                success = _translate_chapter(
                    selected_chapter,
                    translator,
                    effective_source,
                    effective_target,
                    chapter_repo,
                    progress,
                    task_id,
                )
                total_success = 1 if success else 0
                total_failure = 0 if success else 1

    _print_translation_summary(total_success, total_failure, dry_run)

    if dry_run:
        console.print("\n[yellow]Dry-run mode: No changes were saved[/yellow]")
    else:
        console.print(
            f"\n[green]Translation complete: {total_success} chapters translated[/green]"
        )
