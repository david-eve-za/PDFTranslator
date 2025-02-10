import logging
import os
import re
from typing import Optional

import ebooklib
import fitz
from bs4 import BeautifulSoup
from ebooklib import epub

# Configure logging
logger = logging.getLogger(__name__)


class TextExtractorAgent:
    def extract_text(self, file_path: str) -> Optional[str]:
        """Extrae texto de un archivo PDF o EPUB."""
        logger.info(f"Extrayendo texto de: {os.path.basename(file_path)}")
        _, extension = os.path.splitext(file_path)
        try:
            if extension.lower() == ".pdf":
                return self._extract_pdf(file_path)
            elif extension.lower() == ".epub":
                return self._extract_epub(file_path)
            else:
                logger.warning(f"Advertencia: Extensión no soportada para {file_path}")
                return None
        except Exception as e:
            logger.error(f"Error al extraer texto de {os.path.basename(file_path)}: {e}")
            return None

    def _extract_pdf(self, file_path: str) -> str:
        text = ""
        try:
            reader = fitz.open(filename=file_path, filetype="pdf")
            logger.info(f"  - PDF: {len(reader)} páginas encontradas.")
            for i, page in enumerate(reader):
                try:
                    page_text = page.get_text()
                    if page_text:
                        text += page_text + "\n"
                except Exception as page_e:
                    logger.warning(f"  - Advertencia: No se pudo extraer texto de la página {i + 1}: {page_e}")
            logger.info(f"  - PDF: Extracción completada.")
        except Exception as e:
            logger.error(f"  - Error inesperado durante extracción de PDF: {e}")
            raise  # Relanza errores inesperados
        return text

    def _extract_epub(self, file_path: str) -> str:
        book = epub.read_epub(file_path)
        text = ""
        items = list(book.get_items_of_type(ebooklib.ITEM_DOCUMENT))
        logger.info(f"  - EPUB: {len(items)} documentos encontrados.")
        for item in items:
            try:
                soup = BeautifulSoup(item.get_body_content(), 'html.parser')
                # Intenta obtener solo el texto visible, excluyendo scripts, styles, etc.
                # Elimina elementos comunes no deseados si existen
                for element_type in ['script', 'style', 'nav', 'footer', 'header']:
                    for element in soup.find_all(element_type):
                        element.decompose()

                # Extrae el texto, intentando preservar párrafos
                raw_text = soup.get_text(separator='\n', strip=True)
                # Limpieza básica adicional (múltiples saltos -> uno solo)
                cleaned_text = re.sub(r'\n\s*\n', '\n', raw_text)
                if cleaned_text:
                    text += cleaned_text + "\n\n"  # Doble salto para separar secciones del EPUB
            except Exception as item_e:
                logger.warning(f"  - Advertencia: No se pudo procesar un item del EPUB ({item.get_name()}): {item_e}")
        logger.info(f"  - EPUB: Extracción completada.")
        return text