"""
FastAPI Main Application
=========================
Entry point for the Dental Tutor AI REST API.
Runs alongside the Streamlit app without interference.

Run with: uvicorn app.api.main:app --reload --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.api.routers import chat, auth

from dotenv import load_dotenv
load_dotenv()  # .env dosyasını yükler

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Dental Tutor AI API",
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
        "http://localhost:3000",  # React development server
        "http://127.0.0.1:3000",  # Localhost alternative
        "http://192.168.1.72:3000",  # Local network IP
        "http://localhost:5173",  # Vite development server
        "http://localhost:8000",  # Backend self-reference
        "*",  # Fallback for any other origin (development only)
    ],
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Allow all headers
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["authentication"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])

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
        "service": "Dental Tutor AI API",
        "version": "1.0.0"
    }

# Startup event
@app.on_event("startup")
async def startup_event():
    logger.info("🚀 Dental Tutor API starting up...")
    logger.info("📚 API documentation available at: http://localhost:8000/docs")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("👋 Dental Tutor API shutting down...")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
