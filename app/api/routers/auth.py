"""
Authentication Router
=====================
JWT-based authentication endpoints for user login and registration.
"""

from fastapi import APIRouter, HTTPException, status, Depends, Query
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime, timedelta
import bcrypt
from sqlalchemy.orm import Session
import logging
import json
from pathlib import Path

from app.api.deps import (
    get_db,
    create_access_token,
    get_access_token_expire_minutes,
    AuthenticatedUser,
    get_current_user_context,
    require_roles,
)
from db.database import User, UserRole

logger = logging.getLogger(__name__)

router = APIRouter()

SEED_USER_FILES = [
    Path(__file__).resolve().parents[2] / "data" / "users.json",
    Path(__file__).resolve().parents[3] / "data" / "users.json",
]


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash using bcrypt directly."""
    try:
        plain_bytes = plain_password.encode('utf-8')
        hashed_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(plain_bytes, hashed_bytes)
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt directly."""
    # Bcrypt has a maximum password length of 72 bytes
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
    
    # Generate salt and hash
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


def _normalize_role(raw_role: object) -> UserRole:
    if isinstance(raw_role, UserRole):
        return raw_role

    try:
        role_str = str(raw_role).strip()
        if role_str in UserRole.__members__:
            return UserRole[role_str]
        return UserRole(role_str.lower())
    except Exception:
        return UserRole.STUDENT


def _iter_seed_user_items(payload: object) -> List[dict]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        if all(isinstance(value, dict) for value in payload.values()):
            return list(payload.values())
        return [payload]
    return []


def _import_seed_users_if_empty(db: Session) -> None:
    """
    Import users from JSON only when DB is empty.
    JSON is treated as seed source, never as the live user store.
    """
    existing = db.query(User.id).first()
    if existing:
        return

    imported_count = 0
    seen_ids = set()

    for seed_file in SEED_USER_FILES:
        if not seed_file.exists():
            continue

        try:
            with open(seed_file, 'r', encoding='utf-8') as f:
                payload = json.load(f)
        except Exception as exc:
            logger.warning("Failed to read seed user file %s: %s", seed_file, exc)
            continue

        for item in _iter_seed_user_items(payload):
            user_id = str(item.get("student_id") or item.get("user_id") or "").strip()
            if not user_id or user_id in seen_ids:
                continue

            display_name = str(item.get("name") or item.get("display_name") or user_id).strip()
            email = item.get("email")
            hashed_password = item.get("hashed_password")

            if not hashed_password and item.get("password"):
                hashed_password = get_password_hash(str(item.get("password")))

            if not hashed_password:
                logger.warning("Skipping seed user %s due to missing password hash", user_id)
                continue

            db.add(
                User(
                    user_id=user_id,
                    display_name=display_name,
                    email=email,
                    hashed_password=hashed_password,
                    role=_normalize_role(item.get("role")),
                    is_archived=False,
                    archived_at=None,
                )
            )
            seen_ids.add(user_id)
            imported_count += 1

        if imported_count > 0:
            break

    if imported_count > 0:
        db.commit()
        logger.info("Imported %s users from JSON seed source", imported_count)


def _get_active_user_by_id(db: Session, user_id: str) -> Optional[User]:
    return (
        db.query(User)
        .filter(User.user_id == user_id, User.is_archived.is_(False))
        .first()
    )


# ==================== REQUEST/RESPONSE MODELS ====================

class UserRegister(BaseModel):
    """User registration data."""
    student_id: str = Field(..., description="Student ID number", example="2021001")
    name: str = Field(..., description="Full name", example="Ahmet Yılmaz")
    password: str = Field(..., min_length=6, description="Password (min 6 characters)")
    email: Optional[EmailStr] = Field(None, description="Email address", example="ahmet@example.com")

    class Config:
        json_schema_extra = {
            "example": {
                "student_id": "2021001",
                "name": "Ahmet Yılmaz",
                "password": "securepassword123",
                "email": "ahmet@example.com"
            }
        }


class UserLogin(BaseModel):
    """User login credentials."""
    student_id: str = Field(..., description="Student ID number", example="2021001")
    password: str = Field(..., description="Password")

    class Config:
        json_schema_extra = {
            "example": {
                "student_id": "2021001",
                "password": "securepassword123"
            }
        }


class Token(BaseModel):
    """JWT token response."""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    user_id: str = Field(..., description="Canonical user ID")
    role: UserRole = Field(..., description="Role assigned to the user")
    display_name: str = Field(..., description="Canonical display name")
    student_id: str = Field(..., description="Student ID")
    name: str = Field(..., description="Student name")

    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "user_id": "2021001",
                "role": "student",
                "display_name": "Ahmet Yılmaz",
                "student_id": "2021001",
                "name": "Ahmet Yılmaz"
            }
        }


class UserMe(BaseModel):
    """Authenticated user profile response."""

    user_id: str
    role: UserRole
    display_name: str
    student_id: str
    name: str
    email: Optional[str] = None


class UserSummary(BaseModel):
    """Admin/instructor user listing response."""

    user_id: str
    display_name: str
    email: Optional[str] = None
    role: UserRole
    is_archived: bool
    archived_at: Optional[datetime] = None
    created_at: datetime


class ArchiveUserRequest(BaseModel):
    """Archive/unarchive command payload."""

    archived: bool = Field(default=True, description="True to archive, False to reactivate")


class ArchiveUserResponse(BaseModel):
    """Archive operation response."""

    user_id: str
    is_archived: bool
    archived_at: Optional[datetime] = None


