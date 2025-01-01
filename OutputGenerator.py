# Clase OutputGenerator
import pathlib

import fitz
from pymupdf import Rect
from tqdm import tqdm


class OutputGenerator:
    def __init__(self):
        self.font_path = pathlib.Path(__file__).parent / "fonts/Roboto-Bold.ttf"

    def reconstruct_pdf(self, source_content, translated_content, output_path):
        """Reconstruye el PDF traducido manteniendo la estructura original."""
        doc = fitz.open()
        with fitz.open(source_content) as original_content:
            for page_content in tqdm(translated_content, desc="Processing Translated content", unit="page", leave=False):
                page = doc.new_page()
                # Agregar texto
                if "text" in page_content:
                    page.insert_textbox(page.mediabox + (36, 36, -36, -36),
                                        page_content["text"]
                                        .replace("”", "\"")
                                        .replace("“", "\"")
                                        .replace("’", "'")
                                        .replace("‘", "'")
                                        .replace("—", "-"),
                                        fontsize=11,
                                        border_width=50,
                                        fontfile=self.font_path)
                elif "images" in page_content:
                    # Agregar imágenes (mantener posición original)
                    xref = page_content["images"][0]
                    image = original_content.extract_image(xref)
                    pix = fitz.Pixmap(image["image"])
                    # rect = fitz.Rect(*image["bbox"])
                    page.insert_image(page.mediabox, pixmap=pix)
        doc.save(output_path)
