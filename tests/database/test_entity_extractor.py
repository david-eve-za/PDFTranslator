import pytest
from unittest.mock import MagicMock, patch
from database.services.entity_extractor import (
    EntityExtractor,
    SKILL_PATTERN,
    TITLE_PATTERN,
)
from database.connection import DatabasePool


@pytest.fixture
def mock_pool():
    return MagicMock()


@pytest.fixture
def mock_connection():
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    return conn, cursor


@pytest.fixture(autouse=True)
def reset_database_pool():
    DatabasePool.reset_instance()
    yield
    DatabasePool.reset_instance()


class TestEntityExtractor:
    def test_skill_pattern_brackets(self):
        text = "He used 【Fireball】 to attack."
        matches = SKILL_PATTERN.findall(text)
        assert len(matches) > 0

    def test_title_pattern(self):
        text = "Lord Arthur entered the room."
        matches = TITLE_PATTERN.findall(text)
        assert len(matches) > 0

    def test_extract_finds_person(self, mock_pool, mock_connection):
        mock_pool.get_sync_pool.return_value.connection.return_value.__enter__ = (
            MagicMock(return_value=mock_connection[0])
        )
        mock_connection[1].fetchall.return_value = []
        mock_connection[1].fetchone.return_value = None

        with patch(
            "database.services.entity_extractor.EntityBlacklistRepository"
        ) as mock_blacklist_cls:
            with patch(
                "database.services.entity_extractor.FantasyTermRepository"
            ) as mock_fantasy_cls:
                mock_blacklist = MagicMock()
                mock_blacklist.get_all_terms.return_value = set()
                mock_blacklist_cls.return_value = mock_blacklist

                mock_fantasy = MagicMock()
                mock_fantasy.get_all_terms.return_value = {}
                mock_fantasy_cls.return_value = mock_fantasy

                extractor = EntityExtractor(mock_pool, min_frequency=1)
                text = "Xylara went to the market. Xylara bought apples. Xylara returned home."
                entities = extractor.extract(text)

                xylara_entities = [e for e in entities if e.text.lower() == "xylara"]
                assert len(xylara_entities) > 0

    def test_extract_filters_blacklist(self, mock_pool, mock_connection):
        mock_pool.get_sync_pool.return_value.connection.return_value.__enter__ = (
            MagicMock(return_value=mock_connection[0])
        )
        mock_connection[1].fetchall.return_value = []
        mock_connection[1].fetchone.return_value = None

        with patch(
            "database.services.entity_extractor.EntityBlacklistRepository"
        ) as mock_blacklist_cls:
            with patch(
                "database.services.entity_extractor.FantasyTermRepository"
            ) as mock_fantasy_cls:
                mock_blacklist = MagicMock()
                mock_blacklist.get_all_terms.return_value = {"chapter"}
                mock_blacklist_cls.return_value = mock_blacklist

                mock_fantasy = MagicMock()
                mock_fantasy.get_all_terms.return_value = {}
                mock_fantasy_cls.return_value = mock_fantasy

                extractor = EntityExtractor(mock_pool, min_frequency=1)
                text = "The chapter was long. The chapter continued."
                entities = extractor.extract(text)

                chapter_entities = [e for e in entities if e.text.lower() == "chapter"]
                assert len(chapter_entities) == 0

    def test_min_frequency_filters_single_occurrence(self, mock_pool, mock_connection):
        mock_pool.get_sync_pool.return_value.connection.return_value.__enter__ = (
            MagicMock(return_value=mock_connection[0])
        )
        mock_connection[1].fetchall.return_value = []
        mock_connection[1].fetchone.return_value = None

        with patch(
            "database.services.entity_extractor.EntityBlacklistRepository"
        ) as mock_blacklist_cls:
            with patch(
                "database.services.entity_extractor.FantasyTermRepository"
            ) as mock_fantasy_cls:
                mock_blacklist = MagicMock()
                mock_blacklist.get_all_terms.return_value = set()
                mock_blacklist_cls.return_value = mock_blacklist

                mock_fantasy = MagicMock()
                mock_fantasy.get_all_terms.return_value = {}
                mock_fantasy_cls.return_value = mock_fantasy

                extractor = EntityExtractor(mock_pool, min_frequency=2)
                text = "Xylophone appeared once in this text."
                entities = extractor.extract(text)

                xylophone_entities = [
                    e for e in entities if "xylophone" in e.text.lower()
                ]
                assert len(xylophone_entities) == 0

    def test_skill_pattern_finds_bracketed_text(self):
        text = "【Sword Art】 and 《Magic Spell》 were used."
        matches = SKILL_PATTERN.findall(text)
        assert len(matches) >= 2

    def test_title_pattern_finds_titles(self):
        text = "Sir Lancelot and Lady Guinevere met the King."
        matches = TITLE_PATTERN.findall(text)
        assert len(matches) >= 1

    def test_extract_returns_list(self, mock_pool, mock_connection):
        mock_pool.get_sync_pool.return_value.connection.return_value.__enter__ = (
            MagicMock(return_value=mock_connection[0])
        )
        mock_connection[1].fetchall.return_value = []
        mock_connection[1].fetchone.return_value = None

        with patch(
            "database.services.entity_extractor.EntityBlacklistRepository"
        ) as mock_blacklist_cls:
            with patch(
                "database.services.entity_extractor.FantasyTermRepository"
            ) as mock_fantasy_cls:
                mock_blacklist = MagicMock()
                mock_blacklist.get_all_terms.return_value = set()
                mock_blacklist_cls.return_value = mock_blacklist

                mock_fantasy = MagicMock()
                mock_fantasy.get_all_terms.return_value = {}
                mock_fantasy_cls.return_value = mock_fantasy

                extractor = EntityExtractor(mock_pool, min_frequency=1)
                text = "Test text for extraction."
                entities = extractor.extract(text)

                assert isinstance(entities, list)

    def test_common_english_words_filtered(self, mock_pool, mock_connection):
        mock_pool.get_sync_pool.return_value.connection.return_value.__enter__ = (
            MagicMock(return_value=mock_connection[0])
        )
        mock_connection[1].fetchall.return_value = []
        mock_connection[1].fetchone.return_value = None

        with patch(
            "database.services.entity_extractor.EntityBlacklistRepository"
        ) as mock_blacklist_cls:
            with patch(
                "database.services.entity_extractor.FantasyTermRepository"
            ) as mock_fantasy_cls:
                mock_blacklist = MagicMock()
                mock_blacklist.get_all_terms.return_value = set()
                mock_blacklist_cls.return_value = mock_blacklist

                mock_fantasy = MagicMock()
                mock_fantasy.get_all_terms.return_value = {}
                mock_fantasy_cls.return_value = mock_fantasy

                extractor = EntityExtractor(mock_pool, min_frequency=1)
                text = "Someone said that Good was there. Someone is good."
                entities = extractor.extract(text)

                someone_entities = [e for e in entities if "someone" in e.text.lower()]
                good_entities = [e for e in entities if "good" == e.text.lower()]

                assert len(someone_entities) == 0, (
                    "Common word 'someone' should be filtered"
                )
                assert len(good_entities) == 0, "Common word 'good' should be filtered"
