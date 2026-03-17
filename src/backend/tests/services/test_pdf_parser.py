"""Tests for PDF Parser service."""


import pytest
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from app.services.pdf_parser import PDFParser, TextExtractor
from app.services.pdf_parser.extractor import PageContent


@pytest.fixture
def sample_pdf_file(tmp_path):
    """Create a sample PDF for testing."""
    pdf_path = tmp_path / "sample.pdf"
    
    # Create a simple PDF with reportlab
    c = canvas.Canvas(str(pdf_path), pagesize=letter)
    
    # Page 1
    c.drawString(100, 750, "Sample PDF - Page 1")
    c.drawString(100, 700, "This is the first page of the test PDF.")
    c.drawString(100, 650, "It contains some sample text for testing.")
    c.showPage()
    
    # Page 2
    c.drawString(100, 750, "Sample PDF - Page 2")
    c.drawString(100, 700, "This is the second page.")
    c.drawString(100, 650, "Testing multi-page PDF functionality.")
    c.showPage()
    
    # Page 3
    c.drawString(100, 750, "Sample PDF - Page 3")
    c.drawString(100, 700, "Final page with more content.")
    c.showPage()
    
    c.save()
    return pdf_path


class TestPDFParser:
    """Test PDFParser class."""

    def test_parser_initialization(self, sample_pdf_file):
        """Test PDFParser initialization."""
        parser = PDFParser(sample_pdf_file)
        assert parser.file_path == sample_pdf_file
        assert parser.pdf is None
        assert parser.total_pages == 0

    def test_invalid_file_path(self, tmp_path):
        """Test with non-existent file."""
        with pytest.raises(FileNotFoundError):
            PDFParser(tmp_path / "nonexistent.pdf")

    def test_invalid_file_type(self, tmp_path):
        """Test with non-PDF file."""
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("not a pdf")
        
        with pytest.raises(ValueError):
            PDFParser(txt_file)

    def test_open_pdf(self, sample_pdf_file):
        """Test opening a PDF file."""
        parser = PDFParser(sample_pdf_file)
        assert parser.open()
        assert parser.is_open()
        assert parser.total_pages == 3
        parser.close()

    def test_close_pdf(self, sample_pdf_file):
        """Test closing a PDF file."""
        parser = PDFParser(sample_pdf_file)
        parser.open()
        assert parser.is_open()
        parser.close()
        assert not parser.is_open()

    def test_get_page(self, sample_pdf_file):
        """Test getting a specific page."""
        parser = PDFParser(sample_pdf_file)
        parser.open()
        
        page = parser.get_page(1)
        assert page is not None
        
        page = parser.get_page(3)
        assert page is not None
        
        # Invalid page
        page = parser.get_page(10)
        assert page is None
        
        # Negative page
        page = parser.get_page(-1)
        assert page is None
        
        parser.close()

    def test_get_page_range(self, sample_pdf_file):
        """Test getting a range of pages."""
        parser = PDFParser(sample_pdf_file)
        parser.open()
        
        pages = parser.get_page_range(1, 2)
        assert len(pages) == 2
        
        pages = parser.get_page_range(2, 3)
        assert len(pages) == 2
        
        pages = parser.get_page_range(1, 3)
        assert len(pages) == 3
        
        parser.close()

    def test_get_all_pages(self, sample_pdf_file):
        """Test getting all pages."""
        parser = PDFParser(sample_pdf_file)
        parser.open()
        
        pages = parser.get_all_pages()
        assert len(pages) == 3
        
        parser.close()

    def test_context_manager(self, sample_pdf_file):
        """Test using PDF parser as context manager."""
        with PDFParser(sample_pdf_file) as parser:
            assert parser.is_open()
            assert parser.total_pages == 3
        
        assert not parser.is_open()

    def test_get_page_when_closed(self, sample_pdf_file):
        """Test getting page when PDF is closed."""
        parser = PDFParser(sample_pdf_file)
        page = parser.get_page(1)
        assert page is None


