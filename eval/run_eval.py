"""
Evaluation harness.

For each packet in eval/packets/*.txt (a synthetic discharge document,
already formatted as an OCR transcript - see README for why eval skips
real photo capture) with a matching eval/gold/<name>.json (hand-labeled
expected extraction), runs the real redact -> extract -> ground ->
schedule pipeline and reports precision/recall/hallucination rate per
field, plus the grounding score and parsed schedules.

Run from the project root: python eval/run_eval.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from rapidfuzz import fuzz  # noqa: E402

from app.config import USE_MOCK_EXTRACTION  # noqa: E402
from app.pipeline.extract import extract_card  # noqa: E402
from app.pipeline.grounding import ground_card  # noqa: E402
from app.pipeline.mock_extract import extract_card_mock  # noqa: E402
from app.pipeline.ocr import ocr_document_to_text  # noqa: E402
from app.pipeline.redact import redact_document  # noqa: E402
from app.pipeline.schedule import parse_schedule  # noqa: E402
from app.schema import OCRDocument, OCRPage, OCRLine  # noqa: E402

PACKETS_DIR = Path(__file__).parent / "packets"
GOLD_DIR = Path(__file__).parent / "gold"

MATCH_THRESHOLD = 80  # rapidfuzz token_sort_ratio - below this counts as "not in gold"

# category name -> which field to fuzzy-match on when comparing to gold
CATEGORY_TEXT_KEY = {
    "medications": "name_as_written",
    "return_now_warning_signs": "text",
    "follow_up_appointments": "with",
    "home_care_instructions": "text",
    "activity_and_diet_limits": "text",
}


def parse_transcript(text: str) -> OCRDocument:
    """Reverse of ocr_document_to_text: '[page P line L] text' -> OCRDocument."""
    pages: dict[int, list[OCRLine]] = {}
    for raw_line in text.splitlines():
        raw_line = raw_line.strip()
        if not raw_line.startswith("["):
            continue
        header, _, content = raw_line.partition("]")
        header = header.lstrip("[")
        page_part, line_part = header.split(" line ")
        page_num = int(page_part.replace("page ", "").strip())
        line_num = int(line_part.strip())
        pages.setdefault(page_num, []).append(OCRLine(line_number=line_num, text=content.strip()))
    return OCRDocument(pages=[OCRPage(page_number=p, lines=lines) for p, lines in sorted(pages.items())])


def _item_text(item: dict, key: str) -> str:
    return str(item.get(key) or item.get("text") or "")


def compare_category(extracted: list[dict], gold: list[dict], key: str) -> dict:
    """Greedy best-fuzzy-match between extracted and gold items."""
    matched_gold: set[int] = set()
    true_pos = 0
    for item in extracted:
        item_text = _item_text(item, key)
        best_idx, best_score = None, 0
        for i, g in enumerate(gold):
            if i in matched_gold:
                continue
            score = fuzz.token_sort_ratio(item_text, _item_text(g, key))
            if score > best_score:
                best_idx, best_score = i, score
        if best_idx is not None and best_score >= MATCH_THRESHOLD:
            matched_gold.add(best_idx)
            true_pos += 1

    false_pos = len(extracted) - true_pos
    false_neg = len(gold) - len(matched_gold)
    return {
        "precision": round(true_pos / len(extracted), 2) if extracted else 1.0,
        "recall": round(true_pos / len(gold), 2) if gold else 1.0,
        "hallucination_rate": round(false_pos / len(extracted), 2) if extracted else 0.0,
        "true_pos": true_pos,
        "false_pos": false_pos,
        "false_neg": false_neg,
    }


def run_packet(transcript_path: Path) -> dict:
    name = transcript_path.stem
    gold_path = GOLD_DIR / f"{name}.json"
    if not gold_path.exists():
        raise FileNotFoundError(f"No gold file for packet '{name}' at {gold_path}")

    ocr_doc = parse_transcript(transcript_path.read_text(encoding="utf-8"))
    gold = json.loads(gold_path.read_text(encoding="utf-8"))

    redacted_doc, _pii_mapping = redact_document(ocr_doc)
    transcript = ocr_document_to_text(redacted_doc)
    card = extract_card_mock(transcript) if USE_MOCK_EXTRACTION else extract_card(transcript)
    grounded_card, grounding_score = ground_card(card, ocr_doc)

    results = {"packet": name, "grounding_score": grounding_score}
    for category, key in CATEGORY_TEXT_KEY.items():
        # by_alias=True matters for follow_up_appointments: the Python
        # attribute is `with_` (a reserved word), aliased to "with" - without
        # by_alias the dumped dict has the wrong key and every appointment
        # looks empty to the comparison below.
        extracted_items = [
            item.model_dump(mode="json", by_alias=True) for item in getattr(grounded_card, category)
        ]
        results[category] = compare_category(extracted_items, gold.get(category, []), key)

    results["schedules"] = [
        parse_schedule(med, i).model_dump(mode="json") for i, med in enumerate(grounded_card.medications)
    ]
    return results


def main():
    packet_files = sorted(PACKETS_DIR.glob("*.txt"))
    if not packet_files:
        print(f"No packets found in {PACKETS_DIR}")
        return

    all_results = [run_packet(p) for p in packet_files]

    header = f"{'packet':<24}{'grounding':>10}  " + "  ".join(f"{c:>13}" for c in CATEGORY_TEXT_KEY)
    print(header)
    for r in all_results:
        row = f"{r['packet']:<24}{r['grounding_score']:>9.0f}%  "
        row += "  ".join(f"P{r[c]['precision']:.2f}/R{r[c]['recall']:.2f}" for c in CATEGORY_TEXT_KEY)
        print(row)

    out_path = Path(__file__).parent / "results.json"
    out_path.write_text(json.dumps(all_results, indent=2, default=str), encoding="utf-8")
    print(f"\nFull results written to {out_path}")


if __name__ == "__main__":
    main()
