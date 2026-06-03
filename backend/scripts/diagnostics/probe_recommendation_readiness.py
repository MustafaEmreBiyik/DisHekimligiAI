"""Sprint 11 T01 — Data-readiness probe for IRT and BKT.

Runs the gate-condition queries from SPRINT11_RECOMMENDATION_IRT_XGBOOST.md
section 1.1 against a target SQLite DB and prints a structured summary that
can be pasted into SPRINT11_DATA_READINESS_REPORT.md.

Usage:
    python -m scripts.diagnostics.probe_recommendation_readiness [db_path]

If db_path is omitted, falls back to the DATABASE_URL-resolved path.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path
from typing import Any


MIN_IRT_SAMPLE = 200
MIN_BKT_SEQUENCE = 20


def _existing_tables(conn: sqlite3.Connection) -> set[str]:
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    return {row[0] for row in cur.fetchall()}


def _table_count(conn: sqlite3.Connection, table: str) -> int:
    cur = conn.cursor()
    cur.execute(f"SELECT COUNT(*) FROM {table}")
    return int(cur.fetchone()[0])


def _irt_readiness(conn: sqlite3.Connection) -> dict[str, Any]:
    cur = conn.cursor()
    cur.execute(
        """
        SELECT q.question_id, COUNT(a.id) AS responses
        FROM questions q
        LEFT JOIN quiz_answers a
          ON a.question_id = q.id
         AND a.grading_status IN ('GRADED', 'PUBLISHED')
        GROUP BY q.question_id
        """
    )
    rows = cur.fetchall()
    total_questions = len(rows)
    ready = [r for r in rows if r[1] >= MIN_IRT_SAMPLE]
    sample_distribution = Counter()
    for _qid, n in rows:
        if n == 0:
            sample_distribution["0"] += 1
        elif n < 50:
            sample_distribution["1-49"] += 1
        elif n < 200:
            sample_distribution["50-199"] += 1
        elif n < 500:
            sample_distribution["200-499"] += 1
        else:
            sample_distribution["500+"] += 1

    return {
        "total_questions": total_questions,
        "questions_meeting_min_sample": len(ready),
        "fraction_ready": round(len(ready) / total_questions, 3) if total_questions else 0.0,
        "sample_size_distribution": dict(sample_distribution),
        "min_sample_threshold": MIN_IRT_SAMPLE,
        "top10_sample_sizes": sorted([r[1] for r in rows], reverse=True)[:10],
    }


def _bkt_readiness(conn: sqlite3.Connection) -> dict[str, Any]:
    cur = conn.cursor()
    cur.execute(
        """
        SELECT qa.user_id, q.topic_id, COUNT(*) AS answers
        FROM quiz_attempts qa
        JOIN quiz_answers ans ON ans.attempt_id = qa.id
        JOIN questions q ON q.id = ans.question_id
        GROUP BY qa.user_id, q.topic_id
        """
    )
    rows = cur.fetchall()
    total_pairs = len(rows)
    ready_pairs = sum(1 for r in rows if r[2] >= MIN_BKT_SEQUENCE)
    unique_users = len({r[0] for r in rows})
    unique_topics = len({r[1] for r in rows})

    return {
        "total_user_topic_pairs": total_pairs,
        "unique_users": unique_users,
        "unique_topics": unique_topics,
        "pairs_meeting_min_sequence": ready_pairs,
        "fraction_ready": round(ready_pairs / total_pairs, 3) if total_pairs else 0.0,
        "min_sequence_threshold": MIN_BKT_SEQUENCE,
        "top10_sequence_lengths": sorted([r[2] for r in rows], reverse=True)[:10],
    }


def _decision(irt: dict[str, Any], bkt: dict[str, Any]) -> dict[str, str]:
    irt_fraction = irt["fraction_ready"]
    if irt_fraction >= 0.60:
        irt_branch = "full_calibration"
    elif irt_fraction >= 0.20:
        irt_branch = "partial_calibration_well_sampled_subset"
    else:
        irt_branch = "synthetic_bootstrap_required"

    if bkt["fraction_ready"] >= 0.50:
        bkt_branch = "full_confidence_mode"
    else:
        bkt_branch = "low_confidence_fallback_to_v1_weighted"

    return {"irt_branch": irt_branch, "bkt_branch": bkt_branch}


def main(db_path: str | None = None) -> int:
    if db_path is None:
        backend_root = Path(__file__).resolve().parents[2]
        project_root = backend_root.parent
        db_path = str(project_root / "db" / "runtime" / "dentai_app.db")

    if not Path(db_path).exists():
        print(json.dumps({"error": f"db not found at {db_path}", "decision": "no_data_run_synthetic_bootstrap"}, indent=2))
        return 1

    conn = sqlite3.connect(db_path)
    try:
        tables = _existing_tables(conn)
        required = {"questions", "quiz_answers", "quiz_attempts"}
        missing = required - tables
        if missing:
            print(json.dumps({
                "db_path": db_path,
                "tables_present": sorted(tables),
                "tables_missing": sorted(missing),
                "decision": "schema_incomplete_run_alembic_upgrade_first",
            }, indent=2))
            return 1

        report = {
            "db_path": db_path,
            "tables_present_count": len(tables),
            "row_counts": {
                "questions": _table_count(conn, "questions"),
                "quiz_attempts": _table_count(conn, "quiz_attempts"),
                "quiz_answers": _table_count(conn, "quiz_answers"),
            },
            "irt_readiness": _irt_readiness(conn),
            "bkt_readiness": _bkt_readiness(conn),
        }
        report["decision"] = _decision(report["irt_readiness"], report["bkt_readiness"])
        print(json.dumps(report, indent=2, sort_keys=False))
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else None))
