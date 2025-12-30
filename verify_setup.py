"""
FastAPI Setup Verification
===========================
Run this script to verify the FastAPI backend is set up correctly.

Usage: python verify_setup.py
"""

import os
import sys
from pathlib import Path

def check_file_exists(filepath: str) -> bool:
    """Check if a file exists."""
    exists = Path(filepath).exists()
    status = "✅" if exists else "❌"
    print(f"{status} {filepath}")
    return exists

def check_module_installed(module_name: str) -> bool:
    """Check if a Python module is installed."""
    try:
        __import__(module_name)
        print(f"✅ {module_name} is installed")
        return True
    except ImportError:
        print(f"❌ {module_name} is NOT installed")
        return False

def main():
    print("=" * 60)
    print("FASTAPI BACKEND SETUP VERIFICATION")
    print("=" * 60)
    
    print("\n📁 Checking File Structure...")
    print("-" * 60)
    
    files_to_check = [
        "app/api/__init__.py",
        "app/api/main.py",
        "app/api/deps.py",
        "app/api/routers/__init__.py",
        "app/api/routers/chat.py",
        "app/api/routers/auth.py",
        "requirements-api.txt"
    ]
    
    all_files_exist = all(check_file_exists(f) for f in files_to_check)
    
    print("\n📦 Checking Python Dependencies...")
    print("-" * 60)
    
    modules_to_check = ["fastapi", "uvicorn", "pydantic"]
    all_modules_installed = all(check_module_installed(m) for m in modules_to_check)
    
    print("\n🔑 Checking Environment Variables...")
    print("-" * 60)
    
    env_file = Path(".env")
    if env_file.exists():
        print("✅ .env file exists")
        # Don't print the actual key for security
        gemini_key = os.getenv("GEMINI_API_KEY")
        if gemini_key:
            print(f"✅ GEMINI_API_KEY is set (length: {len(gemini_key)})")
        else:
            print("⚠️  GEMINI_API_KEY not found in environment")
            print("   Run: pip install python-dotenv")
            print("   Then add GEMINI_API_KEY to .env file")
    else:
        print("❌ .env file not found")
        print("   Create .env file with: GEMINI_API_KEY=your_key_here")
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    if all_files_exist and all_modules_installed:
        print("✅ FastAPI backend is set up correctly!")
        print("\n📝 Next steps:")
        print("1. Install dependencies (if not done):")
        print("   pip install fastapi uvicorn pydantic python-multipart")
        print("\n2. Run the API server:")
        print("   uvicorn app.api.main:app --reload --port 8000")
        print("\n3. Test in browser:")
        print("   http://localhost:8000/docs")
    else:
        print("⚠️  Setup incomplete. Please fix the issues above.")
        
        if not all_modules_installed:
            print("\n📦 Install missing dependencies:")
            print("   pip install -r requirements-api.txt")

if __name__ == "__main__":
    main()
