import logging
from pathlib import Path
from typing import Dict, Any, Literal, Optional, List

import pdfplumber

from docling.datamodel.accelerator_options import AcceleratorOptions, AcceleratorDevice
from docling.datamodel.base_models import InputFormat
from docling.datamodel.document import ConversionResult
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling_core.types.doc import ImageRefMode

# Configure logging
logger = logging.getLogger(__name__)


class DocumentTextExtractor:
    """
    A class to encapsulate PDF conversion logic, supporting various output formats.

    This class uses the 'docling' library to convert a PDF file into formats like
    Markdown, HTML, plain text, or a dictionary. It features lazy loading to
    defer the costly conversion process until a format is actually requested.
    It also integrates pdfplumber for enhanced table extraction.
    """

    def __init__(self, file_path: Path, num_threads: int = 4, device: Literal['CPU', 'MPS', 'CUDA'] = 'CPU'):
        """
        Initializes the DocumentTextExtractor with a specific configuration.

        Args:
            file_path (Path): The path to the PDF file to process.
            num_threads (int): The number of threads to use for processing.
            device (str): The accelerator device to use (e.g., 'CPU', 'MPS', 'CUDA').
        """
        if not file_path.is_file():
            raise FileNotFoundError(f"The file was not found: {file_path}")

        self.file_path = file_path
        self._config = self._build_config(num_threads, device)
        self._converter = DocumentConverter(format_options=self._config)
        self._doc: Optional[ConversionResult] = None

    @property
    def doc(self) -> ConversionResult:
        """
        Provides access to the converted document, with lazy loading.

        The actual PDF conversion is deferred until this property is first accessed,
        optimizing initial load times.
        """
        if self._doc is None:
            logger.info(f"Starting conversion for: {self.file_path.name}")
            self._doc = self._converter.convert(str(self.file_path))
        return self._doc

    @staticmethod
    def _build_config(num_threads: int, device: str) -> Dict[InputFormat, PdfFormatOption]:
        """
        Builds the configuration for the PDF conversion process.
        """
        try:
            accelerator_device = AcceleratorDevice[device.upper()]
        except KeyError:
            logger.warning(f"Invalid accelerator device '{device}'. Defaulting to CPU.")
            accelerator_device = AcceleratorDevice.CPU

        return {
            InputFormat.PDF: PdfFormatOption(
                pipeline_options=PdfPipelineOptions(
                    generate_picture_images=True,
                    accelerator_options=AcceleratorOptions(
                        num_threads=num_threads,
                        device=accelerator_device
                    )
                )
            )
        }

    def _extract_tables_with_pdfplumber(self) -> str:
        """
        Extracts tables from the PDF using pdfplumber and returns them as Markdown strings.
        """
        tables_markdown = []
        try:
            with pdfplumber.open(self.file_path) as pdf:
                for page in pdf.pages:
                    extracted_tables = page.extract_tables()
                    for table in extracted_tables:
                        # Format table as Markdown
                        header = table[0]
                        rows = table[1:]
                        
                        # Ensure header and rows are not None before processing
                        if not header or not rows:
                            continue

                        # Create markdown table header
                        markdown = "|" + "|".join(header) + "|\n"
                        markdown += "|" + "|".join(["---"] * len(header)) + "|\n"
                        
                        # Add rows to markdown table
                        for row in rows:
                            # Replace None values with empty strings for proper markdown formatting
                            cleaned_row = [cell if cell is not None else "" for cell in row]
                            markdown += "|" + "|".join(cleaned_row) + "|\n"
                        tables_markdown.append(markdown)
        except Exception as e:
            logger.error(f"Error extracting tables with pdfplumber from {self.file_path.name}: {e}")
        return "\n\n".join(tables_markdown)

    def _extract_text_with_pdfplumber_layout_aware(self) -> str:
        """
        Extracts text from the PDF using pdfplumber, attempting to preserve layout.
        """
        full_text = []
        try:
            with pdfplumber.open(self.file_path) as pdf:
                for page in pdf.pages:
                    # Using layout=True to attempt preserving reading order in multi-column layouts
                    page_text = page.extract_text(layout=True)
                    if page_text:
                        full_text.append(page_text)
        except Exception as e:
            logger.error(f"Error extracting layout-aware text with pdfplumber from {self.file_path.name}: {e}")
            return ""
        return "\n".join(full_text)

    def extract_markdown(self, image_mode: ImageRefMode = ImageRefMode.EMBEDDED) -> str:
        """
        Extracts the content from the document and returns it as Markdown.

        Args:
            image_mode (ImageRefMode): The mode for handling images (e.g., EMBEDDED, REFERENCED).

        Returns:
            str: The Markdown representation of the document.
        """
        logger.info(f"Extracting Markdown from: {self.file_path.name} with image_mode='{image_mode.value}'")
        # Currently, docling_markdown is still the primary source for overall Markdown.
        # We will combine pdfplumber tables with it.
        docling_markdown = self.doc.document.export_to_markdown(image_mode=image_mode)
        pdfplumber_tables_markdown = self._extract_tables_with_pdfplumber()

        if pdfplumber_tables_markdown:
            return docling_markdown + "\n\n" + "## Extracted Tables\n\n" + pdfplumber_tables_markdown
        return docling_markdown

    def extract_html(self) -> str:
        """
        Extracts the content from the document and returns it as HTML.
        """
        logger.info(f"Extracting HTML from: {self.file_path.name}")
        return self.doc.document.export_to_html()

    def extract_text(self) -> str:
        """
        Extracts the plain text from the document, prioritizing pdfplumber's layout-aware
        extraction, and augmenting it with structured tables. Falls back to docling
        for general text extraction if pdfplumber fails to yield text.
        """
        logger.info(f"Extracting plain text from: {self.file_path.name}")
        
        pdfplumber_layout_text = self._extract_text_with_pdfplumber_layout_aware()
        pdfplumber_tables_markdown = self._extract_tables_with_pdfplumber()

        final_text_parts = []

        if pdfplumber_layout_text:
            final_text_parts.append(pdfplumber_layout_text)
        else:
            # Fallback to docling's text extraction if pdfplumber didn't yield layout-aware text
            logger.info("pdfplumber layout-aware text extraction failed or returned empty, falling back to docling.")
            final_text_parts.append(self.doc.document.export_to_text())

        if pdfplumber_tables_markdown:
            final_text_parts.append("\n\nExtracted Tables:\n\n" + pdfplumber_tables_markdown)
            
        return "".join(final_text_parts)

    def extract_dict(self) -> Dict[str, Any]:
        """
        Extracts the content from the document and returns it as a dictionary.
        """
        logger.info(f"Extracting dictionary from: {self.file_path.name}")
        return self.doc.document.export_to_dict()

    def extract_images(self) -> List[Any]:
        """
        Extracts all images from the document.
        """
        logger.info(f"Extracting images from: {self.file_path.name}")
        return self.doc.document.get_images()

    def save_to_markdown(self, output_path: Path, image_mode: ImageRefMode = ImageRefMode.EMBEDDED):
        """
        Saves the Document object as a Markdown file.

        Args:
            output_path (Path): The path to save the Markdown file.
            image_mode (ImageRefMode): The mode for handling images.
        """
        logger.info(f"Saving Markdown to: {output_path} with image_mode='{image_mode.value}'")
        self.doc.document.save_as_markdown(str(output_path), image_mode=image_mode)
        logger.info("Markdown file saved successfully.")
