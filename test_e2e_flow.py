"""
End-to-End Integration Test Script
===================================
Tests the complete student journey through the Dental Tutor AI system.

Requirements:
- FastAPI server running on http://localhost:8000
- GEMINI_API_KEY set in environment
- Database initialized (dentai_app.db exists)

Usage:
    python test_e2e_flow.py
"""

import requests
import json
import sys
import time
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8001"  # FastAPI server running on port 8001
TEST_STUDENT_ID = "test_e2e_999"
TEST_PASSWORD = "testpass123"
TEST_NAME = "E2E Test Student"
TEST_CASE_ID = "olp_001"

# ANSI color codes for pretty output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_step(step_num, description):
    """Print step header"""
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}STEP {step_num}: {description}{RESET}")
    print(f"{BLUE}{'='*70}{RESET}")

def print_success(message):
    """Print success message"""
    print(f"{GREEN}✅ {message}{RESET}")

def print_error(message):
    """Print error message"""
    print(f"{RED}❌ {message}{RESET}")

def print_info(message):
    """Print info message"""
    print(f"{YELLOW}ℹ️  {message}{RESET}")

def check_server_health():
    """Check if FastAPI server is running"""
    print_step(0, "Server Health Check")
    try:
        response = requests.get(f"{BASE_URL}/docs", timeout=5)
        if response.status_code == 200:
            print_success(f"FastAPI server is running at {BASE_URL}")
            return True
        else:
            print_error(f"Server responded with status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print_error(f"Cannot connect to {BASE_URL}")
        print_info("Make sure the FastAPI server is running: uvicorn app.api.main:app --reload")
        return False
    except Exception as e:
        print_error(f"Health check failed: {e}")
        return False

def test_auth():
    """Test authentication (register or login)"""
    print_step(1, "Authentication (Register/Login)")
    
    # Try to register first
    print_info(f"Attempting to register user: {TEST_STUDENT_ID}")
    register_data = {
        "student_id": TEST_STUDENT_ID,
        "name": TEST_NAME,
        "password": TEST_PASSWORD
    }
    
    response = requests.post(f"{BASE_URL}/api/auth/register", json=register_data)
    
    if response.status_code in [200, 201]:  # Accept both 200 OK and 201 Created
        print_success(f"Registration successful!")
        token = response.json()["access_token"]
        print_info(f"Access token: {token[:20]}...")
        return token
    elif response.status_code == 400:
        # User might already exist, try login
        print_info("User already exists. Attempting login...")
        login_data = {
            "student_id": TEST_STUDENT_ID,
            "password": TEST_PASSWORD
        }
        response = requests.post(f"{BASE_URL}/api/auth/login", json=login_data)
        
        if response.status_code == 200:
            print_success(f"Login successful!")
            token = response.json()["access_token"]
            print_info(f"Access token: {token[:20]}...")
            return token
        else:
            print_error(f"Login failed: {response.status_code} - {response.text}")
            return None
    else:
        print_error(f"Registration failed: {response.status_code} - {response.text}")
        return None

def test_chat_message(token, message, step_num):
    """Test sending a chat message"""
    print_step(step_num, f"Send Chat Message: '{message[:50]}...'")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    chat_data = {
        "message": message,
        "case_id": TEST_CASE_ID
    }
    
    print_info(f"POST /api/chat/send")
    response = requests.post(f"{BASE_URL}/api/chat/send", json=chat_data, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        print_success(f"Chat message sent successfully!")
        print_info(f"Case ID: {data.get('case_id')}")
        print_info(f"Session ID: {data.get('session_id')}")
        print_info(f"Score: {data.get('score')}")
        print_info(f"AI Response: {data.get('final_feedback')[:100]}...")
        return data
    else:
        print_error(f"Chat failed: {response.status_code} - {response.text}")
        return None

def test_feedback_submission(token, session_id):
    """Test submitting feedback"""
    print_step(4, "Submit Feedback")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    feedback_data = {
        "session_id": session_id,
        "case_id": TEST_CASE_ID,
        "rating": 5,
        "comment": "E2E test feedback - System working perfectly! 🚀"
    }
    
    print_info(f"POST /api/feedback/submit")
    print_info(f"Session ID: {session_id}, Rating: 5 stars")
    response = requests.post(f"{BASE_URL}/api/feedback/submit", json=feedback_data, headers=headers)
    
    if response.status_code in [200, 201]:  # Accept both 200 OK and 201 Created
        data = response.json()
        print_success(f"Feedback submitted successfully!")
        print_info(f"Message: {data.get('message')}")
        return True
    else:
        print_error(f"Feedback submission failed: {response.status_code} - {response.text}")
        return False

def test_analytics_export(token, endpoint_name, endpoint_path):
    """Test CSV export endpoints"""
    print_step(5, f"Export Analytics: {endpoint_name}")
    
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    print_info(f"GET {endpoint_path}")
    response = requests.get(f"{BASE_URL}{endpoint_path}", headers=headers)
    
    if response.status_code == 200:
        csv_content = response.text
        lines = csv_content.strip().split('\n')
        print_success(f"CSV export successful!")
        print_info(f"CSV size: {len(csv_content)} bytes")
        print_info(f"Number of rows: {len(lines)} (including header)")
        
        # Show first few lines
        print_info(f"First 3 lines:")
        for i, line in enumerate(lines[:3]):
            print(f"  {line[:100]}...")
        
        return True
    else:
        print_error(f"Export failed: {response.status_code} - {response.text}")
        return False

def main():
    """Main test execution"""
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}   🧪 DENTAL TUTOR AI - END-TO-END INTEGRATION TEST{RESET}")
    print(f"{BLUE}   Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{RESET}")
    print(f"{BLUE}{'='*70}{RESET}\n")
    
    # Step 0: Health check
    if not check_server_health():
        print_error("\nServer is not running. Exiting.")
        sys.exit(1)
    
    # Step 1: Authentication
    token = test_auth()
    if not token:
        print_error("\nAuthentication failed. Exiting.")
        sys.exit(1)
    
    # Step 2: First chat message
    chat_response_1 = test_chat_message(
        token, 
        "Hastanın şikayeti nedir? Anamnez almak istiyorum.",
        2
    )
    if not chat_response_1:
        print_error("\nFirst chat message failed. Exiting.")
        sys.exit(1)
    
    # Extract session_id
    session_id = chat_response_1.get("session_id")
    if not session_id:
        print_error("\nSession ID not found in response. Exiting.")
        sys.exit(1)
    
    print_info(f"✓ Session ID captured: {session_id}")
    
    # Step 3: Second chat message (test session persistence)
    time.sleep(1)  # Small delay to simulate real usage
    chat_response_2 = test_chat_message(
        token,
        "Oral mukoza muayenesi yapıyorum. Lezyon karakteristiklerini inceliyorum.",
        3
    )
    if not chat_response_2:
        print_error("\nSecond chat message failed. Exiting.")
        sys.exit(1)
    
    # Verify same session_id
    if chat_response_2.get("session_id") != session_id:
        print_error(f"\nSession ID mismatch! Expected {session_id}, got {chat_response_2.get('session_id')}")
        sys.exit(1)
    
    print_success("Session persistence verified!")
    
    # Step 4: Submit feedback
    if not test_feedback_submission(token, session_id):
        print_error("\nFeedback submission failed. Exiting.")
        sys.exit(1)
    
    # Step 5: Export analytics (three endpoints)
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}STEP 5: Analytics CSV Exports{RESET}")
    print(f"{BLUE}{'='*70}{RESET}")
    
    exports = [
        ("Actions CSV", "/api/analytics/export/actions"),
        ("Feedback CSV", "/api/analytics/export/feedback"),
        ("Sessions CSV", "/api/analytics/export/sessions")
    ]
    
    for idx, (name, path) in enumerate(exports):
        print(f"\n{YELLOW}--- Export {idx+1}/3: {name} ---{RESET}")
        if not test_analytics_export(token, name, path):
            print_error(f"\n{name} export failed. Exiting.")
            sys.exit(1)
        time.sleep(0.5)
    
    # Final summary
    print(f"\n{GREEN}{'='*70}{RESET}")
    print(f"{GREEN}   ✅ ALL TESTS PASSED - SYSTEM 100% READY FOR PILOT STUDY{RESET}")
    print(f"{GREEN}{'='*70}{RESET}\n")
    
    print(f"{GREEN}Test Summary:{RESET}")
    print(f"{GREEN}✓ Authentication: Working{RESET}")
    print(f"{GREEN}✓ Chat Messages: Working (session persistence verified){RESET}")
    print(f"{GREEN}✓ Session Tracking: Working (session_id: {session_id}){RESET}")
    print(f"{GREEN}✓ Feedback Submission: Working{RESET}")
    print(f"{GREEN}✓ Analytics Exports (3): All Working{RESET}")
    print(f"\n{GREEN}🚀 The system is production-ready for the pilot study tomorrow!{RESET}\n")
    
    return 0

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Test interrupted by user.{RESET}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{RED}Unexpected error: {e}{RESET}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
