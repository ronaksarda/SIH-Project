"""OCR client — Tesseract primary with OCR.space fallback. Extracts text + bounding boxes + font size estimation."""

import logging
import os

import httpx
from PIL import Image

logger = logging.getLogger(__name__)


def _get_dpi(image_path: str) -> float:
    """Get image DPI. Default 96 if not embedded."""
    try:
        img = Image.open(image_path)
        dpi_info = img.info.get("dpi")
        if dpi_info and dpi_info[0] > 0:
            return float(dpi_info[0])
    except Exception:
        pass
    return 96.0


def _px_to_mm(px: float, dpi: float) -> float:
    """Convert pixels to millimeters."""
    return (px / dpi) * 25.4


async def ocr_extract(image_path: str) -> dict:
    """Run Tesseract OCR. Falls back to OCR.space on failure. Returns text + font size estimate."""
    result = {
        "raw_text": "",
        "text_blocks": [],
        "estimated_font_height_mm": None,
        "bounding_boxes": [],
        "source": "none",
    }

    dpi = _get_dpi(image_path)

    # Try Tesseract first
    try:
        import pytesseract
        import shutil

        if not shutil.which("tesseract"):
            for standard_path in [
                r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
                os.path.expanduser(r"~\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"),
            ]:
                if os.path.exists(standard_path):
                    pytesseract.pytesseract.tesseract_cmd = standard_path
                    break

        # Get full data with bounding boxes
        data = pytesseract.image_to_data(
            Image.open(image_path),
            output_type=pytesseract.Output.DICT,
            config="--oem 3 --psm 6",
        )

        texts = []
        heights_px = []

        for i, text in enumerate(data["text"]):
            text = text.strip()
            if not text:
                continue
            texts.append(text)
            h = data["height"][i]
            if h > 0:
                heights_px.append(h)
                result["bounding_boxes"].append({
                    "text": text,
                    "x": data["left"][i],
                    "y": data["top"][i],
                    "w": data["width"][i],
                    "h": h,
                    "conf": data["conf"][i],
                })

        result["raw_text"] = " ".join(texts)
        result["text_blocks"] = texts
        result["source"] = "tesseract"

        if heights_px:
            # Use median height for font size estimate (robust to outliers)
            heights_px.sort()
            median_h = heights_px[len(heights_px) // 2]
            result["estimated_font_height_mm"] = round(_px_to_mm(median_h, dpi), 2)

        logger.info("Tesseract OCR succeeded (words=%d)", len(texts))
        return result

    except Exception as e:
        logger.warning("Tesseract failed (%s), trying OCR.space fallback", e)

    # Fallback: OCR.space API (defaults to free demo key 'helloworld' if not set)
    api_key = os.environ.get("OCR_SPACE_KEY") or "helloworld"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            with open(image_path, "rb") as f:
                file_bytes = f.read()

            resp = await client.post(
                "https://api.ocr.space/parse/image",
                files={"file": (os.path.basename(image_path), file_bytes, "image/jpeg")},
                data={"apikey": api_key, "language": "eng", "isOverlayRequired": "true"},
            )

            if resp.status_code != 200 or resp.json().get("IsErroredOnProcessing") or resp.json().get("error"):
                if api_key != "helloworld":
                    logger.warning("OCR.space key '%s' failed, retrying with 'helloworld'", api_key[:6])
                    resp = await client.post(
                        "https://api.ocr.space/parse/image",
                        files={"file": (os.path.basename(image_path), file_bytes, "image/jpeg")},
                        data={"apikey": "helloworld", "language": "eng", "isOverlayRequired": "true"},
                    )

            data = resp.json()
            if data.get("IsErroredOnProcessing") or data.get("error"):
                logger.error("OCR.space error: %s", data.get("ErrorMessage") or data.get("error"))
                return result

            parsed = data.get("ParsedResults", [{}])[0]
            result["raw_text"] = parsed.get("ParsedText", "")
            result["text_blocks"] = [line for line in result["raw_text"].split("\n") if line.strip()]
            result["source"] = "ocr_space"

            # Extract overlay bounding boxes for font size
            overlay = parsed.get("TextOverlay", {})
            heights_px = []
            for line in overlay.get("Lines", []):
                for word in line.get("Words", []):
                    h = word.get("Height", 0)
                    if h > 0:
                        heights_px.append(h)
                        result["bounding_boxes"].append({
                            "text": word.get("WordText", ""),
                            "x": word.get("Left", 0),
                            "y": word.get("Top", 0),
                            "w": word.get("Width", 0),
                            "h": h,
                        })

            if heights_px:
                heights_px.sort()
                median_h = heights_px[len(heights_px) // 2]
                result["estimated_font_height_mm"] = round(_px_to_mm(median_h, dpi), 2)

            logger.info("OCR.space succeeded (words=%d)", len(result["text_blocks"]))

    except Exception as e:
        logger.error("OCR.space fallback failed: %s", e)

    return result

