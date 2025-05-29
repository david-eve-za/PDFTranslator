import logging
import re
from pathlib import Path  # Added pathlib
from typing import Optional, Dict, Callable, Any, List, Tuple, Set

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
        self._extraction_methods: Dict[str, Callable[[str], Any]] = {
            PDF_EXTENSION: self._extract_pdf,
            EPUB_EXTENSION: self._extract_epub,
        }

    def extract_text(self, file_path: str) -> Optional[Any]:
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

    def _extract_pdf(self, file_path: str) -> Tuple[str, List[Path]]:
        """
        Extrae texto de un archivo PDF y guarda las imágenes encontradas.
        Primero extrae todo el texto y recolecta XREFs de imágenes.
        Luego, extrae y guarda las imágenes únicas (por XREF).
        Retorna una tupla con el texto extraído y una lista de Paths a las imágenes guardadas.
        """
        extracted_pages_text: List[str] = []
        image_paths: List[Path] = []
        unique_image_xrefs: Set[int] = set()  # Para almacenar XREFs únicos

        pdf_path_obj = Path(file_path)
        file_name = pdf_path_obj.name

        # Crear un directorio para las imágenes basado en el nombre del PDF
        images_dir_created = False
        images_dir = pdf_path_obj.parent / f"images_{pdf_path_obj.stem}"
        try:
            images_dir.mkdir(parents=True, exist_ok=True)
            images_dir_created = True
            logger.info(f"  - PDF ({file_name}): Directorio de imágenes preparado en: {images_dir}")
        except OSError as e:
            logger.error(
                f"  - PDF ({file_name}): No se pudo crear el directorio de imágenes {images_dir}: {e}. Las imágenes no se guardarán."
            )
            # images_dir_created remains False

        try:
            with fitz.open(file_path) as doc:
                logger.info(
                    f"  - PDF ({file_name}): Abierto. {len(doc)} páginas encontradas. Iniciando extracción de texto y recolección de XREFs.")

                # Fase 1: Extracción de texto y recolección de XREFs de imágenes
                for i, page in enumerate(doc):
                    page_num = i + 1

                    # 1.1 Extracción de texto
                    try:
                        page_text = page.get_text().strip()
                        if page_text:
                            extracted_pages_text.append(page_text)
                    except Exception as page_text_e:
                        logger.warning(
                            f"  - PDF ({file_name}): No se pudo extraer texto de la página {page_num}: {page_text_e}")

                    # 1.2 Recolección de XREFs de imágenes
                    try:
                        image_list = page.get_images(full=True)
                        if image_list:
                            logger.debug(
                                f"  - PDF ({file_name}): {len(image_list)} referencias de imágenes encontradas en la página {page_num}.")
                            for img_info in image_list:
                                xref = img_info[0]  # XREF es el primer elemento
                                unique_image_xrefs.add(xref)
                    except Exception as page_image_xref_e:
                        logger.warning(
                            f"  - PDF ({file_name}): Error al obtener XREFs de imágenes de la página {page_num}: {page_image_xref_e}")

                logger.info(
                    f"  - PDF ({file_name}): Extracción de texto y recolección de XREFs completada. {len(unique_image_xrefs)} XREFs de imágenes únicas recolectadas.")

                # Fase 2: Extracción y guardado de imágenes únicas
                if unique_image_xrefs:
                    if images_dir_created:
                        logger.info(
                            f"  - PDF ({file_name}): Iniciando guardado de {len(unique_image_xrefs)} imágenes únicas.")
                        for img_idx, xref in enumerate(unique_image_xrefs):
                            try:
                                base_image = doc.extract_image(xref)
                                if not base_image:
                                    logger.warning(
                                        f"  - PDF ({file_name}): XREF {xref} no corresponde a una imagen o no se pudo extraer.")
                                    continue

                                image_bytes = base_image["image"]
                                image_ext = base_image["ext"]

                                # Construir nombre de archivo para la imagen usando XREF y un índice para unicidad
                                image_filename = f"image_xref_{xref}_idx_{img_idx}.{image_ext}"
                                image_save_path = images_dir / image_filename

                                with open(image_save_path, "wb") as img_file:
                                    img_file.write(image_bytes)
                                image_paths.append(image_save_path)
                                logger.info(
                                    f"  - PDF ({file_name}): Imagen (XREF: {xref}) guardada en {image_save_path}")
                            except IOError as img_io_e:
                                logger.error(
                                    f"  - PDF ({file_name}): No se pudo guardar la imagen con XREF {xref} en {image_save_path}: {img_io_e}")
                            except Exception as img_save_e:
                                logger.error(
                                    f"  - PDF ({file_name}): Error inesperado al procesar/guardar imagen con XREF {xref}: {img_save_e}")
                    else:
                        logger.warning(
                            f"  - PDF ({file_name}): El directorio de imágenes no fue creado, no se guardarán las {len(unique_image_xrefs)} imágenes únicas encontradas."
                        )
                elif len(doc) > 0:  # Only log if there were pages to process
                    logger.info(f"  - PDF ({file_name}): No se encontraron XREFs de imágenes únicas para extraer.")

                logger.info(f"  - PDF ({file_name}): Procesamiento de PDF (texto e imágenes) completado.")
            # 'doc' is automatically closed here by the 'with' statement
        except Exception as e:  # Catch-all for errors during PDF processing (e.g., opening file, or other fitz operations)
            logger.error(f"  - Error general durante extracción de PDF ({file_name}): {e}")
            raise  # Relanza para que sea manejado por extract_text

        return "\n".join(extracted_pages_text), image_paths

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
