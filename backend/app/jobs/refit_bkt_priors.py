"""
BKT Prior EM-Fitting Job — Sprint 14 T07
=========================================
Nightly job that re-fits BKT priors (P_INIT, P_TRANSIT, P_SLIP, P_GUESS)
per topic using Expectation-Maximization over accumulated student responses.

Results are persisted in `bkt_topic_priors` (one row per topic). Topics with
insufficient data (below --min-students / --min-obs thresholds) are stored
with is_synthetic=True using global defaults so the table always has a row.

Run with:
    python -m app.jobs.refit_bkt_priors
    python -m app.jobs.refit_bkt_priors --min-students 5 --min-obs 20
    python -m app.jobs.refit_bkt_priors --dry-run
    python -m app.jobs.refit_bkt_priors --max-iter 200 --tol 1e-8
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


def _print_dry_run_table(results: list) -> None:
    print()
    print(
        f"{'topic_id':<30} {'p_init':>8} {'p_transit':>10} {'p_slip':>8} "
        f"{'p_guess':>8} {'students':>9} {'obs':>6} {'converged':>10} {'synthetic':>10}"
    )
    print("-" * 100)
    for r in results:
        print(
            f"{r.topic_id:<30} "
            f"{r.p_init:>8.4f} "
            f"{r.p_transit:>10.4f} "
            f"{r.p_slip:>8.4f} "
            f"{r.p_guess:>8.4f} "
            f"{r.n_students:>9} "
            f"{r.n_observations:>6} "
            f"{'YES' if r.converged else 'NO':>10} "
            f"{'YES' if r.is_synthetic else 'NO':>10}"
        )
    print()
    n_fitted = sum(1 for r in results if not r.is_synthetic)
    n_synthetic = sum(1 for r in results if r.is_synthetic)
    print(
        f"Total: {len(results)} topics | "
        f"EM-fitted: {n_fitted} | "
        f"Synthetic (defaults): {n_synthetic}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Refit BKT priors per topic via EM over student observation sequences."
    )
    parser.add_argument(
        "--min-students",
        type=int,
        default=5,
        help="Minimum distinct students per topic to run EM (default: 5)",
    )
    parser.add_argument(
        "--min-obs",
        type=int,
        default=20,
        help="Minimum total observations per topic to run EM (default: 20)",
    )
    parser.add_argument(
        "--max-iter",
        type=int,
        default=100,
        help="Maximum EM iterations per topic (default: 100)",
    )
    parser.add_argument(
        "--tol",
        type=float,
        default=1e-6,
        help="EM convergence tolerance on log-likelihood delta (default: 1e-6)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute priors but do not write to DB",
    )
    args = parser.parse_args()

    from app.services.bkt_em_service import run_em_fitting
    from db.database import SessionLocal

    db = SessionLocal()
    try:
        summary = run_em_fitting(
            db,
            min_students=args.min_students,
            min_observations=args.min_obs,
            max_iter=args.max_iter,
            tol=args.tol,
            dry_run=args.dry_run,
        )

        if args.dry_run:
            _print_dry_run_table(summary.results)
        else:
            db.commit()

        logger.info(
            json.dumps(
                {
                    "run_id": summary.run_id,
                    "topics_total": summary.n_topics_total,
                    "topics_fitted": summary.n_topics_fitted,
                    "topics_synthetic": summary.n_topics_synthetic,
                    "dry_run": summary.dry_run,
                }
            )
        )

    except Exception as exc:
        db.rollback()
        logger.error("refit_bkt_priors FAILED: %s", exc, exc_info=True)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
