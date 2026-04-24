import pytest
from unittest.mock import Mock, patch, MagicMock
from pdftranslator.database.services.glossary_manager import GlossaryManager
from pdftranslator.database.models import EntityCandidate, BuildResult
from pdftranslator.database.connection import DatabasePool


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


class TestGlossaryManager:
    def test_build_from_text_returns_result(self, mock_pool, mock_connection):
        mock_pool.get_sync_pool.return_value.connection.return_value.__enter__ = (
            MagicMock(return_value=mock_connection[0])
        )
        mock_connection[1].fetchall.return_value = []
        mock_connection[1].fetchone.return_value = None

        with patch(
            "pdftranslator.database.services.glossary_manager.EntityExtractor"
        ) as mock_extractor_cls:
            with patch(
                "pdftranslator.database.services.glossary_manager.GlossaryRepository"
            ) as mock_glossary_cls:
                with patch(
                    "pdftranslator.database.services.glossary_manager.GlossaryBuildProgressRepository"
                ) as mock_progress_cls:
                    with patch(
                        "pdftranslator.database.services.glossary_manager.VectorStoreService"
                    ) as mock_vector_cls:
                        mock_extractor = MagicMock()
                        mock_extractor.extract.return_value = [
                            EntityCandidate(
                                text="Alice", entity_type="character", frequency=2
                            )
                        ]
                        mock_extractor_cls.return_value = mock_extractor

                        mock_glossary = MagicMock()
                        mock_glossary.filter_new_entities.return_value = []
                        mock_glossary_cls.return_value = mock_glossary

                        mock_progress = MagicMock()
                        mock_progress_cls.return_value = mock_progress

                        mock_vector = MagicMock()
                        mock_vector.embed_entities_for_glossary.return_value = []
                        mock_vector_cls.return_value = mock_vector

                        manager = GlossaryManager(mock_pool)
                        result = manager.build_from_text(
                            text="Alice went to Wonderland. Alice met the Queen. The Queen was angry.",
                            work_id=1,
                            volume_id=1,
                            source_lang="en",
                            target_lang="es",
                            suggest_translations=False,
                        )

                        assert result.extracted > 0
                        assert hasattr(result, "new")
                        assert hasattr(result, "skipped")
                        assert hasattr(result, "entities_by_type")

    @patch("pdftranslator.database.services.glossary_manager.NvidiaLLM")
    def test_suggest_translations_returns_dict(
        self, mock_llm_class, mock_pool, mock_connection
    ):
        mock_llm = Mock()
        mock_llm.call_model.return_value = '{"Alice": "Alicia"}'
        mock_llm._settings.llm.nvidia.max_output_tokens = 4096
        mock_llm_class.return_value = mock_llm

        mock_pool.get_sync_pool.return_value.connection.return_value.__enter__ = (
            MagicMock(return_value=mock_connection[0])
        )

        with patch(
            "pdftranslator.database.services.glossary_manager.EntityExtractor"
        ) as mock_extractor_cls:
            with patch(
                "pdftranslator.database.services.glossary_manager.GlossaryRepository"
            ) as mock_glossary_cls:
                with patch(
                    "pdftranslator.database.services.glossary_manager.GlossaryBuildProgressRepository"
                ) as mock_progress_cls:
                    with patch(
                        "pdftranslator.database.services.glossary_manager.VectorStoreService"
                    ) as mock_vector_cls:
                        mock_extractor = MagicMock()
                        mock_extractor.extract.return_value = []
                        mock_extractor_cls.return_value = mock_extractor

                        mock_glossary = MagicMock()
                        mock_glossary.filter_new_entities.return_value = []
                        mock_glossary_cls.return_value = mock_glossary

                        mock_progress = MagicMock()
                        mock_progress_cls.return_value = mock_progress

                        mock_vector = MagicMock()
                        mock_vector.embed_entities_for_glossary.return_value = []
                        mock_vector_cls.return_value = mock_vector

                        manager = GlossaryManager(mock_pool)
                        manager._llm_client = mock_llm

                        entities = [
                            EntityCandidate(
                                text="Alice", entity_type="character", frequency=2
                            )
                        ]
                        translations = manager._suggest_translations(
                            entities, "en", "es"
                        )

                        assert isinstance(translations, dict)

    def test_get_glossary_for_work(self, mock_pool, mock_connection):
        mock_pool.get_sync_pool.return_value.connection.return_value.__enter__ = (
            MagicMock(return_value=mock_connection[0])
        )

        with patch(
            "pdftranslator.database.services.glossary_manager.GlossaryRepository"
        ) as mock_glossary_cls:
            mock_glossary = MagicMock()
            mock_glossary.get_by_work.return_value = []
            mock_glossary_cls.return_value = mock_glossary

            manager = GlossaryManager(mock_pool)
            result = manager.get_glossary_for_work(1)

            assert isinstance(result, list)

    def test_build_from_text_with_no_entities(self, mock_pool, mock_connection):
        mock_pool.get_sync_pool.return_value.connection.return_value.__enter__ = (
            MagicMock(return_value=mock_connection[0])
        )

        with patch(
            "pdftranslator.database.services.glossary_manager.EntityExtractor"
        ) as mock_extractor_cls:
            with patch(
                "pdftranslator.database.services.glossary_manager.GlossaryRepository"
            ) as mock_glossary_cls:
                with patch(
                    "pdftranslator.database.services.glossary_manager.GlossaryBuildProgressRepository"
                ) as mock_progress_cls:
                    with patch(
                        "pdftranslator.database.services.glossary_manager.VectorStoreService"
                    ) as mock_vector_cls:
                        mock_extractor = MagicMock()
                        mock_extractor.extract.return_value = []
                        mock_extractor_cls.return_value = mock_extractor

                        mock_glossary = MagicMock()
                        mock_glossary_cls.return_value = mock_glossary

                        mock_progress = MagicMock()
                        mock_progress_cls.return_value = mock_progress

                        mock_vector = MagicMock()
                        mock_vector_cls.return_value = mock_vector

                        manager = GlossaryManager(mock_pool)
                        result = manager.build_from_text(
                            text="Simple text.",
                            work_id=1,
                            volume_id=1,
                            source_lang="en",
                            target_lang="es",
                            suggest_translations=False,
                        )

                        assert result.extracted == 0
                        assert result.new == 0
