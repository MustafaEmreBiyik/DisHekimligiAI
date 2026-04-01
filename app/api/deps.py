"""
API Dependencies
================
Shared dependencies for FastAPI endpoints including JWT authentication.
"""

from typing import Callable, Generator, Optional
from datetime import datetime, timedelta
import os
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.orm import Session

from db.database import SessionLocal, User, UserRole

# JWT Configuration
ALGORITHM = "HS256"
AUTH_SECRET_KEY_ENV = "DENTAI_SECRET_KEY"
AUTH_ACCESS_TOKEN_EXPIRE_ENV = "DENTAI_ACCESS_TOKEN_EXPIRE_MINUTES"
DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 hours

# OAuth2 scheme for token extraction
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


class TokenPayload(BaseModel):
    """Standard JWT payload contract for DentAI vNext."""

    user_id: str = Field(..., min_length=1)
    role: UserRole
    display_name: str = Field(..., min_length=1)
    exp: int


class AuthenticatedUser(BaseModel):
    """Authenticated user context injected into protected routes."""

    user_id: str
    role: UserRole
    display_name: str


def _credentials_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def _forbidden_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Forbidden",
    )


def _role_to_value(role: UserRole | str) -> str:
    if isinstance(role, UserRole):
        return role.value

    role_str = str(role).strip()
    if role_str in UserRole.__members__:
        return UserRole[role_str].value

    return role_str.lower()


def get_secret_key() -> str:
    """Fetch JWT secret from environment and fail loudly if absent."""
    secret = os.getenv(AUTH_SECRET_KEY_ENV, "").strip()
    if not secret:
        raise ValueError(
            f"{AUTH_SECRET_KEY_ENV} environment variable is required for JWT signing"
        )
    return secret


def get_access_token_expire_minutes() -> int:
    """Fetch token TTL from environment with safe validation."""
    raw_value = os.getenv(
        AUTH_ACCESS_TOKEN_EXPIRE_ENV,
        str(DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES),
    ).strip()
    try:
        ttl = int(raw_value)
    except ValueError as exc:
        raise ValueError(
            f"{AUTH_ACCESS_TOKEN_EXPIRE_ENV} must be an integer, got '{raw_value}'"
        ) from exc

    if ttl <= 0:
        raise ValueError(
            f"{AUTH_ACCESS_TOKEN_EXPIRE_ENV} must be a positive integer"
        )

    return ttl


def validate_auth_configuration() -> None:
    """Validate required JWT auth settings at application startup."""
    get_secret_key()
    get_access_token_expire_minutes()


def get_db() -> Generator[Session, None, None]:
    """
    Database session dependency for FastAPI endpoints.
    
    Usage:
        @app.get("/example")
        def example(db: Session = Depends(get_db)):
            users = db.query(User).all()
            return users
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_access_token(
    *,
    user_id: str,
    role: UserRole,
    display_name: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create a JWT access token with a standardized payload:
    { user_id, role, display_name, exp }
    
    Args:
        user_id: Stable user identifier
        role: User role enum
        display_name: User-facing name
        expires_delta: Optional custom expiration time
    
    Returns:
        Encoded JWT token string
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=get_access_token_expire_minutes())

    to_encode = {
        "user_id": user_id,
        "role": _role_to_value(role),
        "display_name": display_name,
        "exp": expire,
    }

    encoded_jwt = jwt.encode(to_encode, get_secret_key(), algorithm=ALGORITHM)
    return encoded_jwt


def _decode_token_payload(token: str) -> TokenPayload:
    try:
        payload = jwt.decode(token, get_secret_key(), algorithms=[ALGORITHM])
        return TokenPayload(**payload)
    except (JWTError, ValidationError):
        raise _credentials_exception()


def get_current_user_context(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> AuthenticatedUser:
    """Resolve JWT to an authenticated DB-backed user context."""
    payload = _decode_token_payload(token)

    db_user = (
        db.query(User)
        .filter(User.user_id == payload.user_id, User.is_archived.is_(False))
        .first()
    )
    if not db_user:
        raise _credentials_exception()

    db_role = _role_to_value(db_user.role)
    if db_role != payload.role.value:
        raise _credentials_exception()

    return AuthenticatedUser(
        user_id=db_user.user_id,
        role=UserRole(db_role),
        display_name=db_user.display_name,
    )


def get_current_user(current_user: AuthenticatedUser = Depends(get_current_user_context)) -> str:
    """Backward-compatible dependency that returns only user_id."""
    return current_user.user_id


def get_current_user_optional(
    token: Optional[str] = Depends(oauth2_scheme_optional),
    db: Session = Depends(get_db),
) -> Optional[str]:
    """
    Optional authentication - returns user ID if token is valid, None otherwise.
    Useful for endpoints that work both authenticated and unauthenticated.
    """
    if not token:
        return None

    try:
        payload = _decode_token_payload(token)
        db_user = (
            db.query(User)
            .filter(User.user_id == payload.user_id, User.is_archived.is_(False))
            .first()
        )
        if not db_user:
            return None
        db_role = _role_to_value(db_user.role)
        if db_role != payload.role.value:
            return None
        return db_user.user_id
    except HTTPException:
        return None


def require_roles(*roles: UserRole | str) -> Callable[[AuthenticatedUser], AuthenticatedUser]:
    """Factory dependency that enforces route-level role checks."""

    allowed_roles = {_role_to_value(role) for role in roles}

    def _guard(current_user: AuthenticatedUser = Depends(get_current_user_context)) -> AuthenticatedUser:
        if _role_to_value(current_user.role) not in allowed_roles:
            raise _forbidden_exception()
        return current_user

    return _guard
