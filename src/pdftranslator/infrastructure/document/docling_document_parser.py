"""DoclingDocumentParser — adapter implementing DocumentParser protocol.

Resolves DIP-7: Wraps DoclingExtractor to conform to the
domain DocumentParser interface without modifying DoclingExtractor.
"""
from __future__ import annotations

import logging
from typing import Optional

from pdftranslator.domain.protocols.document_parser import DocumentParser

logger = logging.getLogger(__name__)


class DoclingDocumentParser:
    """Adapter that wraps DoclingExtractor to implement DocumentParser protocol.

    Uses lazy import to avoid hard dependency on docling at import time.
    """

    _SUPPORTED_EXTENSIONS = {".pdf", ".epub"}

    def __init__(self, config=None):
        self._config = config
        self._extractor = None

    @property
    def supported_extensions(self) -> set[str]:
        return self._SUPPORTED_EXTENSIONS

    @property
    def _extractor(self):
        return self.__extractor

    @_extractor.setter
    def _extractor(self, value):
        self.__extractor = value

    def parse(self, file_path: str) -> str | None:
        """Extract text from a document file.

        Returns None if extraction fails or file type is not supported.
        """
        from pathlib import Path

        path = Path(file_path)
        if path.suffix.lower() not in self._SUPPORTED_EXTENSIONS:
            logger.warning(f"Unsupported file type: {path.suffix}")
            return None

        try:
            if self.__extractor is None:
                from pdftranslator.infrastructure.document.docling_extractor import DoclingExtractor
                from pdftranslator.core.config.document import DoclingConfig

                config = self._config or DoclingConfig()
                self.__extractor = DoclingExtractor(config)

            doc = self.__extractor.extract(file_path)
            if doc is None:
                return None

            return doc.export_to_markdown()
        except Exception as e:
            logger.error(f"Error parsing document {file_path}: {e}", exc_info=True)
            return None
