import cv2
import pytesseract
import numpy as np
import re
import logging
import shutil
from typing import Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Resolve Tesseract path dynamically for macOS/Linux/Render
tesseract_path = shutil.which("tesseract")
if not tesseract_path:
    raise RuntimeError("Tesseract is not installed or not in PATH")

pytesseract.pytesseract.tesseract_cmd = tesseract_path
logger.info(f"Using Tesseract binary at: {tesseract_path}")

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

    if len(text) >= 2 and text[:2].isalpha():
        score += 10

    if any(ch.isdigit() for ch in text):
        score += 10

    return score


def _ocr_variants(plate_img: np.ndarray) -> Optional[str]:
    """
    Run OCR on multiple preprocessed variants and return the best candidate.
    """
    logger.info(f"Processing OCR on image of shape: {plate_img.shape}")
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

    processed_variants = []
    for img in variants:
        upscaled = cv2.resize(
            img, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC
        )
        processed_variants.append(upscaled)

    configs = [
        "--oem 3 --psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
        "--oem 3 --psm 8 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
        "--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
    ]

    logger.info(
        f"Running OCR on {len(processed_variants)} variants with {len(configs)} configs"
    )

    for i, img in enumerate(processed_variants):
        for j, config in enumerate(configs):
            try:
                text = pytesseract.image_to_string(img, config=config)
                cleaned = _clean_plate_text(text)

                logger.info(
                    f"Variant {i}, Config {j} raw OCR: {repr(text)} | cleaned: {cleaned}"
                )

                if cleaned:
                    candidates.append(cleaned)

            except Exception as e:
                logger.warning(f"OCR failed on variant {i}, config {j}: {e}")

    logger.info(f"Found {len(candidates)} candidates: {candidates}")

    if not candidates:
        return None

    best = max(candidates, key=_score_candidate)
    best_score = _score_candidate(best)
    logger.info(f"Best candidate: '{best}' with score {best_score}")

    if best_score < 10:
        logger.warning("Best candidate score too low, rejecting")
        return None

    return best


def process_image_for_ocr(image_bytes: bytes) -> Optional[str]:
    """
    Detect probable plate region with OpenCV, then OCR only that region.
    Returns the best candidate plate string or None.
    """
    try:
        logger.info(f"Starting OCR processing for {len(image_bytes)} bytes")

        try:
            version = pytesseract.get_tesseract_version()
            logger.info(f"Tesseract is available: {version}")
            logger.info(f"Tesseract command path: {pytesseract.pytesseract.tesseract_cmd}")
        except Exception as e:
            logger.error(f"Tesseract not available: {e}")
            return None

        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            logger.error("Failed to decode image")
            return None

        logger.info(f"Image decoded successfully: {img.shape}")
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

        logger.info(f"Found {len(contours)} contours")

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
                    logger.info(
                        f"Added ROI with shape {roi.shape} at ({x},{y},{w},{h}), "
                        f"aspect_ratio={aspect_ratio:.2f}, area={area}"
                    )

        # Fallback: if no contour candidate found, use full grayscale image
        if not candidate_regions:
            logger.warning("No suitable contours found, using full image")
            candidate_regions.append(gray)

        logger.info(f"Processing {len(candidate_regions)} candidate regions")

        results = []

        for i, roi in enumerate(candidate_regions[:10]):
            logger.info(f"Processing region {i}: shape={roi.shape}")
            text = _ocr_variants(roi)
            if text:
                results.append(text)
                logger.info(f"Region {i} produced text: '{text}'")

        if not results:
            logger.warning("No OCR results from any region")
            return None

        best = max(results, key=_score_candidate)
        best_score = _score_candidate(best)

        logger.info(f"Final best result: '{best}' with score {best_score}")

        if INDIAN_PLATE_PATTERN.match(best):
            logger.info("Result matches Indian plate pattern")
            return best

        if 6 <= len(best) <= 10:
            logger.info("Result accepted based on length criteria")
            return best

        logger.warning(f"Result rejected: '{best}' (length: {len(best)})")
        return None

    except Exception as e:
        logger.error(f"OCR processing failed: {e}", exc_info=True)
        return None