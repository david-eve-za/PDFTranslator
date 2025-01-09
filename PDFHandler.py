# Clase PDFHandler
import os

import fitz
from tqdm import tqdm


class PDFHandler:
    def __init__(self, input_dir):
        self.input_dir = input_dir

    def find_pdfs(self):
        """Busca de forma recursiva todos los PDFs en el directorio y los ordena por nombre."""
        pdf_files = []
        for root, _, files in os.walk(self.input_dir):
            for file in files:
                if file.endswith(".pdf") and "translated_" not in file:
                    pdf_files.append(os.path.join(root, file))
        return sorted(pdf_files)

    def extract_content(self, pdf_path):
        """
        Analiza el contenido de un PDF para extraer texto e imágenes.
        También genera un registro de metadatos agrupando las páginas por tipo de contenido.
        """
        metadata = []  # Almacena los metadatos agrupados
        content = []  # Contenido extraído de cada página
        current_group = None  # Grupo actual para metadatos

        with (fitz.open(pdf_path) as doc):
            with tqdm(total=len(doc), desc="Processing PDF", unit="page") as pbar:
                for page_number in range(len(doc)):
                    page = doc[page_number]
                    text = page.get_text()
                    images = len(page.get_images(full=True)) > 0

                    if text.strip():  # Página con texto
                        content.append({"text": text, "images": []})
                        page_type = "text"
                    elif images:  # Página con imágenes
                        content.append({"text": "", "images": page.get_images(full=True)})
                        page_type = "image"
                    else:  # Página vacía o sin contenido relevante
                        continue

                    # Agrupar páginas por tipo
                    if not current_group or current_group["type"] != page_type:
                        if current_group:
                            current_group["to"] = page_number - 1
                            current_group["content"] = []
                            current_group["content"].extend(content[:len(content) - 1])
                            del content[:len(content) - 1]
                            metadata.append(current_group)
                        current_group = {"type": page_type, "from": page_number, "to": page_number}
                    else:
                        current_group["to"] = page_number

                    pbar.update(1)

                # Finalizar el último grupo
                if current_group:
                    current_group["content"] = content
                    metadata.append(current_group)

        return metadata
