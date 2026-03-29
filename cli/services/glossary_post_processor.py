# cli/services/glossary_post_processor.py
"""
Glossary Post-Processor for Translation Consistency.

This module ensures 100% consistency of glossary terms in translated text
by validating and correcting terms after translation.
"""

import logging
import re
from typing import List, Dict, Set, Tuple
from database.models import GlossaryEntry

logger = logging.getLogger(__name__)


class GlossaryPostProcessor:
    """
    Validates and corrects glossary terms in translated text.

    Ensures all terms from the glossary are applied consistently,
    handling grammatical variations (case, plural, etc.).
    """

    def __init__(self, glossary_entries: List[GlossaryEntry], target_lang: str):
        """
        Initialize the post-processor.

        Args:
            glossary_entries: List of glossary terms to validate/correct
            target_lang: Target language code (e.g., 'es-MX')
        """
        self.entries = glossary_entries
        self.target_lang = target_lang
        self._variant_maps: Dict[str, Dict] = {}
        self._first_translation_map: Dict[str, str] = {}  # For consistency tracking
        self._correction_counts: Dict[str, int] = {}

        self._build_variant_maps()

    def process(self, translated_text: str) -> str:
        """
        Validate and correct glossary terms in translated text.

        Args:
            translated_text: The translated text to process

        Returns:
            Text with all glossary terms consistently applied
        """
        if not self.entries:
            logger.debug("No glossary entries to process")
            return translated_text

        logger.info(f"Processing {len(self.entries)} glossary entries")

        for entry in self.entries:
            translated_text = self._validate_and_fix(translated_text, entry)

        # Log summary
        total_corrections = sum(self._correction_counts.values())
        if total_corrections > 0:
            logger.info(f"Total corrections applied: {total_corrections}")
            for term, count in self._correction_counts.items():
                if count > 0:
                    logger.debug(f" - '{term}': {count} corrections")

        return translated_text

    def _build_variant_maps(self):
        """
        Pre-generate variant maps for each glossary entry.

        Creates lookup tables for efficient matching of term variants.
        """
        for entry in self.entries:
            self._variant_maps[entry.term] = self._generate_variants(entry)

    def _generate_variants(self, entry: GlossaryEntry) -> Dict:
        """
        Generate all variants for a glossary entry.

        Args:
            entry: The glossary entry

        Returns:
            Dict with 'correct' set and 'incorrect' patterns
        """
        variants = {
            "term": entry.term,
            "correct": set(),
            "incorrect_patterns": [],
            "is_do_not_translate": entry.do_not_translate,
            "expected_translation": entry.translation,
        }

        term = entry.term

        if entry.do_not_translate:
            # For DO NOT TRANSLATE, correct variants are the original term
            variants["correct"].add(term)
            variants["correct"].add(term.lower())
            variants["correct"].add(term.upper())
            variants["correct"].add(term.capitalize())

            # Common incorrect translations to detect and revert
            # These will be language-specific patterns
            variants["incorrect_patterns"].append(
                re.compile(r"\b" + re.escape(term.lower()) + r"\b", re.IGNORECASE)
            )

        elif entry.translation:
            # Has defined translation
            translation = entry.translation
            variants["correct"].add(translation)
            variants["correct"].add(translation.lower())
            variants["correct"].add(translation.upper())
            variants["correct"].add(translation.capitalize())

            # Add grammatical variants for target language
            variants["correct"].update(self._generate_grammatical_variants(translation))

            # Pattern to find the original term (which should be replaced)
            variants["incorrect_patterns"].append(
                re.compile(r"\b" + re.escape(term) + r"\b", re.IGNORECASE)
            )

        return variants

    def _generate_grammatical_variants(self, term: str) -> Set[str]:
        """
        Generate grammatical variants for a term.

        For Spanish: handles plurals, gender variations.

        Args:
            term: The base term

        Returns:
            Set of grammatical variants
        """
        variants = set()

        if self.target_lang.startswith("es"):
            # Spanish plural (add 's' or 'es')
            if term.endswith(("a", "e", "i", "o", "u")):
                variants.add(term + "s")
            elif term.endswith(("ón", "án", "ín")):
                # Words ending in -ón, -án, -ín: ón → ones
                base = term[:-2] + "one"
                variants.add(base + "s")
            else:
                variants.add(term + "es")

        # Common case variations
        variants.add(term.capitalize())

        return variants

    def _validate_and_fix(self, text: str, entry: GlossaryEntry) -> str:
        """
        Validate and correct a single glossary entry in text.

        Args:
            text: Text to process
            entry: Glossary entry to validate

        Returns:
            Text with entry validated/corrected
        """
        # Implementation in next task
        raise NotImplementedError("Implement in Task 5")
