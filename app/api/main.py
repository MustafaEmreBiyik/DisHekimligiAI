"""
FastAPI Main Application
=========================
Entry point for the DentAI REST API.
Runs alongside the Streamlit app without interference.

Run with: uvicorn app.api.main:app --reload --port 8000
"""

# CRITICAL: Load .env file FIRST before any imports that use environment variables
from dotenv import load_dotenv
load_dotenv()  # Must be called before routers are imported

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.api.routers import chat, auth, cases, feedback, analytics, quiz, recommendations
from app.api.deps import validate_auth_configuration
from db.database import init_db
# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="DentAI API",
    description="RESTful API for dental education simulation platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS (Cross-Origin Resource Sharing)
# Allows React frontend (localhost:3000) to communicate with API (localhost:8000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "http://localhost:8000",
        "http://localhost:8001",
        "http://127.0.0.1:8001",
        "http://192.168.1.5:3000",
        "http://192.168.1.5:3001",
        "http://192.168.1.72:3000",
        "http://localhost:5173",
        "*",
    ],
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Allow all headers
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["authentication"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(chat.sessions_router, prefix="/api", tags=["sessions"])
app.include_router(feedback.router, prefix="/api/feedback", tags=["feedback"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["analytics"])
app.include_router(cases.router, prefix="/api/cases", tags=["cases"])
app.include_router(quiz.router, prefix="/api/quiz", tags=["quiz"])
app.include_router(recommendations.router, prefix="/api/recommendations", tags=["recommendations"])

# Root endpoint
@app.get("/")
def root():
    """
    API health check endpoint.
    Returns status message.
    """
    return {
        "status": "Dental Tutor API is running",
        "version": "1.0.0",
        "docs": "/docs"
    }

# Health check endpoint
@app.get("/health")
def health_check():
    """
    Detailed health check for monitoring.
    """
    return {
        "status": "healthy",
        "service": "DentAI API",
        "version": "1.0.0"
    }

# Startup event
@app.on_event("startup")
async def startup_event():
    validate_auth_configuration()
    init_db()
    logger.info("🚀 Dental Tutor API starting up...")
    logger.info("📚 API documentation available at: http://localhost:8000/docs")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("👋 Dental Tutor API shutting down...")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
