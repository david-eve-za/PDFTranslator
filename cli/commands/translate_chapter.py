# cli/commands/translate_chapter.py
"""
Comando interactivo para traducción de capítulos con integración de glosario.

Permite seleccionar libro, volumen y capítulo, y utiliza el glosario existente
para proporcionar contexto de traducción más preciso.
"""

import logging
import re
from pathlib import Path
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

from cli.app import app, console, setup_logging
from database.models import Work, Volume, Chapter, GlossaryEntry
from database.repositories.book_repository import BookRepository
from database.repositories.chapter_repository import ChapterRepository
from database.repositories.volume_repository import VolumeRepository
from database.repositories.glossary_repository import GlossaryRepository
from tools.Translator import Translator
from GlobalConfig import GlobalConfig

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


def _build_glossary_section(
    glossary_entries: List[GlossaryEntry],
    source_lang: str,
    target_lang: str,
    max_entries: int = 50,
) -> str:
    """
    Builds a formatted glossary section for the translation prompt.

    This section provides context for specialized terms, proper nouns,
    and entity translations to ensure consistency.

    Args:
        glossary_entries: List of glossary terms
        source_lang: Source language
        target_lang: Target language
        max_entries: Maximum number of entries to include (to control token usage)

    Returns:
        Formatted glossary section string
    """
    if not glossary_entries:
        return ""

    # Limit entries if too many (prioritize verified and translated entries)
    if len(glossary_entries) > max_entries:
        # Sort by priority: verified > has_translation > do_not_translate > others
        def entry_priority(e):
            score = 0
            if e.is_verified:
                score += 100
            if e.translation:
                score += 50
            if e.do_not_translate:
                score += 30  # Important to know what NOT to translate
            return score

        glossary_entries = sorted(glossary_entries, key=entry_priority, reverse=True)[
            :max_entries
        ]
        logger.info(f"Limited glossary to {max_entries} highest-priority entries")

    sections = []

    # Group entries by entity type
    by_type = {}
    for entry in glossary_entries:
        etype = entry.entity_type or "other"
        if etype not in by_type:
            by_type[etype] = []
        by_type[etype].append(entry)

    # Type labels for better readability
    type_labels = {
        "character": "Characters (Personajes)",
        "place": "Places (Lugares)",
        "skill": "Skills/Abilities (Habilidades)",
        "item": "Items (Objetos)",
        "spell": "Spells (Hechizos)",
        "faction": "Factions/Organizations (Organizaciones)",
        "title": "Titles (Títulos)",
        "race": "Races/Species (Razas)",
        "other": "Other Terms (Otros)",
    }

    for etype, entries in sorted(by_type.items()):
        label = type_labels.get(etype, etype.capitalize())
        section_lines = [f"\n**{label}:**"]

        for entry in entries:
            if entry.do_not_translate:
                # Term should remain in original language
                section_lines.append(
                    f"  - **{entry.term}**: [DO NOT TRANSLATE - Keep as '{entry.term}']"
                )
            elif entry.translation:
                # Term has an established translation
                context_hint = f" ({entry.notes})" if entry.notes else ""
                section_lines.append(
                    f"  - **{entry.term}**: {entry.translation}{context_hint}"
                )
            else:
                # Term needs translation guidance
                section_lines.append(
                    f"  - **{entry.term}**: [Translate consistently throughout]"
                )

        sections.append("\n".join(section_lines))

    if not sections:
        return ""

    return f"""
### Glossary Reference (Use these translations consistently) ###
The following terms have established translations or special handling requirements.
Maintain absolute consistency with these terms throughout the translation.

{"".join(sections)}

**Important:** When encountering these terms in the source text, use the glossary 
translation exactly. If a term is marked "DO NOT TRANSLATE", keep it in the 
original language without modification.
"""


