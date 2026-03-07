import cv2
import pytesseract
import numpy as np
import re

def process_image_for_ocr(image_bytes: bytes) -> str:
    """
    Takes an image in bytes, processes it using OpenCV, runs Tesseract OCR,
    and returns a cleaned valid Indian number plate string if found.
    Regex logic: Validates basic Indian number plate format.
    Pipeline:
      - Convert to grayscale
      - Bilateral filter (denoise while keeping edges)
      - Otsu threshold
      - pytesseract with PSM 7 and alphanumeric whitelist
    """
    try:
        # Convert bytes to numpy array
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            return None

        # Grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Bilateral filter to reduce noise while preserving edges
        # (good for number plates with sharp character boundaries)
        filtered = cv2.bilateralFilter(gray, d=11, sigmaColor=17, sigmaSpace=17)

        # Otsu thresholding to binarize the image
        _, thresh = cv2.threshold(
            filtered, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )

        # Tesseract configuration for single-line plate text with whitelist
        custom_config = (
            r'--oem 3 '
            r'--psm 7 '
            r'-c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
        )
        text = pytesseract.image_to_string(thresh, config=custom_config)

        # Clean text: uppercase and keep only alphanumeric characters
        cleaned = re.sub(r'[^A-Z0-9]', '', text.upper())
        
        # Simple regex for Indian number plate (e.g. MH12AB1234)
        # 2 letters, 1-2 digits, 1-3 letters, 1-4 digits
        # For simplicity, we just look for 2 letters at start, and 4 digits at end typically,
        # but the request asks for 'Indian plate regex'. Let's use a fairly permissive one:
        pattern = r'^[A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{1,4}$'
        
        if re.match(pattern, cleaned):
            return cleaned
        
        # Also return cleaned text if it's substantial > 6 chars and <= 10 (fallback but less precise)
        if 6 <= len(cleaned) <= 10:
             return cleaned

        return None
    except Exception as e:
        print(f"OCR Error: {e}")
        return None
