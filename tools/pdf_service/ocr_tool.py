import pytesseract
from PIL import Image

pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

def extract(image_path: str) -> dict:
    """
    Extract text from image using OCR
    """
    
    print(f"[OCR TOOL] Processing: {image_path}")
    
    img = Image.open(image_path)
    data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
    
    text_parts = []
    confidences = []
    
    for i, conf in enumerate(data['conf']):
        if int(conf) > 0:
            text_parts.append(data['text'][i])
            confidences.append(int(conf))
    
    text = ' '.join(text_parts)
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0
    
    return {
        "text": text,
        "confidence": avg_confidence / 100,
        "method": "tesseract"
    }


if __name__ == "__main__":
    print(extract("code_screenshot.png"))