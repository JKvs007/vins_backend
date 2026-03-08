import cv2
import pytesseract
import numpy as np
import re


def process_image_for_ocr(image_bytes: bytes) -> str:

    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if img is None:
        return None

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # noise reduction
    blur = cv2.bilateralFilter(gray, 11, 17, 17)

    # edge detection
    edged = cv2.Canny(blur, 30, 200)

    # find contours
    contours, _ = cv2.findContours(
        edged.copy(),
        cv2.RETR_TREE,
        cv2.CHAIN_APPROX_SIMPLE
    )

    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:10]

    plate = None

    for c in contours:

        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.018 * peri, True)

        # plate is usually rectangle
        if len(approx) == 4:
            x, y, w, h = cv2.boundingRect(c)
            plate = gray[y:y + h, x:x + w]
            break

    if plate is None:
        plate = gray

    # threshold plate
    plate = cv2.threshold(
        plate,
        0,
        255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )[1]

    # OCR
    config = "--oem 3 --psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"

    text = pytesseract.image_to_string(plate, config=config)

    cleaned = re.sub(r'[^A-Z0-9]', '', text.upper())

    pattern = r'^[A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{1,4}$'

    if re.match(pattern, cleaned):
        return cleaned

    if 6 <= len(cleaned) <= 10:
        return cleaned

    return None