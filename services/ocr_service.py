import cv2
import pytesseract
import numpy as np
import re

def process_image_for_ocr(image_bytes: bytes) -> str:
    """
    Takes an image in bytes, processes it using OpenCV, runs Tesseract OCR,
    and returns a cleaned valid Indian number plate string if found.
    Improvements:
      - Adaptive preprocessing for better OCR accuracy
      - Bilateral + Gaussian blur for noise reduction
      - Otsu threshold + optional morphological operations
      - Tesseract PSM 7 with alphanumeric whitelist
      - Post-processing to correct common OCR misreads
    """
    try:
        # Convert bytes to numpy array
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            return None

        # Grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Denoise with bilateral filter
        filtered = cv2.bilateralFilter(gray, d=11, sigmaColor=17, sigmaSpace=17)

        # Slight Gaussian blur to smooth remaining noise
        blurred = cv2.GaussianBlur(filtered, (5, 5), 0)

        # Otsu thresholding
        _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # Morphological closing to remove small artifacts
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        morph = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel, iterations=1)

        # Tesseract OCR
        custom_config = (
            r'--oem 3 '
            r'--psm 7 '
            r'-c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
        )
        text = pytesseract.image_to_string(morph, config=custom_config)

        # Uppercase and keep only alphanumeric characters
        cleaned = re.sub(r'[^A-Z0-9]', '', text.upper())

        # Post-processing corrections for common OCR mistakes
        corrections = {
            'O': '0',
            'I': '1',
            'L': '1',
            'S': '5',
            'B': '8',
        }
        corrected = ''.join(corrections.get(c, c) for c in cleaned)

        # Regex validation for Indian number plates
        pattern = r'^[A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{1,4}$'
        if re.match(pattern, corrected):
            return corrected

        # Fallback: return cleaned if reasonable length
        if 6 <= len(corrected) <= 10:
            return corrected

        return None
    except Exception as e:
        print(f"OCR Error: {e}")
        return None