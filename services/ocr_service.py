import cv2
import pytesseract
import numpy as np
import re
from typing import Optional


INDIAN_PLATE_PATTERN = re.compile(r"^[A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{1,4}$")


def _clean_plate_text(text: str) -> str:
    text = text.upper()
    text = re.sub(r"[^A-Z0-9]", "", text)
    return text


def _score_candidate(text: str) -> int:
    """
    Higher score = more likely to be a valid Indian number plate candidate.
    """
    if not text:
        return -1

    score = 0

    if INDIAN_PLATE_PATTERN.match(text):
        score += 100

    if 8 <= len(text) <= 10:
        score += 20

    if text[:2].isalpha():
        score += 10

    if any(ch.isdigit() for ch in text):
        score += 10

    return score


def _ocr_variants(plate_img: np.ndarray) -> Optional[str]:
    """
    Run OCR on multiple preprocessed variants and return the best candidate.
    """
    candidates = []

    variants = []

    # Original grayscale
    variants.append(plate_img)

    # Otsu threshold
    _, otsu = cv2.threshold(
        plate_img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )
    variants.append(otsu)

    # Inverted Otsu threshold
    _, inv_otsu = cv2.threshold(
        plate_img, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
    )
    variants.append(inv_otsu)

    # Adaptive threshold
    adaptive = cv2.adaptiveThreshold(
        plate_img,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        11,
    )
    variants.append(adaptive)

    # Slight enlargement helps Tesseract
    processed_variants = []
    for img in variants:
        upscaled = cv2.resize(img, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
        processed_variants.append(upscaled)

    configs = [
        "--oem 3 --psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
        "--oem 3 --psm 8 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
        "--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
    ]

    for img in processed_variants:
        for config in configs:
            text = pytesseract.image_to_string(img, config=config)
            cleaned = _clean_plate_text(text)

            if cleaned:
                candidates.append(cleaned)

    if not candidates:
        return None

    best = max(candidates, key=_score_candidate)

    if _score_candidate(best) < 10:
        return None

    return best


def process_image_for_ocr(image_bytes: bytes) -> Optional[str]:
    """
    Detect probable plate region with OpenCV, then OCR only that region.
    Returns the best candidate plate string or None.
    """
    try:
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            return None

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Denoise while preserving edges
        filtered = cv2.bilateralFilter(gray, 11, 17, 17)

        # Improve local contrast
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(filtered)

        # Edge map for contour detection
        edged = cv2.Canny(enhanced, 50, 200)

        contours, _ = cv2.findContours(
            edged.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE
        )
        contours = sorted(contours, key=cv2.contourArea, reverse=True)[:20]

        candidate_regions = []

        h_img, w_img = gray.shape[:2]

        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)

            if h == 0:
                continue

            aspect_ratio = w / float(h)
            area = w * h

            # Plate-like heuristics
            if 2.0 <= aspect_ratio <= 6.5 and area > 2000:
                if w < w_img * 0.95 and h < h_img * 0.5:
                    roi = gray[y:y + h, x:x + w]
                    candidate_regions.append(roi)

        # Fallback: if no contour candidate found, use central crop-ish fallback
        if not candidate_regions:
            candidate_regions.append(gray)

        results = []

        for roi in candidate_regions[:10]:
            text = _ocr_variants(roi)
            if text:
                results.append(text)

        if not results:
            return None

        best = max(results, key=_score_candidate)

        if INDIAN_PLATE_PATTERN.match(best):
            return best

        if 6 <= len(best) <= 10:
            return best

        return None

    except Exception as e:
        print(f"OCR Error: {e}")
        return None