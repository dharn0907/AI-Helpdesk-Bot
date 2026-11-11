
"""Image API routes."""

import uuid
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException

from services.ocr_service import process_image


router = APIRouter(prefix="/image", tags=["Image Processing"])

UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads"

ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


@router.post("/extract-text")
async def extract_image_text(file: UploadFile = File(...)):

    extension = Path(file.filename or "").suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Unsupported image format. Upload PNG, JPG, JPEG or WEBP."
        )

    if file.content_type and not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="Uploaded file must be an image."
        )

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    image_path = UPLOAD_DIR / f"{uuid.uuid4().hex}{extension}"

    try:
        image_bytes = await file.read()

        if not image_bytes:
            raise HTTPException(
                status_code=400,
                detail="Uploaded image is empty."
            )

        if len(image_bytes) > 10 * 1024 * 1024:
            raise HTTPException(
                status_code=413,
                detail="Image size must not exceed 10 MB."
            )

        image_path.write_bytes(image_bytes)

        extracted_text = process_image(str(image_path))

        return {
            "success": True,
            "filename": file.filename,
            "extracted_text": extracted_text
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"OCR processing failed: {str(e)}"
        )

    finally:
        if image_path.exists():
            image_path.unlink()

        await file.close()
