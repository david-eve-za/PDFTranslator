# Clase PDFHandler
import os

import fitz


class PDFHandler:
    def __init__(self, input_dir):
        self.input_dir = input_dir

    def find_pdfs(self):
        """Busca de forma recursiva todos los PDFs en el directorio y los ordena por nombre."""
        pdf_files = []
        for root, _, files in os.walk(self.input_dir):
            for file in files:
                if file.endswith(".pdf"):
                    pdf_files.append(os.path.join(root, file))
        return sorted(pdf_files)

    def extract_content(self, pdf_path):
        """Extrae texto e imágenes del PDF manteniendo la estructura."""
        document = fitz.open(pdf_path)
        pages_content = []
        for page_num in range(len(document)):
            page = document[page_num]
            text = page.get_text()
            images = page.get_images(full=True)
            pages_content.append({"page_num": page_num, "text": text, "images": images})
        return pages_content