"""
Recommendation Evaluation Job — Sprint 11 T07
==============================================
CLI for the offline evaluation harness. Compares v1 vs v2 algorithms on
historical recommendation snapshots and prints a Markdown report.

Run with:
    python -m app.jobs.evaluate_recommendations
    python -m app.jobs.evaluate_recommendations --window 90d
    python -m app.jobs.evaluate_recommendations --window 60d --report docs/reports/sprint11_eval.md
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


def _parse_days(value: str) -> int:
    return int(value.replace("d", "").strip())


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Offline evaluation harness for v1 vs v2 recommendation algorithms."
    )
    parser.add_argument(
        "--window",
        default="60d",
        help="Evaluation window in days (e.g. 60d). The last 14 days are excluded as label lag.",
    )
    parser.add_argument(
        "--report",
        default=None,
        metavar="PATH",
        help="Write the Markdown report to PATH in addition to printing it.",
    )
    args = parser.parse_args()

    from app.services.recommendation_evaluator import evaluate, generate_report
    from db.database import SessionLocal

    window_days = _parse_days(args.window)
    logger.info("Starting recommendation evaluation: window=%dd", window_days)

    db = SessionLocal()
    try:
        result = evaluate(db, window_days=window_days)
    except Exception as exc:
        logger.error("Evaluation failed: %s", exc, exc_info=True)
        db.close()
        sys.exit(1)
    finally:
        db.close()

    report = generate_report(result)
    print(report)

    if args.report:
        out_path = Path(args.report)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(report, encoding="utf-8")
        logger.info("Report written to %s", out_path)

    verdict = result.get("verdict", "DO NOT PROMOTE")
    if verdict == "PROMOTE":
        logger.info("Verdict: PROMOTE — v2 meets all offline promotion gates.")
        sys.exit(0)
    else:
        logger.info("Verdict: DO NOT PROMOTE — one or more gates failed.")
        sys.exit(2)


if __name__ == "__main__":
    main()
