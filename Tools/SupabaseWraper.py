import os
from typing import Any, Dict, List, Optional, TypedDict, Union

from postgrest import APIResponse, SyncRequestBuilder, SyncFilterRequestBuilder, SyncSelectRequestBuilder
from postgrest.types import CountMethod
from supabase import Client, create_client


# --- Data Structures ---

class BookData(TypedDict):
    """
    Represents the data structure for a book.
    """
    id: Optional[int]
    book_name: str
    file_hash: str
    file_path: str


class PageData(TypedDict):
    """
    Represents a single page of a book.
    """
    id: Optional[int]
    book_id: int
    content_type: str  # Literal["text", "image"]
    content: str  # Text content or image data (base64)
    content_corrected: Optional[str]
    content_translated: Optional[str]
    translated: bool
    corrected: bool
    validated: bool
    page_number: int


class GroupedBookData(TypedDict):
    """
    Represents a grouped book.
    """
    id: Optional[int]
    file_path: str
    record_ids: List[int]
    book_names: List[str]


# --- Supabase Manager ---

class SupabaseManager:
    """
    A class for managing CRUD operations on Supabase tables.
    """

    def __init__(self, supabase_url: str, supabase_key: str):
        """
        Initializes the SupabaseManager with a Supabase URL and key.

        Args:
            supabase_url: The Supabase project URL.
            supabase_key: The Supabase service role key.
        """
        self.supabase_url = supabase_url
        self.supabase_key = supabase_key
        self.client: Client = create_client(supabase_url, supabase_key)

    def _get_table(self, table_name: str) -> SyncRequestBuilder:
        """
        Helper function to get a table reference.

        Args:
            table_name: The name of the table.

        Returns:
            A table reference.
        """
        return self.client.table(table_name)

    def _insert(self, table_name: str, data: Union[Dict[str, Any], List[Dict[str, Any]]]) -> Optional[
        Union[int, List[int]]]:
        """
        Inserts data into a table.

        Args:
            table_name: The name of the table.
            data: The data to insert.

        Returns:
            The ID(s) of the inserted row(s), or None if insertion failed.
        """
        response = self._get_table(table_name).insert(data).execute()
        if response.data:
            if isinstance(response.data, list) and len(response.data) > 1:
                return [item["id"] for item in response.data]
            else:
                return response.data[0]['id']
        return None

    def _get(self, table_name: str, item_id: Optional[int] = None, query: Dict[str, Any] = {},
             count: Optional[CountMethod] = None) -> Union[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Retrieves data from a table.

        Args:
            table_name: The name of the table.
            item_id: The ID of the item to retrieve (optional).
            query: The query to filter items (optional).
            count: The method to use to get the count of rows returned.

        Returns:
            The item data, or None if not found.
        """
        select_builder: SyncSelectRequestBuilder = self._get_table(table_name).select("*", count=count)
        filter_builder: SyncFilterRequestBuilder = select_builder.match(query) if query else select_builder
        if item_id:
            response = filter_builder.eq("id", item_id).execute()
        else:
            response = filter_builder.execute()
        if response.data:
            return response.data
        return None

    def _update(self, table_name: str, item_id: int, update_data: Dict[str, Any]) -> int:
        """
        Updates an item in a table.

        Args:
            table_name: The name of the table.
            item_id: The ID of the item to update.
            update_data: The data to update.

        Returns:
            The number of rows modified.
        """
        response: APIResponse = self._get_table(table_name).update(update_data).eq("id", item_id).execute()
        return len(response.data)

    def _delete(self, table_name: str, item_id: int) -> int:
        """
        Deletes an item from a table.

        Args:
            table_name: The name of the table.
            item_id: The ID of the item to delete.

        Returns:
            The number of rows deleted.
        """
        response: APIResponse = self._get_table(table_name).delete().eq("id", item_id).execute()
        return len(response.data)

    # --- Books Table Operations ---

    def insert_book(self, book_data: BookData) -> Optional[int]:
        """
        Inserts a new book into the 'books' table.

        Args:
            book_data: The data of the book to insert.

        Returns:
            The ID of the inserted book, or None if insertion failed.
        """
        return self._insert("books", book_data)

    def get_book(self, book_id: int) -> Optional[BookData]:
        """
        Retrieves a book from the 'books' table by its ID.

        Args:
            book_id: The ID of the book to retrieve.

        Returns:
            The book data, or None if not found.
        """
        result = self._get("books", item_id=book_id)
        return result[0] if result else None

    def get_books(self, query: Dict[str, Any] = {}, count: Optional[CountMethod] = None) -> List[BookData]:
        """
        Retrieves multiple books from the 'books' table based on a query.

        Args:
            query: The query to filter books.
            count: The method to use to get the count of rows returned.

        Returns:
            A list of book data.
        """
        return self._get("books", query=query, count=count)

    def update_book(self, book_id: int, update_data: Dict[str, Any]) -> int:
        """
        Updates a book in the 'books' table.

        Args:
            book_id: The ID of the book to update.
            update_data: The data to update.

        Returns:
            The number of rows modified.
        """
        return self._update("books", book_id, update_data)

    def delete_book(self, book_id: int) -> int:
        """
        Deletes a book from the 'books' table.

        Args:
            book_id: The ID of the book to delete.

        Returns:
            The number of rows deleted.
        """
        return self._delete("books", book_id)

    # --- Pages Table Operations ---

    def insert_page(self, page_data: PageData) -> Optional[int]:
        """
        Inserts a new page into the 'pages' table.

        Args:
            page_data: The data of the page to insert.

        Returns:
            The ID of the inserted page, or None if insertion failed.
        """
        return self._insert("pages", page_data)

    def get_page(self, page_id: int) -> Optional[PageData]:
        """
        Retrieves a page from the 'pages' table by its ID.

        Args:
            page_id: The ID of the page to retrieve.

        Returns:
            The page data, or None if not found.
        """
        result = self._get("pages", item_id=page_id)
        return result[0] if result else None

    def get_pages(self, query: Dict[str, Any] = {}, count: Optional[CountMethod] = None) -> List[PageData]:
        """
        Retrieves multiple pages from the 'pages' table based on a query.

        Args:
            query: The query to filter pages.
            count: The method to use to get the count of rows returned.

        Returns:
            A list of page data.
        """
        return self._get("pages", query=query, count=count)

    def update_page(self, page_id: int, update_data: Dict[str, Any]) -> int:
        """
        Updates a page in the 'pages' table.

        Args:
            page_id: The ID of the page to update.
            update_data: The data to update.

        Returns:
            The number of rows modified.
        """
        return self._update("pages", page_id, update_data)

    def delete_page(self, page_id: int) -> int:
        """
        Deletes a page from the 'pages' table.

        Args:
            page_id: The ID of the page to delete.

        Returns:
            The number of rows deleted.
        """
        return self._delete("pages", page_id)

    # --- Grouped Books Table Operations ---

    def insert_grouped_book(self, grouped_book_data: GroupedBookData) -> Optional[int]:
        """
        Inserts a new grouped book into the 'grouped_books' table.

        Args:
            grouped_book_data: The data of the grouped book to insert.

        Returns:
            The ID of the inserted grouped book, or None if insertion failed.
        """
        return self._insert("grouped_books", grouped_book_data)

    def get_grouped_book(self, grouped_book_id: int) -> Optional[GroupedBookData]:
        """
        Retrieves a grouped book from the 'grouped_books' table by its ID.

        Args:
            grouped_book_id: The ID of the grouped book to retrieve.

        Returns:
            The grouped book data, or None if not found.
        """
        result = self._get("grouped_books", item_id=grouped_book_id)
        return result[0] if result else None

    def get_grouped_books(self, query: Dict[str, Any] = {}, count: Optional[CountMethod] = None) -> List[
        GroupedBookData]:
        """
        Retrieves multiple grouped books from the 'grouped_books' table based on a query.

        Args:
            query: The query to filter grouped books.
            count: The method to use to get the count of rows returned.

        Returns:
            A list of grouped book data.
        """
        return self._get("grouped_books", query=query, count=count)

    def update_grouped_book(self, grouped_book_id: int, update_data: Dict[str, Any]) -> int:
        """
        Updates a grouped book in the 'grouped_books' table.

        Args:
            grouped_book_id: The ID of the grouped book to update.
            update_data: The data to update.

        Returns:
            The number of rows modified.
        """
        return self._update("grouped_books", grouped_book_id, update_data)

    def delete_grouped_book(self, grouped_book_id: int) -> int:
        """
        Deletes a grouped book from the 'grouped_books' table.

        Args:
            grouped_book_id: The ID of the grouped book to delete.

        Returns:
            The number of rows deleted.
        """
        return self._delete("grouped_books", grouped_book_id)

    def truncate_and_reset_index(self):
        try:
            # Truncate table in cascade mode
            truncate_query = f'TRUNCATE TABLE "books" CASCADE;'
            response = self.client.rpc("execute_sql", {"query": truncate_query}).execute()
            print("Tabla truncada con éxito:", response)

            # Reset index from books table to 1
            reset_index_query = f'ALTER SEQUENCE "books_id_seq" RESTART WITH 1;'
            response = self.client.rpc("execute_sql", {"query": reset_index_query}).execute()
            print("Índice reiniciado con éxito:", response)

            # Reset index from pages table to 1
            reset_index_query = f'ALTER SEQUENCE "books_id_seq" RESTART WITH 1;'
            response = self.client.rpc("execute_sql", {"query": reset_index_query}).execute()
            print("Índice reiniciado con éxito:", response)
        except Exception as e:
            print("Error:", e)


# --- Example Usage ---
if __name__ == "__main__":
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "http://localhost:8000/")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY",
                                  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.ewogICJyb2xlIjogInNlcnZpY2Vfcm9sZSIsCiAgImlzcyI6ICJzdXBhYmFzZSIsCiAgImlhdCI6IDE3NDIxODc2MDAsCiAgImV4cCI6IDE4OTk5NTQwMDAKfQ.qwjlgmU_2rQj3H7KeillHV49WjuVQzMf5Qr-Up20E0g")

    manager = SupabaseManager(SUPABASE_URL, SUPABASE_KEY)

    # Example: Insert a book
    new_book: BookData = {
        "id": None,
        "book_name": "Test Book",
        "file_hash": "some_hash",
        "file_path": "/path/to/book",
    }
    book_id = manager.insert_book(new_book)
    print(f"Inserted book with ID: {book_id}")

    # Example: Get the book
    retrieved_book = manager.get_book(book_id)
    print(f"Retrieved book: {retrieved_book}")

    # Example: get all books
    all_books = manager.get_books()
    print(f"All books: {all_books}")

    # Example: Update the book
    updated_rows = manager.update_book(book_id, {"book_name": "Updated Test Book"})
    print(f"Updated {updated_rows} book(s)")

    # Example: Insert a page
    new_page: PageData = {
        "id": None,
        "book_id": book_id,
        "content_type": "text",
        "content": "This is a test page.",
        "content_corrected": None,
        "content_translated": None,
        "translated": False,
        "corrected": False,
        "validated": False,
        "page_number": 1,
    }
    page_id = manager.insert_page(new_page)
    print(f"Inserted page with ID: {page_id}")

    # Example: Get all pages
    all_pages = manager.get_pages()
    print(f"All pages: {all_pages}")

    # Example: Insert a grouped book
    new_grouped_book: GroupedBookData = {
        "id": None,
        "file_path": "/path/to/grouped/book",
        "record_ids": [1, 2, 3],
        "book_names": ["Book 1", "Book 2", "Book 3"],
    }
    grouped_book_id = manager.insert_grouped_book(new_grouped_book)
    print(f"Inserted grouped book with ID: {grouped_book_id}")

    # Example: Get all grouped books
    all_grouped_books = manager.get_grouped_books()
    print(f"All grouped books: {all_grouped_books}")

    # Example: Delete the book
    deleted_rows = manager.delete_book(book_id)
    print(f"Deleted {deleted_rows} book(s)")

    # Example: Delete the page
    deleted_rows = manager.delete_page(page_id)
    print(f"Deleted {deleted_rows} page(s)")

    # Example: Delete the grouped book
    deleted_rows = manager.delete_grouped_book(grouped_book_id)
    print(f"Deleted {deleted_rows} grouped book(s)")
