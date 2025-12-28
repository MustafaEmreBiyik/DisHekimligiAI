"""
Authentication Router
=====================
JWT-based authentication endpoints for user login and registration.
"""

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from datetime import timedelta
import bcrypt
from sqlalchemy.orm import Session
import logging
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
import json
from pathlib import Path
from app.api.deps import get_current_user
from app.api.deps import get_db, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES

logger = logging.getLogger(__name__)

router = APIRouter()

# Mock user database (TODO: Replace with real database table)
USERS_FILE = Path(__file__).parent.parent.parent / "data" / "users.json"


def get_users_db():
    """Load users from JSON file (mock database)."""
    if not USERS_FILE.exists():
        USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(USERS_FILE, 'w') as f:
            json.dump({}, f)
        return {}
    
    try:
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load users: {e}")
        return {}


def save_users_db(users: dict):
    """Save users to JSON file (mock database)."""
    try:
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(users, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Failed to save users: {e}")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt."""
    # Bcrypt has a maximum password length of 72 bytes
    # Truncate string to ensure it doesn't exceed this limit
    if len(password.encode('utf-8')) > 72:
        # Truncate character by character until under 72 bytes
        while len(password.encode('utf-8')) > 72:
            password = password[:-1]
    return pwd_context.hash(password)


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
    student_id: str = Field(..., description="Student ID")
    name: str = Field(..., description="Student name")

    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "student_id": "2021001",
                "name": "Ahmet Yılmaz"
            }
        }


# ==================== ENDPOINTS ====================

@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register(user_data: UserRegister):
    """
    Register a new student account.
    
    - Creates a new user with hashed password
    - Returns JWT token for immediate login
    - Student ID must be unique
    """
    users = get_users_db()
    
    # Check if user already exists
    if user_data.student_id in users:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Student ID {user_data.student_id} is already registered"
        )
    
    # Hash password
    hashed_password = get_password_hash(user_data.password)
    
    # Create new user
    users[user_data.student_id] = {
        "student_id": user_data.student_id,
        "name": user_data.name,
        "email": user_data.email,
        "hashed_password": hashed_password,
        "created_at": "2025-12-27"  # TODO: Use datetime.utcnow().isoformat()
    }
    
    # Save to database
    save_users_db(users)
    
    logger.info(f"✅ New user registered: {user_data.student_id}")
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user_data.student_id},
        expires_delta=access_token_expires
    )
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        student_id=user_data.student_id,
        name=user_data.name
    )


@router.post("/login", response_model=Token, status_code=status.HTTP_200_OK)
def login(credentials: UserLogin):
    """
    Authenticate a student and return JWT token.
    
    - Verifies student_id and password
    - Returns JWT token valid for 24 hours
    - Use this token in Authorization header: `Bearer <token>`
    """
    users = get_users_db()
    
    # Check if user exists
    if credentials.student_id not in users:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid student ID or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = users[credentials.student_id]
    
    # Verify password
    if not verify_password(credentials.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid student ID or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    logger.info(f"✅ User logged in: {credentials.student_id}")
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": credentials.student_id},
        expires_delta=access_token_expires
    )
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        student_id=user["student_id"],
        name=user["name"]
    )


@router.get("/me", status_code=status.HTTP_200_OK)
def get_current_user_info(current_user: str = Depends(get_current_user)):
    """
    Get current authenticated user's information.
    
    **Requires Authentication:** Yes (Bearer token)
    
    Returns the student ID and profile of the currently logged-in user.
    """
    from app.api.deps import get_current_user
    
    users = get_users_db()
    
    if current_user not in users:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user = users[current_user]
    
    return {
        "student_id": user["student_id"],
        "name": user["name"],
        "email": user.get("email")
    }


@router.get("/status", status_code=status.HTTP_200_OK)
def auth_service_status():
    """
    Check authentication service status.
    """
    users = get_users_db()
    
    return {
        "service": "authentication",
        "status": "operational",
        "jwt_enabled": True,
        "total_users": len(users),
        "password_hashing": "bcrypt",
        "token_expiry": f"{ACCESS_TOKEN_EXPIRE_MINUTES} minutes"
    }
