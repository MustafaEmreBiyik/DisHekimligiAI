"""
Notifications Router (T-7A)
============================
Endpoints for reading and marking notifications as read.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional, Any
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_context, AuthenticatedUser, get_db
from db.database import Notification

router = APIRouter()


class NotificationOut(BaseModel):
    id: int
    type: str
    payload: Any
    is_read: bool
    created_at: str


@router.get("/notifications", response_model=List[NotificationOut])
def get_notifications(
    unread_only: bool = False,
    current_user: AuthenticatedUser = Depends(get_current_user_context),
    db: Session = Depends(get_db),
):
    query = db.query(Notification).filter(Notification.user_id == current_user.user_id)
    if unread_only:
        query = query.filter(Notification.is_read == False)
    rows = query.order_by(Notification.created_at.desc()).limit(50).all()
    return [
        NotificationOut(
            id=n.id,
            type=n.type,
            payload=n.payload_json,
            is_read=n.is_read,
            created_at=n.created_at.isoformat() + "Z",
        )
        for n in rows
    ]


@router.get("/notifications/unread-count")
def get_unread_count(
    current_user: AuthenticatedUser = Depends(get_current_user_context),
    db: Session = Depends(get_db),
):
    count = (
        db.query(Notification)
        .filter(Notification.user_id == current_user.user_id, Notification.is_read == False)
        .count()
    )
    return {"count": count}


@router.patch("/notifications/{notification_id}/read")
def mark_as_read(
    notification_id: int,
    current_user: AuthenticatedUser = Depends(get_current_user_context),
    db: Session = Depends(get_db),
):
    n = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.user_id == current_user.user_id)
        .first()
    )
    if not n:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    n.is_read = True
    db.commit()
    return {"status": "ok"}


@router.patch("/notifications/read-all")
def mark_all_as_read(
    current_user: AuthenticatedUser = Depends(get_current_user_context),
    db: Session = Depends(get_db),
):
    db.query(Notification).filter(
        Notification.user_id == current_user.user_id,
        Notification.is_read == False,
    ).update({"is_read": True})
    db.commit()
    return {"status": "ok"}
