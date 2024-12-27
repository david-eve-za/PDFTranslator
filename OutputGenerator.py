# Clase OutputGenerator
import fitz


class OutputGenerator:
    def __init__(self):
        pass

    def reconstruct_pdf(self, original_content, translated_content, output_path):
        """Reconstruye el PDF traducido manteniendo la estructura original."""
        doc = fitz.open()
        for page_content in translated_content:
            page = doc.new_page()
            # Agregar texto
            if "text" in page_content:
                page.insert_text((72, 72), page_content["text"], fontsize=12)
            # Agregar imágenes (mantener posición original)
            for img in page_content.get("images", []):
                xref = img["xref"]
                pix = fitz.Pixmap(original_content.extract_image(xref)["image"])
                rect = fitz.Rect(*img["bbox"])
                page.insert_image(rect, pixmap=pix)
        doc.save(output_path)
