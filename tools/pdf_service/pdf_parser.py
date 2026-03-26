from typing import Dict, Optional
import os
import pdfplumber
import fitz
from pdf2image import convert_from_path
import tempfile
from tools.pdf_service.ocr_tool import extract

def is_scanned_pdf(pdf_path: str, max_pages: int = 2) -> bool:
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages[:max_pages]:
                text = page.extract_text()
                if text and text.strip():
                    return False
        return True
    except Exception:
        return True


def extract_digital_pdf(pdf_path: str) -> str:
    pdf_len = 0
    text_chunks = []
    with fitz.open(pdf_path) as doc:
        pdf_len = len(doc)
        for page in doc:
            page_text = page.get_text("text")
            if page_text:
                text_chunks.append(page_text)
    return "\n".join(text_chunks), pdf_len


def extract_pdf(pdf_path: str) -> Dict[str, Optional[str]]:
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    # Detect PDF type
    scanned = is_scanned_pdf(pdf_path)
    print(scanned)

    # Digital PDF
    if not scanned:
        text, pdf_len = extract_digital_pdf(pdf_path)
        return {
            "text": text.strip() if text else None,
            "confidence": 1.0 if text else 0.0,
            "pages": pdf_len
        }

    # Scanned PDF → OCR
    images = convert_from_path(pdf_path, dpi=300)

    text_parts = []
    confidences = []

    with tempfile.TemporaryDirectory() as tmpdir:
        for i, img in enumerate(images):
            img_path = os.path.join(tmpdir, f"page_{i}.png")
            img.save(img_path)

            ocr_result = extract(img_path)
            if ocr_result.get("text"):
                text_parts.append(ocr_result["text"])
                confidences.append(ocr_result.get("confidence", 0))

    avg_conf = sum(confidences) / len(confidences) if confidences else 0.0

    return {
        "text": "\n".join(text_parts) if text_parts else None,
        "confidence": avg_conf,
        "source": "OCR"
    }

if __name__ == "__main__":
    print(extract_pdf("D:/IIITD/$ SEM/IP/WebUpdaterAgent_trial/test_pdfs/test.pdf"))