class AuthStatusResponse(BaseModel):
    """Authentication service status response."""

    service: str
    status: str
    jwt_enabled: bool
    total_users: int
    total_archived_users: int
    password_hashing: str
    token_expiry: str


def _build_token_response(user: User, access_token: str) -> Token:
    return Token(
        access_token=access_token,
        token_type="bearer",
        user_id=user.user_id,
        role=_normalize_role(user.role),
        display_name=user.display_name,
        student_id=user.user_id,
        name=user.display_name,
    )


# ==================== ENDPOINTS ====================

@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """
    Register a new student account.
    
    - Creates a new user with hashed password
    - Returns JWT token for immediate login
    - Student ID must be unique
    """
    _import_seed_users_if_empty(db)

    # Check if user already exists (archived or active)
    existing_user = db.query(User).filter(User.user_id == user_data.student_id).first()
    if existing_user:
        detail = f"Student ID {user_data.student_id} is already registered"
        if existing_user.is_archived:
            detail = f"Student ID {user_data.student_id} is archived and cannot register"
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
        )

    # Hash password
    hashed_password = get_password_hash(user_data.password)

    new_user = User(
        user_id=user_data.student_id,
        display_name=user_data.name,
        email=user_data.email,
        hashed_password=hashed_password,
        role=UserRole.STUDENT,
        is_archived=False,
        archived_at=None,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    logger.info(f"✅ New user registered: {user_data.student_id}")
    
    # Create access token
    access_token_expires = timedelta(minutes=get_access_token_expire_minutes())
    access_token = create_access_token(
        user_id=new_user.user_id,
        role=_normalize_role(new_user.role),
        display_name=new_user.display_name,
        expires_delta=access_token_expires,
    )

    return _build_token_response(new_user, access_token)


@router.post("/login", response_model=Token, status_code=status.HTTP_200_OK)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """
    Authenticate a student and return JWT token.
    
    - Verifies student_id and password
    - Returns JWT token valid for 24 hours
    - Use this token in Authorization header: `Bearer <token>`
    """
    _import_seed_users_if_empty(db)

    user = _get_active_user_by_id(db, credentials.student_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid student ID or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify password
    if not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid student ID or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    logger.info(f"✅ User logged in: {credentials.student_id}")
    
    # Create access token
    access_token_expires = timedelta(minutes=get_access_token_expire_minutes())
    access_token = create_access_token(
        user_id=user.user_id,
        role=_normalize_role(user.role),
        display_name=user.display_name,
        expires_delta=access_token_expires,
    )

    return _build_token_response(user, access_token)


@router.get("/me", response_model=UserMe, status_code=status.HTTP_200_OK)
def get_current_user_info(
    current_user: AuthenticatedUser = Depends(get_current_user_context),
    db: Session = Depends(get_db),
):
    """
    Get current authenticated user's information.
    
    **Requires Authentication:** Yes (Bearer token)
    
    Returns the authenticated user's profile.
    """
    _import_seed_users_if_empty(db)
    user = _get_active_user_by_id(db, current_user.user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return UserMe(
        user_id=user.user_id,
        role=_normalize_role(user.role),
        display_name=user.display_name,
        student_id=user.user_id,
        name=user.display_name,
        email=user.email,
    )


@router.get("/status", response_model=AuthStatusResponse, status_code=status.HTTP_200_OK)
def auth_service_status(db: Session = Depends(get_db)):
    """
    Check authentication service status.
    """
    _import_seed_users_if_empty(db)
    active_count = db.query(User).filter(User.is_archived.is_(False)).count()
    archived_count = db.query(User).filter(User.is_archived.is_(True)).count()

    return AuthStatusResponse(
        service="authentication",
        status="operational",
        jwt_enabled=True,
        total_users=active_count,
        total_archived_users=archived_count,
        password_hashing="bcrypt",
        token_expiry=f"{get_access_token_expire_minutes()} minutes",
    )


@router.get("/users", response_model=List[UserSummary], status_code=status.HTTP_200_OK)
def list_users(
    include_archived: bool = Query(default=False),
    current_user: AuthenticatedUser = Depends(require_roles(UserRole.INSTRUCTOR, UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """List users for instructor/admin roles."""
    _import_seed_users_if_empty(db)

    query = db.query(User)
    if not include_archived:
        query = query.filter(User.is_archived.is_(False))

    users = query.order_by(User.created_at.desc()).all()
    return [
        UserSummary(
            user_id=user.user_id,
            display_name=user.display_name,
            email=user.email,
            role=_normalize_role(user.role),
            is_archived=user.is_archived,
            archived_at=user.archived_at,
            created_at=user.created_at,
        )
        for user in users
    ]


@router.patch("/users/{user_id}/archive", response_model=ArchiveUserResponse, status_code=status.HTTP_200_OK)
def archive_user(
    user_id: str,
    request: ArchiveUserRequest,
    current_user: AuthenticatedUser = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """Archive or reactivate a user using soft-delete semantics."""
    _import_seed_users_if_empty(db)

    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    user.is_archived = request.archived
    user.archived_at = datetime.utcnow() if request.archived else None
    db.commit()
    db.refresh(user)

    logger.info(
        "User archive state changed by %s: target=%s archived=%s",
        current_user.user_id,
        user.user_id,
        user.is_archived,
    )

    return ArchiveUserResponse(
        user_id=user.user_id,
        is_archived=user.is_archived,
        archived_at=user.archived_at,
    )
