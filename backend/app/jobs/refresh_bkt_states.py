"""
BKT State Refresh Job — Sprint 11 T04
======================================
Nightly job that replays all historical graded answers for every active user
and brings MasteryState rows to a consistent, deterministic posterior.

Run with:
    python -m app.jobs.refresh_bkt_states
    python -m app.jobs.refresh_bkt_states --user-id stu_001
    python -m app.jobs.refresh_bkt_states --dry-run
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
import uuid
from datetime import datetime, timezone

from db.database import SessionLocal, User, UserRole

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


def _all_student_ids(db) -> list[str]:
    return [
        u.user_id
        for u in db.query(User)
        .filter(User.role == UserRole.STUDENT, User.is_archived.is_(False))
        .all()
    ]


def run(user_ids: list[str] | None = None, dry_run: bool = False) -> dict:
    from app.services.bkt_service import recompute_for_user

    run_id = str(uuid.uuid4())
    started_at = datetime.now(timezone.utc)
    logger.info(
        json.dumps({
            "job_name": "refresh_bkt_states",
            "run_id": run_id,
            "dry_run": dry_run,
            "started_at": started_at.isoformat(),
        })
    )

    db = SessionLocal()
    try:
        if user_ids is None:
            user_ids = _all_student_ids(db)

        results: dict[str, int] = {}
        for uid in user_ids:
            t0 = time.perf_counter()
            if dry_run:
                logger.info("DRY-RUN: would recompute BKT for user=%s", uid)
                results[uid] = -1
            else:
                topic_map = recompute_for_user(db, uid)
                db.commit()
                results[uid] = len(topic_map)
                elapsed_ms = int((time.perf_counter() - t0) * 1000)
                logger.info(
                    "BKT recomputed: user=%s topics=%d elapsed_ms=%d",
                    uid,
                    len(topic_map),
                    elapsed_ms,
                )

        duration_ms = int((datetime.now(timezone.utc) - started_at).total_seconds() * 1000)
        summary = {
            "job_name": "refresh_bkt_states",
            "run_id": run_id,
            "dry_run": dry_run,
            "users_processed": len(results),
            "duration_ms": duration_ms,
            "outcome": "ok",
        }
        logger.info(json.dumps(summary))
        return summary

    except Exception as exc:
        db.rollback()
        logger.error("refresh_bkt_states FAILED: %s", exc, exc_info=True)
        raise
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Refresh BKT mastery states for all students.")
    parser.add_argument("--user-id", dest="user_id", help="Single user_id to recompute")
    parser.add_argument("--dry-run", action="store_true", help="Print plan without writing")
    args = parser.parse_args()

    user_ids = [args.user_id] if args.user_id else None
    run(user_ids=user_ids, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
