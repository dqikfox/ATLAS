"""OCR tool – extract text from images using pytesseract (or easyocr fallback)."""

from __future__ import annotations

import io
from typing import Any

from ultron.tools import ToolRegistry


def _ocr_pytesseract(image_bytes: bytes) -> str:
    from PIL import Image  # type: ignore
    import pytesseract  # type: ignore

    image = Image.open(io.BytesIO(image_bytes))
    return pytesseract.image_to_string(image)


def _ocr_easyocr(image_bytes: bytes) -> str:
    import easyocr  # type: ignore
    import numpy as np
    from PIL import Image  # type: ignore

    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    reader = easyocr.Reader(["en"], gpu=False)
    results = reader.readtext(np.array(image), detail=0)
    return "\n".join(results)


def _extract_text(image_bytes: bytes) -> str:
    """Try pytesseract first, fall back to easyocr."""
    try:
        return _ocr_pytesseract(image_bytes)
    except Exception:
        pass
    try:
        return _ocr_easyocr(image_bytes)
    except Exception as exc:
        raise RuntimeError(
            "OCR failed. Please install pytesseract (and tesseract-ocr) or easyocr."
        ) from exc


def register_ocr_tools(registry: ToolRegistry) -> None:
    """Register OCR tools into *registry*."""

    @registry.register(
        name="ocr_extract",
        description="Extract text from an image using OCR.",
        parameters={
            "type": "object",
            "required": ["image_data"],
            "properties": {
                "image_data": {
                    "type": "string",
                    "description": "Raw image bytes (passed internally; use the /api/ocr endpoint from the UI).",
                },
            },
        },
    )
    def ocr_extract(image_data: bytes) -> str:
        if isinstance(image_data, str):
            import base64

            image_data = base64.b64decode(image_data)
        return _extract_text(image_data)
