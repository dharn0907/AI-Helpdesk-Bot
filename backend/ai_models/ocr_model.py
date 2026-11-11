
from paddleocr import PaddleOCR
import os

ocr = PaddleOCR(
    lang="en",
    enable_mkldnn=False
)

def extract_text(image_path):

    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")

    results = ocr.predict(input=image_path)

    extracted_text = []

    for result in results:
        data = result.json

        if isinstance(data, dict):
            page_data = data.get("res", data)
            texts = page_data.get("rec_texts", [])
            extracted_text.extend(texts)

    return " ".join(extracted_text)
