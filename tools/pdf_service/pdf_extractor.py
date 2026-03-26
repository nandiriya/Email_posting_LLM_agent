# pdf_service/pdf_extractor.py

import pdfplumber
import pytesseract
from pdf2image import convert_from_path


def extract_pdf_text(pdf_path: str) -> str:
    """
    Extract text from PDF.
    If PDF is scanned, fallback to OCR.
    """

    text = ""

    # Try normal text extraction first
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"

    # If text is empty, use OCR
    if len(text.strip()) < 50:
        print("[PDF] No text found, running OCR...")
        images = convert_from_path(pdf_path)

        for img in images:
            text += pytesseract.image_to_string(img) + "\n"

    return text.strip()
