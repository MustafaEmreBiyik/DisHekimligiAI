"""S11-A: Research snapshot endpoints (instructor/admin only)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Any, Dict, List, Optional

import datetime

from app.api.deps import AuthenticatedUser, get_db, require_roles
from app.services import research_snapshot_service as svc
from app.services import ab_test_service as ab_svc
from db.database import ResearchExport, SystemSnapshot, UserRole

router = APIRouter()

_instructor_or_admin = require_roles(UserRole.INSTRUCTOR, UserRole.ADMIN)


class SnapshotCreateRequest(BaseModel):
    label: str = Field(min_length=1, max_length=200)
    notes: Optional[str] = None


class SnapshotSummary(BaseModel):
    id: int
    label: str
    created_by: str
    notes: Optional[str]
    git_commit_hash: Optional[str]
    questions_count: int
    cases_count: int
    bundle_size_bytes: Optional[int]
    created_at: str


class SnapshotDetail(SnapshotSummary):
    scoring_config_payload: dict
    llm_config_payload: dict


def _to_summary(s: SystemSnapshot) -> SnapshotSummary:
    return SnapshotSummary(
        id=s.id,
        label=s.label,
        created_by=s.created_by,
        notes=s.notes,
        git_commit_hash=s.git_commit_hash,
        questions_count=s.questions_count,
        cases_count=s.cases_count,
        bundle_size_bytes=s.bundle_size_bytes,
        created_at=s.created_at.isoformat() if s.created_at else "",
    )


def _to_detail(s: SystemSnapshot) -> SnapshotDetail:
    return SnapshotDetail(
        **_to_summary(s).model_dump(),
        scoring_config_payload=s.scoring_config_payload or {},
        llm_config_payload=s.llm_config_payload or {},
    )


@router.post(
    "/snapshots",
    response_model=SnapshotSummary,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new research snapshot",
)
def create_snapshot(
    body: SnapshotCreateRequest,
    current_user: AuthenticatedUser = Depends(_instructor_or_admin),
    db: Session = Depends(get_db),
) -> SnapshotSummary:
    snapshot = svc.create_snapshot(
        db,
        label=body.label,
        created_by=current_user.user_id,
        notes=body.notes,
    )
    return _to_summary(snapshot)


@router.get(
    "/snapshots",
    response_model=List[SnapshotSummary],
    summary="List all research snapshots (newest first)",
)
def list_snapshots(
    current_user: AuthenticatedUser = Depends(_instructor_or_admin),
    db: Session = Depends(get_db),
) -> List[SnapshotSummary]:
    rows = (
        db.query(SystemSnapshot)
        .order_by(SystemSnapshot.created_at.desc())
        .all()
    )
    return [_to_summary(s) for s in rows]


@router.get(
    "/snapshots/{snapshot_id}",
    response_model=SnapshotDetail,
    summary="Get snapshot detail including scoring config and LLM config",
)
def get_snapshot(
    snapshot_id: int,
    current_user: AuthenticatedUser = Depends(_instructor_or_admin),
    db: Session = Depends(get_db),
) -> SnapshotDetail:
    s = db.query(SystemSnapshot).filter(SystemSnapshot.id == snapshot_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    return _to_detail(s)


@router.get(
    "/recommendation-eval",
    response_model=Dict[str, Any],
    summary="Offline evaluation: V1 vs V2 recommendation algorithm comparison",
)
def recommendation_eval(
    window_days: int = Query(default=60, ge=7, le=365, description="Look-back window in days"),
    current_user: AuthenticatedUser = Depends(_instructor_or_admin),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Run offline evaluation comparing v1 (rule-based) vs v2 (XGBoost+IRT+BKT) on
    historical RecommendationSnapshot data. Returns NDCG@5, Hit-rate@5, MAP@10,
    bootstrap 95% CI on ΔNDCG and a PROMOTE/DO NOT PROMOTE verdict.
    """
    try:
        from app.services.recommendation_evaluator import evaluate as _evaluate
    except ImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Recommendation evaluator unavailable: {exc}. Install xgboost and scipy.",
        )
    return _evaluate(db, window_days=window_days)


