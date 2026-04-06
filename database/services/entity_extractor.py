"""
Entity extraction service using NLTK NER + regex patterns.
Detects entities that need special treatment in translation:
- Characters (PERSON)
- Places (LOCATION, GPE)
- Organizations (ORGANIZATION)
- Skills/Powers (SKILL) - fantasy specific
- Items/Artifacts (ITEM)
- Titles/Ranks (TITLE/RANK)
"""

from __future__ import annotations

import re
import logging
from collections import Counter
from typing import Dict, List, Optional, Set

import nltk
from nltk import word_tokenize, pos_tag, ne_chunk, sent_tokenize
from nltk.corpus import words as nltk_words
from nltk.tree import Tree

from database.models import EntityCandidate
from database.repositories.entity_blacklist_repository import EntityBlacklistRepository
from database.repositories.fantasy_term_repository import FantasyTermRepository
from database.connection import DatabasePool

logger = logging.getLogger(__name__)

NLTK_PACKAGES = [
    "punkt",
    "punkt_tab",
    "averaged_perceptron_tagger",
    "maxent_ne_chunker",
    "words",
    "maxent_ne_chunker_tab",
]

for pkg in NLTK_PACKAGES:
    try:
        nltk.download(pkg, quiet=True)
    except Exception:
        pass

try:
    ENGLISH_WORDS: Set[str] = set(w.lower() for w in nltk_words.words())
except Exception:
    ENGLISH_WORDS = set()

ENTITY_TYPES = {
    "PERSON": "character",
    "GPE": "place",
    "LOCATION": "place",
    "ORGANIZATION": "faction",
    "FACILITY": "place",
}

SKILL_PATTERN = re.compile(
    r"(?:"
    r"【([^】]{2,60})】"
    r"|《([^》]{2,60})》"
    r"|\[([^\]]{2,60})\]"
    r"|<([^>]{2,60})>"
    r'|"([A-Z][A-Za-z\s\'\-]{2,50})"'
    r"|'([A-Z][A-Za-z\s\'\-]{2,50})'"
    r")"
)

TITLE_PATTERN = re.compile(
    r"(?:"
    r"Lord|Lady|Sir|Duke|Duchess|Baron|Count|Countess|"
    r"Prince|Princess|King|Queen|Emperor|Empress|"
    r"Elder|Sect\s*Master|Grand\s*Master|Overlord|"
    r"Demon\s*King|Hero|Sage|Archmage"
    r")\s+([A-Z][A-Za-z\s\'\-]{1,50})",
    re.IGNORECASE,
)


