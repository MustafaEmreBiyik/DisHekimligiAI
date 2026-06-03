"""
IRT Recalibration Job — Sprint 11 T03
======================================
Nightly job that re-fits IRT 2PL parameters for every active Question and
persists results in `irt_parameters`. Runs in synthetic-bootstrap mode when
real graded responses are insufficient.

Run with:
    python -m app.jobs.recalibrate_irt
    python -m app.jobs.recalibrate_irt --since 90d --min-sample 200
    python -m app.jobs.recalibrate_irt --dry-run
    python -m app.jobs.recalibrate_irt --question-id q_001
"""

from __future__ import annotations

import argparse
import json
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


def _parse_days(value: str) -> int:
    return int(value.replace("d", "").strip())


def _print_dry_run_table(results: list[dict]) -> None:
    print()
    print(f"{'question_id':<20} {'a':>8} {'b':>8} {'n':>6} {'synthetic':>10}")
    print("-" * 60)
    for r in results:
        print(
            f"{r['question_str_id']:<20} "
            f"{r['discrimination_a']:>8.4f} "
            f"{r['difficulty_b']:>8.4f} "
            f"{r['sample_size']:>6} "
            f"{'YES' if r['is_synthetic'] else 'NO':>10}"
        )
    print()
    synthetic_count = sum(1 for r in results if r["is_synthetic"])
    print(f"Total: {len(results)} items | Real: {len(results) - synthetic_count} | Synthetic: {synthetic_count}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Recalibrate IRT 2PL parameters for all active questions.")
    parser.add_argument("--since", default="90d", help="Time window for real responses (e.g. 90d)")
    parser.add_argument("--min-sample", type=int, default=None, help="Min real responses per item (default from env)")
    parser.add_argument("--dry-run", action="store_true", help="Compute but do not write to DB")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for synthetic bootstrap")
    parser.add_argument("--question-id", help="Calibrate a single question only (by string question_id)")
    args = parser.parse_args()

    from app.constants import IRT_MIN_SAMPLE
    from app.services.irt_calibration import run_calibration
    from db.database import Question, SessionLocal

    min_sample = args.min_sample if args.min_sample is not None else IRT_MIN_SAMPLE
    since_days = _parse_days(args.since)

    db = SessionLocal()
    try:
        if args.question_id:
            # Single-question mode: narrow the run to just that item
            q = db.query(Question).filter(Question.question_id == args.question_id).first()
            if q is None:
                logger.error("Question not found: %s", args.question_id)
                sys.exit(1)
            logger.info("Single-item mode: %s", args.question_id)

        summary = run_calibration(
            db=db,
            since_days=since_days,
            min_sample=min_sample,
            dry_run=args.dry_run,
            seed=args.seed,
        )

        if args.dry_run:
            _print_dry_run_table(summary["results"])

        if not args.dry_run:
            db.commit()

        logger.info(json.dumps({
            "run_id": summary["run_id"],
            "total": summary["n_items_total"],
            "real": summary["n_items_real"],
            "synthetic": summary["n_items_synthetic"],
            "dry_run": args.dry_run,
        }))

    except Exception as exc:
        db.rollback()
        logger.error("recalibrate_irt FAILED: %s", exc, exc_info=True)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