@router.get(
    "/experiments",
    response_model=List[Dict[str, Any]],
    summary="List all registered A/B experiments with group distributions (T06)",
)
def list_experiments(
    current_user: AuthenticatedUser = Depends(_instructor_or_admin),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Return each experiment's metadata and current group distribution from DB."""
    result = []
    for exp in ab_svc.list_experiments():
        result.append(ab_svc.get_experiment_summary(exp["experiment_id"], db))
    return result


@router.get(
    "/experiments/{experiment_id}/results",
    response_model=Dict[str, Any],
    summary="Per-group learning metrics for an A/B experiment (T06)",
)
def get_experiment_results(
    experiment_id: str,
    current_user: AuthenticatedUser = Depends(_instructor_or_admin),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Return avg exam score, session count, quiz attempts, and avg mastery per group."""
    try:
        return ab_svc.get_experiment_results(experiment_id, db)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


class ExportSummary(BaseModel):
    id: int
    created_by: str
    created_at: str
    tables_included: List[str]
    row_count_total: int
    status: str
    filename: Optional[str]


def _to_export_summary(e: ResearchExport) -> ExportSummary:
    return ExportSummary(
        id=e.id,
        created_by=e.created_by,
        created_at=e.created_at.isoformat() if e.created_at else "",
        tables_included=e.tables_included or [],
        row_count_total=e.row_count_total,
        status=e.status,
        filename=e.filename,
    )


@router.post(
    "/exports",
    response_model=ExportSummary,
    status_code=status.HTTP_201_CREATED,
    summary="Generate anonymised research dataset export (T08)",
)
def create_export(
    current_user: AuthenticatedUser = Depends(_instructor_or_admin),
    db: Session = Depends(get_db),
) -> ExportSummary:
    """Build a KVKK-anonymised ZIP of all interaction tables and persist it for download."""
    from app.services.research_export_service import build_export_zip

    now = datetime.datetime.utcnow()
    record = ResearchExport(
        created_by=current_user.user_id,
        created_at=now,
        tables_included=[],
        row_count_total=0,
        status="pending",
    )
    db.add(record)
    db.flush()

    try:
        zip_bytes, total_rows, tables = build_export_zip(db)
        filename = f"dentai_export_{now.strftime('%Y%m%d_%H%M%S')}.zip"
        record.zip_bytes = zip_bytes
        record.row_count_total = total_rows
        record.tables_included = tables
        record.status = "ready"
        record.filename = filename
    except Exception as exc:
        record.status = "error"
        record.error_message = str(exc)

    db.commit()
    db.refresh(record)
    return _to_export_summary(record)


@router.get(
    "/exports",
    response_model=List[ExportSummary],
    summary="List all research exports (newest first, T08)",
)
def list_exports(
    current_user: AuthenticatedUser = Depends(_instructor_or_admin),
    db: Session = Depends(get_db),
) -> List[ExportSummary]:
    rows = (
        db.query(ResearchExport)
        .order_by(ResearchExport.created_at.desc())
        .all()
    )
    return [_to_export_summary(r) for r in rows]


@router.get(
    "/exports/{export_id}/download",
    summary="Download anonymised dataset ZIP (T08)",
)
def download_export(
    export_id: int,
    current_user: AuthenticatedUser = Depends(_instructor_or_admin),
    db: Session = Depends(get_db),
) -> Response:
    record = db.query(ResearchExport).filter(ResearchExport.id == export_id).first()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Export not found")
    if record.status != "ready" or not record.zip_bytes:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Export is not ready (status={record.status})",
        )
    filename = record.filename or f"dentai_export_{record.id}.zip"
    return Response(
        content=record.zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/snapshots/{snapshot_id}/export",
    summary="Download full snapshot bundle as JSON",
)
def export_snapshot(
    snapshot_id: int,
    current_user: AuthenticatedUser = Depends(_instructor_or_admin),
    db: Session = Depends(get_db),
) -> Response:
    s = db.query(SystemSnapshot).filter(SystemSnapshot.id == snapshot_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Snapshot not found")

    bundle_bytes = svc.export_bundle(s)
    safe_label = "".join(c if c.isalnum() or c in "-_ " else "_" for c in s.label).strip()
    filename = f"dentai_snapshot_{s.id}_{safe_label[:40]}.json"

    return Response(
        content=bundle_bytes,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
