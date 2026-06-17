"""S13-M5: Seed visual_complexity_score into CaseDefinition rows from computed JSON."""

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from db.database import SessionLocal, CaseDefinition  # noqa: E402

INPUT_FILE = PROJECT_ROOT / "data" / "visual_complexity.json"


def main():
    if not INPUT_FILE.exists():
        print(f"ERROR: {INPUT_FILE} not found. Run compute_visual_complexity.py first.")
        sys.exit(1)

    with open(INPUT_FILE, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    db = SessionLocal()
    try:
        updated = 0
        not_found = []

        for case_id, payload in data.items():
            row = db.query(CaseDefinition).filter(CaseDefinition.case_id == case_id).first()
            if row is None:
                not_found.append(case_id)
                continue
            row.visual_complexity_score = payload["complexity"]
            updated += 1

        db.commit()

        print(f"Updated {updated} CaseDefinition rows.")
        if not_found:
            for cid in not_found:
                print(f"NOT FOUND in DB: {cid}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
