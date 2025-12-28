"""
API Dependencies
================
Shared dependencies for FastAPI endpoints including JWT authentication.
"""

from typing import Generator, Optional
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from db.database import SessionLocal

# JWT Configuration
SECRET_KEY = "YOUR_SECRET_KEY_CHANGE_IN_PRODUCTION"  # TODO: Move to environment variable
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 hours

# OAuth2 scheme for token extraction
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_db() -> Generator:
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


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: Dictionary containing user information (typically {"sub": user_id})
        expires_delta: Optional custom expiration time
    
    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    """
    Validate JWT token and extract current user ID.
    
    This dependency should be used in protected endpoints:
    
    Usage:
        @router.post("/protected")
        def protected_route(current_user: str = Depends(get_current_user)):
            # current_user contains the student_id
            return {"user": current_user}
    
    Args:
        token: JWT token from Authorization header
    
    Returns:
        student_id (str) extracted from token
    
    Raises:
        HTTPException: 401 if token is invalid or expired
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Decode JWT token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        student_id: str = payload.get("sub")
        
        if student_id is None:
            raise credentials_exception
        
        return student_id
    
    except JWTError:
        raise credentials_exception


def get_current_user_optional(token: Optional[str] = Depends(oauth2_scheme)) -> Optional[str]:
    """
    Optional authentication - returns user ID if token is valid, None otherwise.
    Useful for endpoints that work both authenticated and unauthenticated.
    """
    if not token:
        return None
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None
