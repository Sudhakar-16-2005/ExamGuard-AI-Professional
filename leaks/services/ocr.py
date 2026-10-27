import io
import logging
from pathlib import Path

import pymupdf
from django.conf import settings
from PIL import Image

logger = logging.getLogger(__name__)


def _tesseract(image: Image.Image) -> str:
    import pytesseract

    return pytesseract.image_to_string(image, lang=settings.OCR_LANGUAGES)


def _paddle(image: Image.Image) -> str:
    import numpy as np
    from paddleocr import PaddleOCR

    languages = settings.OCR_LANGUAGES.split("+")
    engine = PaddleOCR(
        use_doc_orientation_classify=True,
        use_doc_unwarping=False,
        use_textline_orientation=True,
        lang=languages[0],
    )
    result = engine.predict(np.asarray(image.convert("RGB")))
    lines = []
    for page in result:
        payload = page.json if hasattr(page, "json") else page
        if callable(payload):
            payload = payload()
        if isinstance(payload, dict):
            data = payload.get("res", payload)
            lines.extend(data.get("rec_texts", []))
    return "\n".join(lines)


def ocr_image(image: Image.Image) -> str:
    engine = settings.OCR_ENGINE.lower()
    if engine in {"auto", "paddle"}:
        try:
            return _paddle(image)
        except (ImportError, RuntimeError, ValueError) as exc:
            if engine == "paddle":
                raise
            logger.info("PaddleOCR unavailable; using Tesseract: %s", exc)
    return _tesseract(image)


def extract_text_from_path(file_path: str) -> str:
    path = Path(file_path)
    suffix = path.suffix.lower()
    if suffix == ".txt":
        return path.read_text(encoding="utf-8", errors="ignore")
    if suffix == ".pdf":
        pages = []
        with pymupdf.open(path) as document:
            for page in document:
                direct = page.get_text("text").strip()
                if len(direct) >= 40:
                    pages.append(direct)
                else:
                    pixmap = page.get_pixmap(matrix=pymupdf.Matrix(2, 2), alpha=False)
                    image = Image.open(io.BytesIO(pixmap.tobytes("png")))
                    pages.append(ocr_image(image))
        return "\n\n".join(pages).strip()
    if suffix in {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}:
        with Image.open(path) as image:
            return ocr_image(image).strip()
    return ""
