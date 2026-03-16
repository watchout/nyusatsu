"""Text Extraction - PDF text and metadata extraction."""

import logging
from typing import Optional, Dict, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PageContent:
    """Container for extracted page content."""
    page_num: int
    text: str
    markdown: str
    char_count: int
    lines_count: int


class TextExtractor:
    """Extract text and structured data from PDF pages."""

    @staticmethod
    def extract_text(page) -> str:
        """Extract raw text from a page.
        
        Args:
            page: pdfplumber page object
            
        Returns:
            Extracted text string
        """
        try:
            text = page.extract_text()
            return text if text else ""
        except Exception as e:
            logger.error(f"Failed to extract text from page: {e}")
            return ""

    @staticmethod
    def extract_text_with_layout(page) -> str:
        """Extract text preserving layout.
        
        Args:
            page: pdfplumber page object
            
        Returns:
            Text with preserved layout
        """
        try:
            text = page.extract_text(layout=True)
            return text if text else ""
        except Exception as e:
            logger.error(f"Failed to extract layout text: {e}")
            return ""

    @staticmethod
    def extract_markdown(page) -> str:
        """Extract text in markdown format (if available).
        
        Args:
            page: pdfplumber page object
            
        Returns:
            Markdown formatted text
        """
        try:
            # pdfplumber supports markdown extraction in newer versions
            if hasattr(page, 'extract_text_with_markdown'):
                return page.extract_text_with_markdown()
            else:
                # Fallback to regular text
                return TextExtractor.extract_text(page)
        except Exception as e:
            logger.error(f"Failed to extract markdown: {e}")
            return ""

    @staticmethod
    def extract_tables(page) -> List[List[List[str]]]:
        """Extract tables from a page.
        
        Args:
            page: pdfplumber page object
            
        Returns:
            List of tables (each table is list of rows)
        """
        try:
            tables = page.extract_tables()
            return tables if tables else []
        except Exception as e:
            logger.error(f"Failed to extract tables: {e}")
            return []

    @staticmethod
    def extract_page_metadata(page) -> Dict:
        """Extract metadata from a page.
        
        Args:
            page: pdfplumber page object
            
        Returns:
            Dictionary of page metadata
        """
        try:
            return {
                "page_number": page.page_number,
                "width": page.width,
                "height": page.height,
                "rotation": page.rotation,
            }
        except Exception as e:
            logger.error(f"Failed to extract page metadata: {e}")
            return {}

    @staticmethod
    def extract_page_content(page, page_num: int) -> PageContent:
        """Extract complete page content.
        
        Args:
            page: pdfplumber page object
            page_num: Page number for reference
            
        Returns:
            PageContent dataclass with all extracted data
        """
        text = TextExtractor.extract_text(page)
        markdown = TextExtractor.extract_markdown(page)
        
        return PageContent(
            page_num=page_num,
            text=text,
            markdown=markdown,
            char_count=len(text),
            lines_count=len(text.split('\n')) if text else 0,
        )

    @staticmethod
    def split_pages(pages: list) -> Dict[int, PageContent]:
        """Split and extract content from multiple pages.
        
        Args:
            pages: List of pdfplumber page objects
            
        Returns:
            Dictionary mapping page numbers to PageContent
        """
        result = {}
        for idx, page in enumerate(pages, 1):
            try:
                result[idx] = TextExtractor.extract_page_content(page, idx)
            except Exception as e:
                logger.error(f"Failed to process page {idx}: {e}")
                continue
        
        return result
