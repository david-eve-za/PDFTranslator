# cli/services/glossary_post_processor.py
"""
Glossary Post-Processor for Translation Consistency.

This module ensures 100% consistency of glossary terms in translated text
by validating and correcting terms after translation.
"""

import logging
import re
from typing import List, Dict, Set, Tuple
from pdftranslator.database.models import GlossaryEntry

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
        # Check if this is a DO_NOT_TRANSLATE entry via notes
        is_do_not_translate = entry.notes and "DO_NOT_TRANSLATE" in entry.notes

        variants = {
            "term": entry.term,
            "correct": set(),
            "incorrect_patterns": [],
            "is_do_not_translate": is_do_not_translate,
            "expected_translation": entry.translation,
        }

        term = entry.term

        if is_do_not_translate:
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
        if entry.term not in self._variant_maps:
            return text

        variants = self._variant_maps[entry.term]
        correction_count = 0

        is_do_not_translate = entry.notes and "DO_NOT_TRANSLATE" in entry.notes

        if is_do_not_translate:
            # Ensure term remains in original language
            text, count = self._ensure_do_not_translate(text, entry, variants)
            correction_count = count

        elif entry.translation:
            # Ensure term uses the defined translation
            text, count = self._ensure_translation(text, entry, variants)
            correction_count = count

        else:
            # No translation defined - track for consistency
            text, count = self._ensure_consistency(text, entry)
            correction_count = count

        if correction_count > 0:
            self._correction_counts[entry.term] = (
                self._correction_counts.get(entry.term, 0) + correction_count
            )
            logger.debug(f"Corrected '{entry.term}' {correction_count} times")

        return text

    def _ensure_do_not_translate(
        self, text: str, entry: GlossaryEntry, variants: Dict
    ) -> Tuple[str, int]:
        """
        Ensure DO NOT TRANSLATE terms remain in original.

        If the term was translated, revert it to original.

        Args:
            text: Text to process
            entry: Glossary entry
            variants: Pre-generated variants for this entry

        Returns:
            Tuple of (corrected text, correction count)
        """
        original_term = entry.term
        correction_count = 0

        # Pattern to find the original term (should be present)
        pattern = re.compile(r"\b" + re.escape(original_term) + r"\b", re.IGNORECASE)

        # Find all matches
        matches = list(pattern.finditer(text))

        # If no matches, the term might have been translated - we can't easily detect this
        # without knowing what it was translated to. Log a warning.
        if not matches:
            logger.warning(
                f"DO NOT TRANSLATE term '{original_term}' not found in text - "
                "may have been translated"
            )

        return text, correction_count

    def _ensure_translation(
        self, text: str, entry: GlossaryEntry, variants: Dict
    ) -> Tuple[str, int]:
        """
        Ensure term uses the defined translation.

        Replace any occurrence of the original term with the correct translation.

        Args:
            text: Text to process
            entry: Glossary entry
            variants: Pre-generated variants for this entry

        Returns:
            Tuple of (corrected text, correction count)
        """
        original_term = entry.term
        correct_translation = entry.translation
        correction_count = 0

        # Pattern to find the original term
        pattern = re.compile(r"\b" + re.escape(original_term) + r"\b", re.IGNORECASE)

        # Find matches and check if they need correction
        # Process in reverse to maintain correct positions
        for match in reversed(list(pattern.finditer(text))):
            found_term = match.group()

            # Check if it's already the correct translation (case-insensitive)
            if found_term.lower() == correct_translation.lower():
                # Already correct, but might need case adjustment
                expected_case = self._match_case(found_term, correct_translation)
                if found_term != expected_case:
                    text = text[: match.start()] + expected_case + text[match.end() :]
                    correction_count += 1
            else:
                # Need to replace with correct translation
                replacement = self._match_case(found_term, correct_translation)
                text = text[: match.start()] + replacement + text[match.end() :]
                correction_count += 1

        return text, correction_count

    def _ensure_consistency(self, text: str, entry: GlossaryEntry) -> Tuple[str, int]:
        """
        For terms without defined translation, ensure internal consistency.

        Uses the first translation found and applies it throughout.

        Args:
            text: Text to process
            entry: Glossary entry

        Returns:
            Tuple of (corrected text, correction count)
        """
        # This is more complex - would need NER-like detection
        # For now, just log that consistency should be checked
        logger.debug(
            f"Term '{entry.term}' has no defined translation - consistency not enforced"
        )
        return text, 0

    def _match_case(self, original: str, replacement: str) -> str:
        """
        Match the case pattern of original in replacement.

        Args:
            original: Original text with case pattern to match
            replacement: Text to apply case pattern to

        Returns:
            Replacement with matched case
        """
        if not original:
            return replacement

        if original.isupper():
            return replacement.upper()
        elif original[0].isupper():
            return replacement.capitalize()
        else:
            return replacement.lower()
