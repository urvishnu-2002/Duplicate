
import requests
import json

BASE_URL = "http://localhost:8000"

def test_register_error():
    print("\nTest 1: Register with missing email")
    headers = {"Content-Type": "application/json"}
    data = {"username": "test_missing_email", "password": "password123"}
    try:
        r = requests.post(f"{BASE_URL}/register/", json=data, headers=headers)
        print(f"Status: {r.status_code}")
        print(f"Response: {r.text}")
    except Exception as e:
        print(f"Error: {e}")

def test_payment_error():
    print("\nTest 2: Payment without mode (unauthenticated)")
    # This will likely fail with 401 first
    try:
        r = requests.post(f"{BASE_URL}/process_payment/", json={"items": []})
        print(f"Status: {r.status_code}")
        print(f"Response: {r.text}")
    except Exception as e:
        print(f"Error: {e}")

test_register_error()
test_payment_error()
