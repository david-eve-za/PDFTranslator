"""Group document content by sections using Docling hierarchy."""

import logging
from dataclasses import dataclass, field

from docling_core.types.doc import (
    DoclingDocument,
    SectionHeaderItem,
    TextItem,
    TitleItem,
)

logger = logging.getLogger(__name__)


@dataclass
class Section:
    """Represents a document section with metadata."""

    title: str
    level: int
    content: list[str] = field(default_factory=list)

    def finalize(self) -> dict:
        """Convert to dictionary with joined content."""
        return {
            "title": self.title,
            "level": self.level,
            "content": "\n\n".join(self.content),
        }


class SectionGrouper:
    """Group DoclingDocument content by section headers."""

    def group_by_sections(self, doc: DoclingDocument) -> list[dict]:
        """
        Iterate over document and group content under each header.

        Args:
            doc: DoclingDocument to process.

        Returns:
            List of section dicts with keys: title, level, content.
        """
        sections: list[Section] = []
        current_section: Section | None = None

        for item, level in doc.iterate_items():
            # Handle headers (start new section)
            if isinstance(item, (SectionHeaderItem, TitleItem)):
                # Save previous section
                if current_section is not None and current_section.content:
                    sections.append(current_section)

                # Start new section
                header_level = getattr(item, "level", level)
                current_section = Section(
                    title=item.text,
                    level=header_level,
                    content=[],
                )
                logger.debug(f"New section: '{item.text}' (level {header_level})")

            # Handle text (add to current section)
            elif isinstance(item, TextItem):
                if current_section is None:
                    # Text before any header -> create implicit section
                    current_section = Section(
                        title="Untitled",
                        level=0,
                        content=[],
                    )
                current_section.content.append(item.text)

        # Add final section
        if current_section is not None and current_section.content:
            sections.append(current_section)

        logger.info(f"Grouped {len(sections)} sections from document")
        return [s.finalize() for s in sections]
