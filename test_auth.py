"""
Test authentication endpoints directly from Python
"""
import requests
import json

API_URL = "http://localhost:8000"

print("=" * 60)
print("FastAPI Authentication Test")
print("=" * 60)

# Test 1: Register new user
print("\n1️⃣ Testing REGISTER...")
register_data = {
    "student_id": "test999",
    "name": "Test User",
    "password": "test123",
    "email": "test@example.com"
}

try:
    response = requests.post(f"{API_URL}/api/auth/register", json=register_data)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 201:
        print("✅ Register SUCCESS!")
        token = response.json().get("access_token")
    elif response.status_code == 400:
        print("⚠️ User already exists, trying login instead...")
    else:
        print(f"❌ Register FAILED: {response.status_code}")
except Exception as e:
    print(f"❌ Network Error: {e}")

# Test 2: Login
print("\n2️⃣ Testing LOGIN...")
login_data = {
    "student_id": "test999",
    "password": "test123"
}

try:
    response = requests.post(f"{API_URL}/api/auth/login", json=login_data)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 200:
        print("✅ Login SUCCESS!")
        token = response.json().get("access_token")
        print(f"\n🔑 Token: {token[:50]}...")
    else:
        print(f"❌ Login FAILED: {response.status_code}")
        print("Possible reasons:")
        print("  - Password verification not working (pwd_context issue)")
        print("  - User not found in users.json")
        print("  - Hash mismatch")
except Exception as e:
    print(f"❌ Network Error: {e}")

print("\n" + "=" * 60)
print("Test completed!")
print("=" * 60)
