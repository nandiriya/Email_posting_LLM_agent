# pdf_service/pdf_cleaner.py

import re


def clean_pdf_text(text: str) -> str:
    """
    Cleans headers, footers, page numbers
    """

    # Remove multiple spaces
    text = re.sub(r"\s+", " ", text)

    # Remove page numbers like "Page 1 of 3"
    text = re.sub(r"page\s+\d+\s+of\s+\d+", "", text, flags=re.IGNORECASE)

    # Remove standalone page numbers
    text = re.sub(r"\n\d+\n", "\n", text)

    return text.strip()

