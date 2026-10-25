"""
Component 1: image preprocessing.

Takes a raw uploaded photo and prepares it for OCR: grayscale, deskew,
contrast. Also flags photos that are too blurry to trust, using the
variance-of-Laplacian sharpness check (a standard cheap blur detector:
a sharp image has lots of high-frequency edge detail, so its Laplacian
has high variance; a blurry image's edges are smeared out, so the
variance is low).
"""
import cv2
import numpy as np

from app.config import BLUR_VARIANCE_THRESHOLD


def _decode(image_bytes: bytes) -> np.ndarray:
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Could not decode image - unsupported or corrupt file")
    return img


def sharpness_score(gray: np.ndarray) -> float:
    """Variance of the Laplacian. Higher = sharper. ~<100 is usually blurry."""
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def _deskew(gray: np.ndarray) -> np.ndarray:
    """Rotate the image to straighten text lines, using the minimum-area
    bounding box of all dark (text) pixels as a proxy for document angle.

    NOT called from preprocess_image() right now - rotating would move
    OCR bounding boxes out of alignment with the ORIGINAL photo, which
    the frontend displays and draws source-highlight boxes on top of.
    Kept here, unused, as the natural next step for 2.0 (would need the
    frontend to apply the same rotation to the displayed image, or bbox
    coordinates to be mapped back through the inverse rotation)."""
    coords = np.column_stack(np.where(gray < 200))
    if coords.shape[0] < 50:
        return gray  # not enough dark pixels to estimate an angle safely

    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle

    # Small angles are just OCR noise, not real skew - don't rotate for those.
    if abs(angle) < 0.5:
        return gray

    (h, w) = gray.shape
    center = (w // 2, h // 2)
    matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    return cv2.warpAffine(gray, matrix, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)


class ProcessedPage:
    def __init__(self, image: np.ndarray, sharpness: float, blurry: bool):
        self.image = image          # ready for pytesseract
        self.sharpness = sharpness
        self.blurry = blurry


def preprocess_image(image_bytes: bytes) -> ProcessedPage:
    img = _decode(image_bytes)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Measure sharpness before any processing smooths it out.
    score = sharpness_score(gray)
    blurry = score < BLUR_VARIANCE_THRESHOLD

    # Adaptive threshold copes better with uneven lighting/shadows on a
    # photographed (not scanned) page than a single global threshold.
    thresholded = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 15
    )

    return ProcessedPage(image=thresholded, sharpness=score, blurry=blurry)
