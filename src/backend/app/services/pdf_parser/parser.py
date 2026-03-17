"""PDF Parser - Core PDF reading and page management."""

import logging
from pathlib import Path

import pdfplumber

logger = logging.getLogger(__name__)


class PDFParser:
    """Main PDF parser class for reading and managing PDF documents."""

    def __init__(self, file_path: str | Path):
        """Initialize PDF parser with file path.
        
        Args:
            file_path: Path to the PDF file
            
        Raises:
            FileNotFoundError: If PDF file doesn't exist
            ValueError: If file is not a valid PDF
        """
        self.file_path = Path(file_path)
        self._validate_file()
        self.pdf = None
        self.total_pages = 0

    def _validate_file(self) -> None:
        """Validate that file exists and is a PDF."""
        if not self.file_path.exists():
            raise FileNotFoundError(f"PDF file not found: {self.file_path}")
        if self.file_path.suffix.lower() != ".pdf":
            raise ValueError(f"File must be a PDF: {self.file_path}")

    def open(self) -> bool:
        """Open the PDF file.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.pdf = pdfplumber.open(str(self.file_path))
            self.total_pages = len(self.pdf.pages)
            logger.info(f"Opened PDF: {self.file_path.name} ({self.total_pages} pages)")
            return True
        except Exception as e:
            logger.error(f"Failed to open PDF: {e}")
            return False

    def close(self) -> None:
        """Close the PDF file."""
        if self.pdf is not None:
            self.pdf.close()
            self.pdf = None
            logger.info(f"Closed PDF: {self.file_path.name}")

    def is_open(self) -> bool:
        """Check if PDF is currently open."""
        return self.pdf is not None

    def get_page(self, page_num: int) -> object | None:
        """Get a specific page from the PDF.
        
        Args:
            page_num: 1-indexed page number
            
        Returns:
            Page object or None if page doesn't exist
        """
        if self.pdf is None:
            logger.warning("PDF not open")
            return None

        if page_num < 1 or page_num > self.total_pages:
            logger.warning(f"Invalid page number: {page_num}")
            return None

        return self.pdf.pages[page_num - 1]

    def get_page_range(self, start_page: int, end_page: int) -> list:
        """Get a range of pages.
        
        Args:
            start_page: 1-indexed start page
            end_page: 1-indexed end page (inclusive)
            
        Returns:
            List of page objects
        """
        if self.pdf is None:
            logger.warning("PDF not open")
            return []

        start_page = max(1, start_page)
        end_page = min(self.total_pages, end_page)

        if start_page > end_page:
            return []

        return self.pdf.pages[start_page - 1 : end_page]

    def get_all_pages(self) -> list:
        """Get all pages from the PDF.
        
        Returns:
            List of all page objects
        """
        if self.pdf is None:
            logger.warning("PDF not open")
            return []

        return self.pdf.pages

    def __enter__(self):
        """Context manager entry."""
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
