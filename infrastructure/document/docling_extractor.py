"""Docling-based document extractor."""

import logging
from pathlib import Path

from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    PdfPipelineOptions,
    EasyOcrOptions,
)
from docling.datamodel.accelerator_options import (
    AcceleratorOptions,
    AcceleratorDevice,
)
from docling.datamodel.document import ConversionResult
from docling_core.types.doc import DoclingDocument

from config.document import DoclingConfig

logger = logging.getLogger(__name__)


class DoclingExtractor:
    """Extract documents using Docling with optimized configuration."""

    def __init__(self, config: DoclingConfig | None = None):
        """
        Initialize DoclingExtractor.

        Args:
            config: Docling configuration. Uses defaults if None.
        """
        self.config = config or DoclingConfig()
        self._converter = self._create_converter()
        logger.info(f"DoclingExtractor initialized with config: {self.config}")

    def extract(self, filepath: str) -> DoclingDocument:
        """
        Extract document and return structured DoclingDocument.

        Args:
            filepath: Path to document (PDF, DOCX, etc.)

        Returns:
            DoclingDocument with hierarchical structure.

        Raises:
            FileNotFoundError: If filepath doesn't exist.
            ValueError: If format not supported.
        """
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"Document not found: {filepath}")

        logger.info(f"Extracting document: {filepath}")
        result: ConversionResult = self._converter.convert(str(path))
        logger.info(
            f"Extraction complete: {len(result.document.pages)} pages, "
            f"format: {path.suffix}"
        )
        return result.document

    def _create_converter(self) -> DocumentConverter:
        """
        Create DocumentConverter with configured pipeline.

        Returns:
            Configured DocumentConverter instance.
        """
        # Configure PDF pipeline
        pipeline_options = PdfPipelineOptions()

        # OCR settings
        pipeline_options.do_ocr = self.config.enable_ocr
        if self.config.enable_ocr:
            pipeline_options.ocr_options = EasyOcrOptions(
                lang=self.config.ocr_languages
            )

        # Table extraction
        pipeline_options.do_table_structure = self.config.do_table_structure

        # Image generation
        pipeline_options.generate_page_images = self.config.generate_page_images

        # Accelerator
        device_map = {
            "auto": AcceleratorDevice.AUTO,
            "cpu": AcceleratorDevice.CPU,
            "cuda": AcceleratorDevice.CUDA,
            "mps": AcceleratorDevice.MPS,
        }
        pipeline_options.accelerator_options = AcceleratorOptions(
            device=device_map[self.config.accelerator_device]
        )

        # Create converter with PDF format options
        converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            }
        )

        logger.debug(f"Converter created with pipeline options: {pipeline_options}")
        return converter
