import hashlib
import os

import fitz
from exceptiongroup import catch
from supabase import create_client, Client
from tqdm import tqdm

from MongoDB import BookData, PageData
from Tools.SupabaseWraper import SupabaseManager


class FileProcessor:
    # Supabase Configuration
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "http://localhost:8000/")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY",
                                  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.ewogICJyb2xlIjogInNlcnZpY2Vfcm9sZSIsCiAgImlzcyI6ICJzdXBhYmFzZSIsCiAgImlhdCI6IDE3NDIxODc2MDAsCiAgImV4cCI6IDE4OTk5NTQwMDAKfQ.qwjlgmU_2rQj3H7KeillHV49WjuVQzMf5Qr-Up20E0g")

    def __init__(self, root_path: str):
        self._root_path = root_path
        self._db = SupabaseManager(self.SUPABASE_URL, self.SUPABASE_KEY)
        self._files = self._find_files()

    def _find_files(self):
        pdf_files = []
        for root, _, files in os.walk(self._root_path):
            for file in files:
                if file.endswith(".pdf") and "translated_" not in file:
                    pdf_files.append(os.path.join(root, file))
        return sorted(pdf_files)

    def _calculate_hash(self, file: str) -> str:
        with open(file, "rb") as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()
        return file_hash

    def _split_file_path(self, file: str):
        file_name = os.path.splitext(os.path.basename(file))[0]
        file_path = os.path.dirname(file)
        file_hash = self._calculate_hash(file)
        return file_path, file_name, file_hash

    def store_documents(self):
        print(f"Will be processed: {len(self._files)}")
        self._db.truncate_and_reset_index()
        for file in tqdm(self._files, desc="Processing PDF", unit="PDF"):
            file_path, file_name, file_hash = self._split_file_path(file)
            book = BookData(book_name=file_name, file_path=file_path, file_hash=file_hash)
            book_id = self._db.insert_book(book)
            del book
            if book_id is None:
                exit(1)
            doc = fitz.open(file)
            try:
                for page in doc:
                    text = page.get_text()
                    images = len(page.get_images(full=True)) > 0
                    if text.strip():
                        page_content: PageData = PageData()
                        page_content["book_id"] = book_id
                        page_content["content_type"] = "text"
                        page_content["content"] = text.strip().encode("ascii", "ignore").decode("ascii").replace("\x00",
                                                                                                                 "")
                        page_content["content_corrected"] = ""
                        page_content["content_translated"] = ""
                        page_content["corrected"] = False
                        page_content["translated"] = False
                        page_content["validated"] = False
                        page_content["page_number"] = page.number
                        self._db.insert_page(page_content)
                        del page_content
                    if images:
                        image_list = page.get_images(full=True)
                        for xref in image_list:
                            image_info = doc.extract_image(xref[0])
                            page_content: PageData = PageData()
                            page_content["book_id"] = book_id
                            page_content["content_type"] = "image"
                            page_content["content"] = xref[0]
                            page_content["content_corrected"] = ""
                            page_content["content_translated"] = ""
                            page_content["corrected"] = False
                            page_content["translated"] = False
                            page_content["validated"] = False
                            page_content["page_number"] = page.number
                            self._db.insert_page(page_content)
                            del page_content
            except Exception as e:
                print(f"Error processing file {file}: {e}")
            finally:
                doc.close()


if __name__ == "__main__":
    fp = FileProcessor("/Volumes/Elements/Peliculas/.Hide/Thinks/NVL/ENG/")
    fp.store_documents()
