# Clase OutputGenerator
import io
import pathlib

import PIL
import fitz
from PIL.Image import Image
from tqdm import tqdm


class OutputGenerator:
    def __init__(self):
        self.font_path = pathlib.Path(__file__).parent / "fonts/Roboto-Bold.ttf"

    def reconstruct_pdf(self, source_content, translated_content, output_path):
        """Reconstruye el PDF traducido manteniendo la estructura original."""
        doc = fitz.open()
        with fitz.open(source_content) as original_content:
            for page_content in tqdm(translated_content, desc="Processing Translated content", unit="page",
                                     leave=False):
                page = doc.new_page()
                # Agregar texto
                if "text" in page_content:
                    page.insert_htmlbox(page.mediabox + (36, 36, -36, -36),
                                        page_content["text"]
                                        .replace("”", "\"")
                                        .replace("“", "\"")
                                        .replace("’", "'")
                                        .replace("‘", "'")
                                        .replace("—", "-")
                                        .replace("\n", "<br>")
                                        # fontsize=11,
                                        # border_width=50,
                                        # archive=self.font_path
                                        )
                elif "images" in page_content:
                    # Agregar imágenes (mantener posición original)
                    xref = page_content["images"][0]
                    image = original_content.extract_image(xref)
                    image_stream = self.compress_image(image)
                    # rect = fitz.Rect(*image["bbox"])
                    page.insert_image(page.mediabox, stream=image_stream)
        doc.save(output_path, deflate=True, deflate_images=True)

    def compress_image(self, image):
        pixmap = fitz.Pixmap(image["image"])
        # Convert Pixmap to PIL Image
        buffer = io.BytesIO()
        img = pixmap.pil_save(buffer,"JPEG", quality=20)
        return buffer.getvalue()
