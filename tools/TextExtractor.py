import logging
import re
import zipfile
from pathlib import Path
from typing import Optional, Dict, Callable, List, Tuple, Set

import ebooklib
import fitz  # PyMuPDF
from bs4 import BeautifulSoup
from ebooklib import epub

# Configure logging
logger = logging.getLogger(__name__)

# Define constants for better readability and maintainability
PDF_EXTENSION = ".pdf"
EPUB_EXTENSION = ".epub"


class TextExtractorAgent:
    """
    An agent responsible for extracting and cleaning text from PDF and EPUB files.
    """

    def __init__(self, html_tags_to_remove: Optional[List[str]] = None):
        """
        Initializes the text extraction agent.

        Args:
            html_tags_to_remove: A list of HTML tags to be removed from the content of EPUBs.
                                 If not provided, a default list will be used.
        """
        self._extraction_methods: Dict[str, Callable] = {
            PDF_EXTENSION: self._extract_from_pdf,
            EPUB_EXTENSION: self._extract_from_epub,
        }
        self.html_tags_to_remove = html_tags_to_remove or ['script', 'style', 'nav', 'footer', 'header']

    def extract_text(self, file_path: str, extract_images: bool = True) -> Optional[Tuple[str, List[Path]]]:
        """
        Extracts and cleans text from a given file.

        Args:
            file_path: The path to the file (PDF or EPUB).
            extract_images: If True, extracts images from PDF files.

        Returns:
            A tuple containing the cleaned text and a list of paths to extracted images,
            or None if the file type is not supported or an error occurs.
        """
        path_obj = Path(file_path)
        extension = path_obj.suffix.lower()
        logger.info(f"Starting text extraction from: {path_obj.name}")

        extraction_method = self._extraction_methods.get(extension)
        if not extraction_method:
            logger.warning(f"Unsupported extension '{extension}' for file {path_obj.name}")
            return None

        try:
            if not path_obj.is_file():
                raise FileNotFoundError(f"File not found at path: {file_path}")

            # The 'extract_images' argument is only relevant for PDFs.
            if extension == PDF_EXTENSION:
                return extraction_method(path_obj, extract_images=extract_images)
            else:
                return extraction_method(path_obj)

        except FileNotFoundError as e:
            logger.error(f"File error: {e}", exc_info=True)
        except (epub.EpubException, zipfile.BadZipFile, fitz.fitz.PyMuPDFError) as e:
            logger.error(f"Error processing file '{path_obj.name}'. It may be corrupt or invalid: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"An unexpected error occurred while processing {path_obj.name}: {e}", exc_info=True)

        return None

    def _clean_extracted_text(self, text: str) -> str:
        """
        Cleans the extracted text by removing common artifacts using regex.
        """
        logger.info("  - Cleaning extracted text...")
        cleaned_text = text

        # Remove URLs (http/https links)
        cleaned_text = re.sub(r'https?://\S+', '', cleaned_text, flags=re.IGNORECASE)
        # Remove URLs without http/https prefix (e.g., www.example.com, example.com/path)
        # This needs to be done carefully to avoid removing legitimate words.
        # This regex looks for word boundaries around common domain patterns.
        cleaned_text = re.sub(r'\b(?:www\.)?[\w.-]+\.(?:com|org|net|gov|edu|io|co|ai|app|blog|info|biz|dev|me|xyz)(?:\/\S*)?\b', '', cleaned_text, flags=re.IGNORECASE)
        # Remove social media mentions (@username)
        cleaned_text = re.sub(r'@\w+', '', cleaned_text)
        # Remove hashtags (#hashtag)
        cleaned_text = re.sub(r'#\w+', '', cleaned_text)
        # Remove common social media platform names (case-insensitive)
        cleaned_text = re.sub(r'\b(?:Twitter|Facebook|Instagram|LinkedIn|YouTube|Reddit|Pinterest|TikTok|Snapchat|WhatsApp|Telegram|Discord|WeChat|Signal)\b', '', cleaned_text, flags=re.IGNORECASE)
        # Remove ISBN numbers (e.g., ISBN 978-1234567890, ISBN-13: 978-1-234-56789-0)
        cleaned_text = re.sub(r'ISBN(?:\s*-?\s*\d{1,5}){2,5}[xX]?', '', cleaned_text, flags=re.IGNORECASE)
        # Remove the plural form "ISBNs"
        cleaned_text = re.sub(r'\bISBNs\b', '', cleaned_text, flags=re.IGNORECASE)
        # Remove "Page X" or "P. X" style numbering, case-insensitively
        cleaned_text = re.sub(r'(?i)(?:^|\s)(?:page|p\.)\s*\d+\s*(?:de\s*\d+)?(?:/|\s|$)', '', cleaned_text)
        # Remove page numbers in "page|X" format (e.g., page|1, Page|123)
        cleaned_text = re.sub(r'(?i)(?:^|\s)page\|\s*\d+', '', cleaned_text)
        # Remove lines that likely are just page numbers (contain only digits and whitespace)
        cleaned_text = re.sub(r'^\s*\d+\s*$', '', cleaned_text, flags=re.MULTILINE)
        # Remove header/footer-like patterns (e.g., repeating book titles, chapter names, etc.)
        # This is very context-dependent and hard to do generally with regex.
        # The LLM prompt is better suited for contextual removal of these.
        # For now, we focus on more generic patterns.

        # Normalize multiple newlines to a maximum of two, preserving paragraphs
        cleaned_text = re.sub(r'\n{3,}', '\n\n', cleaned_text).strip()
        # Remove any empty lines that might have resulted from previous cleaning
        cleaned_text = re.sub(r'(\n\s*)+\n', '\n\n', cleaned_text).strip()

        logger.info("  - Text cleaning complete.")
        return cleaned_text

    def _extract_from_pdf(self, pdf_path: Path, extract_images: bool) -> Tuple[str, List[Path]]:
        """
        Extracts text and optionally images from a PDF file.
        """
        extracted_pages: List[str] = []
        image_paths: List[Path] = []
        images_dir = pdf_path.parent / f"images_{pdf_path.stem}"
        doc = fitz.open(pdf_path)

        with doc:
            logger.info(f"  - PDF: Opened '{pdf_path.name}' with {doc.page_count} pages.")
            if doc.is_repaired:
                logger.warning(f"  - PDF: Document was damaged and has been repaired.")

            for page_num, page in enumerate(doc, start=1):
                try:
                    page_text = page.get_text().strip()
                    if page_text:
                        extracted_pages.append(page_text)
                except Exception as e:
                    logger.warning(f"  - PDF: Could not extract text from page {page_num}: {e}")

                if extract_images:
                    image_list = page.get_images(full=True)
                    for img_index, img_info in enumerate(image_list):
                        xref = img_info[0]
                        base_image = doc.extract_image(xref)
                        if not base_image:
                            continue

                        image_bytes = base_image["image"]
                        image_ext = base_image["ext"]
                        image_filename = f"page{page_num}_img{img_index}.{image_ext}"

                        try:
                            images_dir.mkdir(parents=True, exist_ok=True)
                            image_save_path = images_dir / image_filename
                            with open(image_save_path, "wb") as img_file:
                                img_file.write(image_bytes)
                            image_paths.append(image_save_path)
                        except OSError as e:
                            logger.error(f"  - PDF: Could not save image {image_filename}: {e}")

        full_text = "\n\n".join(extracted_pages)
        cleaned_text = self._clean_extracted_text(full_text)
        return cleaned_text, image_paths

    def _extract_from_epub(self, epub_path: Path) -> Tuple[str, List[Path]]:
        """
        Extracts and cleans text from an EPUB file.
        """
        text_sections: List[str] = []
        book = epub.read_epub(epub_path)
        items = list(book.get_items_of_type(ebooklib.ITEM_DOCUMENT))
        logger.info(f"  - EPUB: Found {len(items)} document items in '{epub_path.name}'.")

        for item in items:
            try:
                soup = BeautifulSoup(item.get_body_content(), 'html.parser')
                for tag in self.html_tags_to_remove:
                    for element in soup.find_all(tag):
                        element.decompose()

                raw_text = soup.get_text(separator='\n', strip=True)
                # Clean up whitespace within the section before appending
                cleaned_section = re.sub(r'(\s*\n\s*){2,}', '\n\n', raw_text).strip()
                if cleaned_section:
                    text_sections.append(cleaned_section)
            except Exception as e:
                logger.warning(f"  - EPUB: Could not process item '{item.get_name()}': {e}")

        full_text = "\n\n".join(text_sections)
        cleaned_text = self._clean_extracted_text(full_text)
        # This EPUB implementation does not extract images, so it returns an empty list.
        return cleaned_text, []