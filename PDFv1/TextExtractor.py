import logging
import re
from pathlib import Path  # Added pathlib
from typing import Optional, Dict, Callable

import ebooklib
import fitz  # PyMuPDF
from bs4 import BeautifulSoup
from ebooklib import epub

# Configure logging
logger = logging.getLogger(__name__)

# Define constants for better readability and maintainability
PDF_EXTENSION = ".pdf"
EPUB_EXTENSION = ".epub"

# For _extract_epub: HTML tags to remove
HTML_TAGS_TO_REMOVE = ['script', 'style', 'nav', 'footer', 'header']


class TextExtractorAgent:
    def __init__(self):
        """Inicializa el agente extractor de texto."""
        self._extraction_methods: Dict[str, Callable[[str], str]] = {
            PDF_EXTENSION: self._extract_pdf,
            EPUB_EXTENSION: self._extract_epub,
        }

    def extract_text(self, file_path: str) -> Optional[str]:
        """
        Extrae texto de un archivo PDF o EPUB.
        Devuelve el texto extraído o None si la extensión no es soportada o ocurre un error.
        """
        path_obj = Path(file_path)
        file_name = path_obj.name
        extension = path_obj.suffix.lower()

        logger.info(f"Extrayendo texto de: {file_name}")

        extraction_method = self._extraction_methods.get(extension)

        if extraction_method:
            try:
                return extraction_method(file_path)
            except Exception as e:
                # Log detallado del error específico de extracción
                logger.error(f"Error al procesar el archivo {file_name} con el método para {extension}: {e}")
                return None
        else:
            logger.warning(f"Advertencia: Extensión '{extension}' no soportada para el archivo {file_name}")
            return None

    def _extract_pdf(self, file_path: str) -> str:
        """Extrae texto de un archivo PDF."""
        extracted_pages_text = []
        file_name = Path(file_path).name  # Para logs más claros

        try:
            # Usar 'with' asegura que el documento se cierre automáticamente
            with fitz.open(file_path) as doc:
                logger.info(f"  - PDF ({file_name}): {len(doc)} páginas encontradas.")
                for i, page in enumerate(doc):
                    try:
                        page_text = page.get_text().strip()  # Obtener texto y quitar espacios extra
                        if page_text:  # Solo añadir si hay contenido
                            extracted_pages_text.append(page_text)
                    except Exception as page_e:
                        logger.warning(
                            f"  - PDF ({file_name}): No se pudo extraer texto de la página {i + 1}: {page_e}")
                logger.info(f"  - PDF ({file_name}): Extracción completada.")
        except Exception as e:
            logger.error(f"  - Error inesperado durante extracción de PDF ({file_name}): {e}")
            raise  # Relanza para que sea manejado por extract_text

        # Unir el texto de todas las páginas con un solo salto de línea entre ellas
        return "\n".join(extracted_pages_text)

    def _extract_epub(self, file_path: str) -> str:
        """Extrae texto de un archivo EPUB."""
        text_sections = []
        file_name = Path(file_path).name  # Para logs más claros

        try:
            book = epub.read_epub(file_path)
            items = list(book.get_items_of_type(ebooklib.ITEM_DOCUMENT))
            logger.info(f"  - EPUB ({file_name}): {len(items)} documentos encontrados.")

            for item in items:
                try:
                    soup = BeautifulSoup(item.get_body_content(), 'html.parser')

                    # Eliminar elementos no deseados
                    for tag_name in HTML_TAGS_TO_REMOVE:
                        for element in soup.find_all(tag_name):
                            element.decompose()

                    # Extraer texto, intentando preservar párrafos con un solo \n
                    raw_text = soup.get_text(separator='\n', strip=True)

                    # Limpieza: colapsar múltiples saltos de línea (y espacios entre ellos) a un solo \n
                    # Luego, quitar espacios al inicio/final del bloque de texto del item.
                    cleaned_text = re.sub(r'(\s*\n\s*){2,}', '\n', raw_text).strip()

                    if cleaned_text:
                        text_sections.append(cleaned_text)
                except Exception as item_e:
                    logger.warning(
                        f"  - EPUB ({file_name}): No se pudo procesar un item ({item.get_name()}): {item_e}"
                    )
            logger.info(f"  - EPUB ({file_name}): Extracción completada.")
        except ebooklib.epub.EpubException as epub_e:  # Captura específica para errores de lectura de EPUB
            logger.error(f"  - Error al leer el archivo EPUB ({file_name}): {epub_e}")
            raise  # Relanza para que sea manejado por extract_text
        except Exception as e:  # Otros errores inesperados
            logger.error(f"  - Error inesperado durante extracción de EPUB ({file_name}): {e}")
            raise  # Relanza para que sea manejado por extract_text

        # Unir las secciones de texto con dos saltos de línea para separarlas claramente
        return "\n\n".join(text_sections)
