"""S13-M5: Compute visual complexity scores for clinical images using Gemini."""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Run from project root: python scripts/compute_visual_complexity.py
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from google import generativeai as genai
except ImportError:
    print("ERROR: google-generativeai package not installed.")
    sys.exit(1)

IMAGES_DIR = PROJECT_ROOT / "assets" / "images"
OUTPUT_FILE = PROJECT_ROOT / "data" / "visual_complexity.json"

# Maps image filename stem to case_id
FILENAME_TO_CASE_ID = {
    "olp_clinical": "olp_001",
    "perio_clinical": "perio_001",
    "herpes_clinical": "herpes_001",
    "behcet_clinical": "behcet_001",
    "syphilis_clinical": "syphilis_001",
    "desquamative_clinical": "desquamative_001",
}

COMPLEXITY_PROMPT = (
    "Rate the visual diagnostic complexity of this clinical dental image on a 0.0–1.0 scale.\n"
    "Consider: visibility of lesion margins, color contrast, image quality, how many differential\n"
    "diagnoses a student would need to consider.\n"
    'Return JSON only: {"complexity": float, "rationale": str}'
)


def score_image(model, image_path: Path) -> dict:
    import PIL.Image
    img = PIL.Image.open(image_path)
    response = model.generate_content([COMPLEXITY_PROMPT, img])
    text = response.text.strip()
    # Strip markdown code fences if present
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])
    return json.loads(text)


def main():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY environment variable is not set.")
        sys.exit(1)

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.0-flash")

    jpeg_files = sorted(IMAGES_DIR.glob("*.jpg")) + sorted(IMAGES_DIR.glob("*.jpeg"))
    if not jpeg_files:
        print(f"No JPEG files found in {IMAGES_DIR}")
        sys.exit(1)

    results = {}
    for image_path in jpeg_files:
        stem = image_path.stem
        case_id = FILENAME_TO_CASE_ID.get(stem)
        if case_id is None:
            print(f"WARNING: No case_id mapping for {image_path.name}, skipping.")
            continue

        print(f"Scoring {image_path.name} → {case_id} ...", end=" ", flush=True)
        try:
            scored = score_image(model, image_path)
            results[case_id] = {
                "gorsel_id": image_path.name,
                "complexity": float(scored["complexity"]),
                "rationale": str(scored["rationale"]),
                "computed_at": datetime.now(timezone.utc).isoformat(),
            }
            print(f"complexity={results[case_id]['complexity']:.3f}")
        except Exception as exc:
            print(f"ERROR: {exc}")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2, ensure_ascii=False)

    print(f"\nWrote {len(results)} entries to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
