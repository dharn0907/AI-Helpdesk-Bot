
"""Optical character recognition service."""

from ai_models.ocr_model import extract_text


def process_image(image_path: str) -> str:
    """
    Extract text from an uploaded customer complaint image.
    """
    extracted_text = extract_text(image_path)

    return extracted_text