def _build_enhanced_prompt(
    base_prompt: str,
    text_chunk: str,
    source_lang: str,
    target_lang: str,
    glossary_section: str,
) -> str:
    """
    Builds the enhanced translation prompt with glossary context.

    If the base prompt contains a {glossary_section} placeholder, it will be
    filled directly. Otherwise, the glossary section is inserted before the
    processing protocol section.
    """
    # Check if the template has a glossary_section placeholder
    if "{glossary_section}" in base_prompt:
        # Use the placeholder directly
        enhanced = base_prompt
    elif glossary_section:
        # Insert glossary section before the processing protocol
        protocol_marker = "### Rigorous Processing Protocol"
        if protocol_marker in base_prompt:
            parts = base_prompt.split(protocol_marker, 1)
            enhanced = parts[0] + glossary_section + "\n\n" + protocol_marker + parts[1]
        else:
            # Fallback: prepend to the text section
            enhanced = base_prompt + "\n\n" + glossary_section
    else:
        enhanced = base_prompt

    # Format the prompt with all available placeholders
    return enhanced.format(
        source_lang=source_lang,
        target_lang=target_lang,
        text_chunk=text_chunk,
        glossary_section=glossary_section,
    )


class GlossaryAwareTranslator(Translator):
    """
    Extended Translator that incorporates glossary terms into translation prompts.

    Uses a specialized prompt template when glossary entries are available,
    falling back to the standard prompt for works without glossary.

    Important: This translator accounts for prompt overhead when splitting text,
    ensuring that the total token count (prompt + glossary + text) stays within
    the model's context limit.
    """

    # Path to the glossary-optimized prompt template
    GLOSSARY_PROMPT_PATH = "tools/translation_prompt_glossary.txt"

    # Safety margin for token calculation (accounts for variations in tokenization)
    TOKEN_SAFETY_MARGIN = 100

    # Target output tokens (reserve space for the translation output)
    # This should be roughly equal to input size for translation tasks
    OUTPUT_TOKEN_RESERVE_RATIO = 1.2  # Output can be slightly longer than input

    # Minimum chunk size to avoid tiny chunks
    MIN_CHUNK_SIZE = 300

    # Maximum glossary entries to include (to control token usage)
    DEFAULT_MAX_GLOSSARY_ENTRIES = 50

    def __init__(
        self,
        glossary_entries: List[GlossaryEntry],
        progress=None,
        max_glossary_entries: int = None,
    ):
        """
        Initialize with glossary entries for context-aware translation.

        Args:
            glossary_entries: List of glossary terms to use for translation guidance
            progress: Optional progress tracker
            max_glossary_entries: Maximum glossary entries to include (default: 50)
        """
        super().__init__(progress=progress)
        self.glossary_entries = glossary_entries
        self._use_glossary_prompt = len(glossary_entries) > 0
        self._max_glossary_entries = (
            max_glossary_entries or self.DEFAULT_MAX_GLOSSARY_ENTRIES
        )

        # Pre-calculate glossary section for token counting
        self._glossary_section_cache = None
        self._prompt_overhead_cache = None

    def _calculate_prompt_overhead(self, source_lang: str, target_lang: str) -> int:
        """
        Calculate the token overhead from prompt template and glossary.

        This must be called before splitting text to ensure proper chunk sizing.

        Returns:
            Number of tokens used by prompt + glossary (without text).
        """
        if self._prompt_overhead_cache is not None:
            return self._prompt_overhead_cache

        # Get the base prompt template
        prompt_template = self._get_raw_prompt_template()

        # Build glossary section with entry limit
        glossary_section = _build_glossary_section(
            self.glossary_entries,
            source_lang,
            target_lang,
            max_entries=self._max_glossary_entries,
        )

        # Create a sample prompt with empty text to measure overhead
        sample_prompt = _build_enhanced_prompt(
            base_prompt=prompt_template,
            text_chunk="",  # Empty text to measure just the overhead
            source_lang=source_lang,
            target_lang=target_lang,
            glossary_section=glossary_section,
        )

        # Count tokens
        overhead = self.llm_client.count_tokens(sample_prompt)
        overhead += self.TOKEN_SAFETY_MARGIN

        logger.info(
            f"Calculated prompt overhead: {overhead} tokens (including {self.TOKEN_SAFETY_MARGIN} safety margin)"
        )

        self._prompt_overhead_cache = overhead
        self._glossary_section_cache = glossary_section

        return overhead

    def _get_raw_prompt_template(self) -> str:
        """Get the raw prompt template without formatting."""
        if self._use_glossary_prompt:
            glossary_prompt_path = Path(self.GLOSSARY_PROMPT_PATH)
            if glossary_prompt_path.exists():
                with open(glossary_prompt_path, "r", encoding="utf-8") as f:
                    return f.read()

        with open(self.config.translation_prompt_path, "r", encoding="utf-8") as f:
            return f.read()

    def _get_effective_chunk_size(self, source_lang: str, target_lang: str) -> int:
        """
        Calculate the effective chunk size accounting for prompt overhead.

        Returns:
            Maximum number of tokens for text content per chunk.
        """
        # Get the model's context size from config
        context_size = self.config.nvidia_context_size

        # Calculate overhead (prompt template + glossary)
        overhead = self._calculate_prompt_overhead(source_lang, target_lang)

        # Calculate available space after overhead
        available_after_overhead = context_size - overhead

        # Reserve space for output (translations can be slightly longer)
        # Use dynamic output reserve based on available space
        output_reserve = int(
            available_after_overhead
            * self.OUTPUT_TOKEN_RESERVE_RATIO
            / (1 + self.OUTPUT_TOKEN_RESERVE_RATIO)
        )

        # Final chunk size for input text
        effective_chunk_size = available_after_overhead - output_reserve

        # Ensure minimum chunk size
        if effective_chunk_size < self.MIN_CHUNK_SIZE:
            logger.warning(
                f"Calculated chunk size ({effective_chunk_size}) is too small. "
                f"Using minimum of {self.MIN_CHUNK_SIZE} tokens. "
                f"Consider increasing nvidia_context_size in config."
            )
            effective_chunk_size = self.MIN_CHUNK_SIZE

        logger.info(
            f"Chunk sizing: context={context_size}, overhead={overhead}, "
            f"output_reserve={output_reserve}, effective_chunk={effective_chunk_size}"
        )

        return effective_chunk_size

    def _get_translation_prompt_template(
        self, source_lang: str, target_lang: str
    ) -> str:
        """
        Get the appropriate prompt template based on glossary availability.

        Returns:
            The glossary-optimized prompt if entries exist, otherwise the standard prompt.
        """
        if self._use_glossary_prompt:
            # Try to load the glossary-optimized prompt
            glossary_prompt_path = Path(self.GLOSSARY_PROMPT_PATH)
            if glossary_prompt_path.exists():
                with open(glossary_prompt_path, "r", encoding="utf-8") as f:
                    return f.read()
            else:
                logger.warning(
                    f"Glossary prompt not found at {self.GLOSSARY_PROMPT_PATH}, "
                    "falling back to standard prompt"
                )

        # Fall back to standard prompt
        with open(self.config.translation_prompt_path, "r", encoding="utf-8") as f:
            return f.read()

    def split_text_with_overhead(
        self, text: str, source_lang: str, target_lang: str
    ) -> List[str]:
        """
        Split text into chunks that account for prompt overhead.

        This is the preferred method for splitting text before translation,
        as it ensures the total prompt (template + glossary + text) fits
        within the model's context limit.

        Args:
            text: The text to split
            source_lang: Source language code
            target_lang: Target language code

        Returns:
            List of text chunks sized appropriately for translation
        """
        effective_chunk_size = self._get_effective_chunk_size(source_lang, target_lang)

        logger.info(f"Splitting text into chunks of max {effective_chunk_size} tokens")

        # Use the LLM client's tokenizer with our calculated size
        from langchain_text_splitters import NLTKTextSplitter

        text_splitter = NLTKTextSplitter(
            chunk_size=effective_chunk_size,
            chunk_overlap=100,  # Add some overlap for context continuity
            language="english",
            length_function=self.llm_client.count_tokens,
        )

        chunks = text_splitter.split_text(text)

        # Log chunk sizes for debugging
        for i, chunk in enumerate(chunks):
            chunk_tokens = self.llm_client.count_tokens(chunk)
            total_tokens = self._prompt_overhead_cache + chunk_tokens
            logger.debug(
                f"Chunk {i + 1}: {chunk_tokens} tokens (total with prompt: {total_tokens})"
            )

        return chunks

    def translate_text(self, full_text: str, source_lang: str, target_lang: str) -> str:
        """
        Translate text with proper chunk sizing that accounts for prompt overhead.

        Overrides parent method to use overhead-aware chunking.
        """
        # Use our custom splitting method
        original_chunks = self.split_text_with_overhead(
            full_text, source_lang, target_lang
        )

        logger.info(
            f" - Original text split into {len(original_chunks)} chunks for translation."
        )

        if not original_chunks:
            logger.warning(
                " - Warning: The original text resulted in 0 chunks. Check input."
            )
            return ""

        translated_text_parts = self._translate_chunks(
            original_chunks, source_lang, target_lang
        )

        logger.info("Translation of all chunks completed.")
        full_translated_text = "\n\n".join(translated_text_parts)
        full_translated_text = re.sub(r"\n{3,}", "\n\n", full_translated_text).strip()

        return full_translated_text

    def _translate_single_chunk(
        self,
        chunk: str,
        chunk_index: int,
        base_prompt_template: str,
        source_lang: str,
        target_lang: str,
    ) -> str:
        """
        Translate a single chunk with glossary context.

        Overrides parent to inject glossary terms.
        """
        glossary_section = _build_glossary_section(
            self.glossary_entries,
            source_lang,
            target_lang,
            max_entries=self._max_glossary_entries,
        )

        enhanced_prompt = _build_enhanced_prompt(
            base_prompt=base_prompt_template,
            text_chunk=chunk,
            source_lang=source_lang,
            target_lang=target_lang,
            glossary_section=glossary_section,
        )

        # Log token counts for debugging
        prompt_tokens = self.llm_client.count_tokens(enhanced_prompt)
        logger.debug(f"Chunk {chunk_index + 1}: Prompt total = {prompt_tokens} tokens")

        try:
            translated_chunk = self.llm_client.call_model(enhanced_prompt)
            return translated_chunk if translated_chunk is not None else ""
        except Exception as e:
            logger.error(f"Error during LLM call for chunk {chunk_index + 1}: {e}")
            return self._ERROR_CHUNK_MARKER_FORMAT.format(index=chunk_index + 1)

    def _translate_chunks(
        self, chunks: list[str], source_lang: str, target_lang: str
    ) -> list[str]:
        """Translate all chunks with progress tracking."""
        translated_chunks = []
        prompt_template = self._get_translation_prompt_template(
            source_lang, target_lang
        )

        if self._progress:
            iterator = self._progress(enumerate(chunks), desc="Translating Chunks...")
        else:
            iterator = enumerate(chunks)

        for i, chunk in iterator:
            translated_chunk = self._translate_single_chunk(
                chunk, i, prompt_template, source_lang, target_lang
            )
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
    max_glossary_entries: int = typer.Option(
        50, "--max-glossary", "-g", help="Maximum glossary entries to include in prompt"
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

    # Create translator with glossary
    translator = GlossaryAwareTranslator(
        glossary_entries=glossary_entries, max_glossary_entries=max_glossary_entries
    )

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
