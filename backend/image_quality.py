"""Image quality pre-check — reject blurry/unusable images before sending to AI."""

import logging
from PIL import Image
import numpy as np

logger = logging.getLogger(__name__)

# ponytail: Laplacian variance is the simplest blur detector that works.
# Upgrade to frequency-domain analysis if field accuracy demands it.
BLUR_THRESHOLD = 50.0
MIN_RESOLUTION = (200, 200)


def check_image_quality(image_path: str) -> tuple[bool, str]:
    """Return (is_acceptable, reason). Rejects blurry or tiny images."""
    try:
        img = Image.open(image_path)
    except Exception as e:
        logger.error({"error": str(e)}, "Image open failed")
        return False, f"Cannot open image: {e}"

    w, h = img.size
    if w < MIN_RESOLUTION[0] or h < MIN_RESOLUTION[1]:
        return False, f"Image too small ({w}x{h}). Minimum {MIN_RESOLUTION[0]}x{MIN_RESOLUTION[1]} required."

    # Laplacian variance for blur detection
    gray = img.convert("L")
    arr = np.array(gray, dtype=np.float64)

    # Manual Laplacian kernel convolution (no opencv dependency)
    laplacian = (
        arr[:-2, 1:-1] + arr[2:, 1:-1] + arr[1:-1, :-2] + arr[1:-1, 2:]
        - 4 * arr[1:-1, 1:-1]
    )
    variance = laplacian.var()

    if variance < BLUR_THRESHOLD:
        return False, f"Image appears blurry (sharpness score: {variance:.1f}, minimum: {BLUR_THRESHOLD}). Please upload a clearer photo."

    return True, "OK"
