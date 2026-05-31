"""S11-A: Research snapshot endpoints (instructor/admin only)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import List, Optional

from app.api.deps import AuthenticatedUser, get_db, require_roles
from app.services import research_snapshot_service as svc
from db.database import SystemSnapshot, UserRole

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
