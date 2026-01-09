"""Test using Kalshi's official example code"""

import requests
import datetime
import base64
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import padding
import os
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Configuration
API_KEY_ID = os.getenv('KALSHI_API_KEY_ID')
PRIVATE_KEY_PATH = os.getenv('KALSHI_PRIVATE_KEY_PATH')
BASE_URL = 'https://api.elections.kalshi.com'

print(f"API Key ID: {API_KEY_ID[:20]}...")
print(f"Private Key Path: {PRIVATE_KEY_PATH}")
print(f"Base URL: {BASE_URL}")

def load_private_key(key_path):
    """Load the private key from file."""
    with open(key_path, "rb") as f:
        return serialization.load_pem_private_key(
            f.read(), password=None, backend=default_backend()
        )

def create_signature(private_key, timestamp, method, path):
    """Create the request signature."""
    path_without_query = path.split('?')[0]
    message = f"{timestamp}{method}{path_without_query}".encode('utf-8')

    print(f"\n[DEBUG] Signing message: {timestamp}{method}{path_without_query}")

    signature = private_key.sign(
        message,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.DIGEST_LENGTH
        ),
        hashes.SHA256()
    )
    return base64.b64encode(signature).decode('utf-8')

def get(private_key, api_key_id, path, base_url=BASE_URL):
    """Make an authenticated GET request."""
    timestamp = str(int(datetime.datetime.now().timestamp() * 1000))
    signature = create_signature(private_key, timestamp, "GET", path)

    headers = {
        'KALSHI-ACCESS-KEY': api_key_id,
        'KALSHI-ACCESS-SIGNATURE': signature,
        'KALSHI-ACCESS-TIMESTAMP': timestamp
    }

    print(f"\n[DEBUG] Headers:")
    print(f"  KALSHI-ACCESS-KEY: {api_key_id[:30]}...")
    print(f"  KALSHI-ACCESS-SIGNATURE: {signature[:50]}...")
    print(f"  KALSHI-ACCESS-TIMESTAMP: {timestamp}")

    url = base_url + path
    print(f"\n[DEBUG] Request URL: {url}")

    return requests.get(url, headers=headers)

# Load private key and get balance
print("\n=== Testing Kalshi Authentication (Official Example) ===")

try:
    private_key = load_private_key(PRIVATE_KEY_PATH)
    print("\n[OK] Private key loaded")

    response = get(private_key, API_KEY_ID, "/trade-api/v2/portfolio/balance")

    print(f"\n[INFO] Response Status: {response.status_code}")
    print(f"[INFO] Response: {response.text}")

    if response.status_code == 200:
        data = response.json()
        balance = data.get('balance', 0) / 100
        print(f"\n[OK] Authentication successful!")
        print(f"[INFO] Your balance: ${balance:.2f}")
    else:
        print(f"\n[ERROR] Authentication failed")

except Exception as e:
    print(f"\n[ERROR] {e}")
    import traceback
    traceback.print_exc()
