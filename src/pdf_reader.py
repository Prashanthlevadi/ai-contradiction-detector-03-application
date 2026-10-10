"""PDF Text Extraction Module.

Implements byte-stream PDF text extraction using PyMuPDF (fitz) according to
PDF 02 specifications.
"""

from typing import Dict, Any, Tuple
import pymupdf


class PDFExtractionError(Exception):
    """Raised when PDF bytes cannot be parsed or opened."""
    pass


def extract_text(file_bytes: bytes) -> str:
    """Extract raw text from a PDF byte stream.

    Args:
        file_bytes: Raw bytes of the uploaded PDF file.

    Returns:
        Extracted and joined text from all pages in the document.

    Raises:
        PDFExtractionError: If bytes are empty or document is unreadable/corrupted.
    """
    if not file_bytes:
        raise PDFExtractionError("PDF file byte stream is empty.")

    try:
        doc = pymupdf.open(stream=file_bytes, filetype="pdf")
    except Exception as exc:
        raise PDFExtractionError(f"Failed to parse PDF document: {exc}") from exc

    try:
        pages = []
        for page_index in range(len(doc)):
            page = doc[page_index]
            text = page.get_text()
            if text:
                pages.append(text)
        return "\n".join(pages).strip()
    finally:
        doc.close()


def inspect_pdf(file_bytes: bytes) -> Dict[str, Any]:
    """Inspect PDF structure and diagnose OCR/scanned document status.

    Args:
        file_bytes: Raw bytes of the PDF.

    Returns:
        Dictionary containing page_count, char_count, is_empty, is_likely_scanned.
    """
    if not file_bytes:
        return {
            "page_count": 0,
            "char_count": 0,
            "is_empty": True,
            "is_likely_scanned": False,
            "warning": "Empty file provided.",
        }

    try:
        doc = pymupdf.open(stream=file_bytes, filetype="pdf")
    except Exception as exc:
        return {
            "page_count": 0,
            "char_count": 0,
            "is_empty": True,
            "is_likely_scanned": False,
            "warning": f"Corrupt PDF: {exc}",
        }

    try:
        page_count = len(doc)
        total_text = ""
        has_images = False

        for page in doc:
            total_text += page.get_text()
            if len(page.get_images()) > 0:
                has_images = True

        char_count = len(total_text.strip())
        is_likely_scanned = (char_count == 0 and has_images and page_count > 0)

        warning = None
        if char_count == 0:
            if is_likely_scanned:
                warning = "Document contains images with 0 extractable text characters. Scanned/image-only PDFs require an OCR engine."
            else:
                warning = "Document contains no extractable text."

        return {
            "page_count": page_count,
            "char_count": char_count,
            "is_empty": char_count == 0,
            "is_likely_scanned": is_likely_scanned,
            "warning": warning,
        }
    finally:
        doc.close()
