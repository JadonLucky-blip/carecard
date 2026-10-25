"""
Component 2: OCR.

Runs Tesseract over each preprocessed page and reconstructs numbered
text lines (not just one big blob), because every later pipeline step
needs to cite an exact page + line number back to the source document.
"""
import pytesseract

from app.config import TESSERACT_CMD
from app.pipeline.preprocess import ProcessedPage
from app.schema import OCRDocument, OCRPage, OCRLine, BoundingBox

pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD


def _lines_from_image(image) -> list[tuple[str, BoundingBox]]:
    """Group Tesseract's word-level output into (line text, bbox) pairs,
    using the block/paragraph/line numbers Tesseract already assigns per
    word. The bbox is the union of that line's word boxes, in the pixel
    coordinates of `image` - which is the same size as the original
    uploaded photo (preprocess.py only grayscales/thresholds, never
    resizes or rotates), so the frontend can draw it directly on that photo."""
    data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)

    lines: dict[tuple[int, int, int], list[int]] = {}
    words: dict[tuple[int, int, int], list[str]] = {}
    for i, word in enumerate(data["text"]):
        word = word.strip()
        if not word:
            continue
        key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
        words.setdefault(key, []).append(word)
        left, top = data["left"][i], data["top"][i]
        right, bottom = left + data["width"][i], top + data["height"][i]
        box = lines.setdefault(key, [left, top, right, bottom])
        box[0] = min(box[0], left)
        box[1] = min(box[1], top)
        box[2] = max(box[2], right)
        box[3] = max(box[3], bottom)

    # dict preserves insertion order in Python 3.7+, and Tesseract emits
    # words in reading order, so this is already top-to-bottom.
    result = []
    for key, text_words in words.items():
        x0, y0, x1, y1 = lines[key]
        bbox = BoundingBox(x=x0, y=y0, width=x1 - x0, height=y1 - y0)
        result.append((" ".join(text_words), bbox))
    return result


def run_ocr(pages: list[ProcessedPage]) -> OCRDocument:
    ocr_pages = []
    for page_number, page in enumerate(pages, start=1):
        line_data = _lines_from_image(page.image)
        lines = [
            OCRLine(line_number=i, text=text, bbox=bbox)
            for i, (text, bbox) in enumerate(line_data, start=1)
        ]
        height, width = page.image.shape[:2]
        ocr_pages.append(
            OCRPage(
                page_number=page_number,
                lines=lines,
                width=width,
                height=height,
                blurry=page.blurry,
                sharpness_score=page.sharpness,
            )
        )
    return OCRDocument(pages=ocr_pages)


def ocr_document_to_text(doc: OCRDocument) -> str:
    """Flatten to a 'page N, line M: text' transcript for the LLM prompt -
    this is the exact format the extraction step cites back to."""
    out = []
    for page in doc.pages:
        for line in page.lines:
            out.append(f"[page {page.page_number} line {line.line_number}] {line.text}")
    return "\n".join(out)
