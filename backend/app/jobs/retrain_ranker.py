"""
Ranker Retraining Job — Sprint 11 T05
======================================
CLI for the XGBoost learning-to-rank training pipeline.

Run with:
    python -m app.jobs.retrain_ranker
    python -m app.jobs.retrain_ranker --since 180d --algorithm-version v2_hybrid_xgb_irt_bkt
    python -m app.jobs.retrain_ranker --dry-run
    python -m app.jobs.retrain_ranker --seed 42
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Retrain the XGBoost recommendation ranker.")
    parser.add_argument("--since", default="180d", help="Training window (e.g. 180d)")
    parser.add_argument(
        "--algorithm-version",
        default="v2_hybrid_xgb_irt_bkt",
        help="Version string for the model bundle directory and DB row",
    )
    parser.add_argument("--dry-run", action="store_true", help="Compute metrics but do not persist")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    args = parser.parse_args()

    from app.services.recommendation_trainer import InsufficientTrainingData, train
    from db.database import SessionLocal

    db = SessionLocal()
    try:
        result = train(
            db=db,
            since_days=_parse_days(args.since),
            algorithm_version=args.algorithm_version,
            dry_run=args.dry_run,
            seed=args.seed,
        )

        if not args.dry_run:
            db.commit()

        logger.info(json.dumps({k: v for k, v in result.items() if k != "run_id"}))

        if args.dry_run:
            print("\n[DRY RUN] Training metrics (not persisted):")
            print(f"  NDCG@5      : {result.get('ndcg_at_5', 'N/A')}")
            print(f"  Hit-rate@5  : {result.get('hit_rate_at_5', 'N/A')}")
            print(f"  MAP@10      : {result.get('map_at_10', 'N/A')}")
            print(f"  Train rows  : {result.get('training_sample_size', 'N/A')}")
            print(f"  Val rows    : {result.get('validation_sample_size', 'N/A')}")

    except InsufficientTrainingData as exc:
        logger.warning("Insufficient training data: %s", exc)
        print(f"\nWarning: {exc}")
        sys.exit(2)
    except Exception as exc:
        db.rollback()
        logger.error("retrain_ranker FAILED: %s", exc, exc_info=True)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