class EntityExtractor:
    _english_words: Set[str] = ENGLISH_WORDS

    def __init__(
        self,
        pool: Optional[DatabasePool] = None,
        min_frequency: int = 2,
    ):
        self._pool = pool or DatabasePool.get_instance()
        self._blacklist_repo = EntityBlacklistRepository(pool)
        self._fantasy_repo = FantasyTermRepository(pool)
        self.min_frequency = min_frequency
        self._blacklist: Set[str] = set()
        self._fantasy_terms: Dict[str, any] = {}

    def _ensure_loaded(self):
        if not self._blacklist:
            self._blacklist = self._blacklist_repo.get_all_terms()
        if not self._fantasy_terms:
            self._fantasy_terms = self._fantasy_repo.get_all_terms()

    def _is_common_english_word(self, name: str) -> bool:
        words = name.split()
        if len(words) != 1:
            return False
        return name.lower() in self._english_words

    def extract(self, text: str, source_language: str = "en") -> List[EntityCandidate]:
        self._ensure_loaded()
        entity_counts: Dict[str, EntityCandidate] = {}

        if source_language in ("en", "en-US", "en-GB"):
            nltk_entities = self._extract_nltk(text)
            for ent in nltk_entities:
                key = ent.text.lower()
                if key in entity_counts:
                    entity_counts[key].frequency += ent.frequency
                    for ctx in ent.contexts:
                        entity_counts[key].add_context(ctx)
                else:
                    entity_counts[key] = ent

        pattern_entities = self._extract_patterns(text)
        for ent in pattern_entities:
            key = ent.text.lower()
            if key in entity_counts:
                entity_counts[key].frequency += ent.frequency
            else:
                entity_counts[key] = ent

        if source_language in ("en", "en-US", "en-GB"):
            pos_entities = self._extract_by_pos_frequency(text)
            for ent in pos_entities:
                key = ent.text.lower()
                if key not in entity_counts:
                    entity_counts[key] = ent

        filtered = [
            ent
            for ent in entity_counts.values()
            if (
                ent.frequency >= self.min_frequency
                and ent.text.lower() not in self._blacklist
                and len(ent.text) >= 2
            )
        ]

        for ent in filtered:
            if ent.text.lower() in self._fantasy_terms:
                ft = self._fantasy_terms[ent.text.lower()]
                ent.entity_type = ft.entity_type
                if ft.do_not_translate and not ent.contexts:
                    ent.add_context(ft.context_hint or "")
            ent.confidence = self._calculate_confidence(ent)

        priority_order = {
            "character": 0,
            "place": 1,
            "skill": 2,
            "item": 3,
            "faction": 4,
            "title": 5,
            "race": 6,
            "other": 9,
        }
        filtered.sort(
            key=lambda e: (priority_order.get(e.entity_type, 9), -e.frequency)
        )

        logger.info(f"Extracted {len(filtered)} entities from text ({len(text)} chars)")
        return filtered

    def _extract_nltk(self, text: str) -> List[EntityCandidate]:
        candidates: Dict[str, EntityCandidate] = {}
        sentences = sent_tokenize(text)

        for sent in sentences:
            try:
                tokens = word_tokenize(sent)
                tagged = pos_tag(tokens)
                tree = ne_chunk(tagged, binary=False)

                for subtree in tree:
                    if isinstance(subtree, Tree):
                        label = subtree.label()
                        name = " ".join(w for w, t in subtree.leaves())

                        if len(name) < 2 or name.lower() in self._blacklist:
                            continue

                        if self._is_common_english_word(name):
                            continue

                        etype = ENTITY_TYPES.get(label, "other")
                        key = name.lower()
                        idx = sent.find(name)
                        ctx = sent[max(0, idx - 50) : idx + len(name) + 50]

                        if key in candidates:
                            candidates[key].frequency += 1
                            candidates[key].add_context(ctx)
                        else:
                            candidates[key] = EntityCandidate(
                                text=name,
                                entity_type=etype,
                                frequency=1,
                                contexts=[ctx],
                                source_language="en",
                            )
            except Exception as e:
                logger.debug(f"Error NLTK NER in sentence: {e}")
                continue

        return list(candidates.values())

    def _extract_patterns(self, text: str) -> List[EntityCandidate]:
        candidates: Dict[str, EntityCandidate] = {}

        for m in SKILL_PATTERN.finditer(text):
            name = next((g for g in m.groups() if g), None)
            if name and len(name) >= 2:
                key = name.lower()
                ctx = text[max(0, m.start() - 40) : m.end() + 40]

                if key in candidates:
                    candidates[key].frequency += 1
                else:
                    candidates[key] = EntityCandidate(
                        text=name.strip(),
                        entity_type="skill",
                        frequency=1,
                        contexts=[ctx],
                        confidence=0.85,
                        source_language="en",
                    )

        for m in TITLE_PATTERN.finditer(text):
            full = m.group(0).strip()
            name = m.group(1).strip()
            key = full.lower()

            if key not in candidates and len(name) >= 2:
                ctx = text[max(0, m.start() - 30) : m.end() + 30]
                candidates[key] = EntityCandidate(
                    text=full,
                    entity_type="title",
                    frequency=1,
                    contexts=[ctx],
                    confidence=0.75,
                    source_language="en",
                )

        return list(candidates.values())

    def _extract_by_pos_frequency(self, text: str) -> List[EntityCandidate]:
        candidates: Dict[str, EntityCandidate] = {}
        word_pos_counts: Counter = Counter()

        sentences = sent_tokenize(text)
        for sent in sentences:
            try:
                tokens = word_tokenize(sent)
                tagged = pos_tag(tokens)
                for word, pos in tagged:
                    if pos in ("NNP", "NNPS") and len(word) >= 2:
                        word_pos_counts[word] += 1
            except Exception:
                continue

        for word, count in word_pos_counts.items():
            if (
                count >= self.min_frequency
                and word.lower() not in self._blacklist
                and not word.isnumeric()
                and len(word) >= 2
                and not self._is_common_english_word(word)
            ):
                key = word.lower()
                if key not in candidates:
                    candidates[key] = EntityCandidate(
                        text=word,
                        entity_type="character",
                        frequency=count,
                        confidence=0.5,
                        source_language="en",
                    )

        return list(candidates.values())

    def _calculate_confidence(self, ent: EntityCandidate) -> float:
        score = 0.5

        if ent.frequency >= 10:
            score += 0.3
        elif ent.frequency >= 5:
            score += 0.2
        elif ent.frequency >= 3:
            score += 0.1

        if ent.entity_type in ("skill", "item"):
            score += 0.2

        if ent.contexts:
            score += 0.1

        if len(ent.text) <= 2:
            score -= 0.2

        return min(1.0, max(0.0, score))