class TestTextExtractor:
    """Test TextExtractor class."""

    def test_extract_text(self, sample_pdf_file):
        """Test text extraction from a page."""
        parser = PDFParser(sample_pdf_file)
        parser.open()
        
        page = parser.get_page(1)
        text = TextExtractor.extract_text(page)
        
        assert text is not None
        assert len(text) > 0
        assert "Sample PDF" in text or "Page 1" in text
        
        parser.close()

    def test_extract_text_with_layout(self, sample_pdf_file):
        """Test text extraction with layout preservation."""
        parser = PDFParser(sample_pdf_file)
        parser.open()
        
        page = parser.get_page(1)
        text = TextExtractor.extract_text_with_layout(page)
        
        assert text is not None
        
        parser.close()

    def test_extract_markdown(self, sample_pdf_file):
        """Test markdown extraction."""
        parser = PDFParser(sample_pdf_file)
        parser.open()
        
        page = parser.get_page(1)
        markdown = TextExtractor.extract_markdown(page)
        
        assert markdown is not None
        
        parser.close()

    def test_extract_page_metadata(self, sample_pdf_file):
        """Test page metadata extraction."""
        parser = PDFParser(sample_pdf_file)
        parser.open()
        
        page = parser.get_page(1)
        metadata = TextExtractor.extract_page_metadata(page)
        
        assert "page_number" in metadata
        assert "width" in metadata
        assert "height" in metadata
        assert metadata["page_number"] == 1
        
        parser.close()

    def test_extract_page_content(self, sample_pdf_file):
        """Test complete page content extraction."""
        parser = PDFParser(sample_pdf_file)
        parser.open()
        
        page = parser.get_page(1)
        content = TextExtractor.extract_page_content(page, 1)
        
        assert isinstance(content, PageContent)
        assert content.page_num == 1
        assert content.char_count > 0
        assert content.lines_count > 0
        
        parser.close()

    def test_split_pages(self, sample_pdf_file):
        """Test splitting and extracting multiple pages."""
        parser = PDFParser(sample_pdf_file)
        parser.open()
        
        pages = parser.get_all_pages()
        contents = TextExtractor.split_pages(pages)
        
        assert len(contents) == 3
        assert all(isinstance(v, PageContent) for v in contents.values())
        assert 1 in contents
        assert 2 in contents
        assert 3 in contents
        
        parser.close()

    def test_extract_tables(self, sample_pdf_file):
        """Test table extraction."""
        parser = PDFParser(sample_pdf_file)
        parser.open()
        
        page = parser.get_page(1)
        tables = TextExtractor.extract_tables(page)
        
        # Sample PDF doesn't have tables, so should return empty list
        assert isinstance(tables, list)
        
        parser.close()


class TestIntegration:
    """Integration tests for PDF parsing workflow."""

    def test_full_pdf_processing_workflow(self, sample_pdf_file):
        """Test complete PDF processing workflow."""
        with PDFParser(sample_pdf_file) as parser:
            # Verify PDF is open
            assert parser.is_open()
            
            # Get all pages
            all_pages = parser.get_all_pages()
            assert len(all_pages) == 3
            
            # Extract content from all pages
            contents = TextExtractor.split_pages(all_pages)
            
            # Verify all pages were processed
            assert len(contents) == 3
            
            # Verify content quality
            for page_num, content in contents.items():
                assert content.page_num == page_num
                assert content.char_count > 0

    def test_pdf_page_range_processing(self, sample_pdf_file):
        """Test processing a range of pages."""
        with PDFParser(sample_pdf_file) as parser:
            # Get pages 1-2
            pages = parser.get_page_range(1, 2)
            contents = TextExtractor.split_pages(pages)
            
            assert len(contents) == 2
            assert 1 in contents
            assert 2 in contents

    def test_individual_page_processing(self, sample_pdf_file):
        """Test processing individual pages."""
        with PDFParser(sample_pdf_file) as parser:
            # Process each page individually
            for page_num in range(1, 4):
                page = parser.get_page(page_num)
                content = TextExtractor.extract_page_content(page, page_num)
                
                assert content.page_num == page_num
                assert content.char_count > 0
