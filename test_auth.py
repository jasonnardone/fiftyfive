"""Test Kalshi API authentication"""

import asyncio
import aiohttp
import sys
sys.path.insert(0, '.')

from src.config.loader import load_config
from src.api.auth import KalshiAuth
from loguru import logger

async def test_auth():
    """Test authentication with Kalshi API"""
    print("\n=== Testing Kalshi API Authentication ===\n")

    try:
        # Load config
        config = load_config("config/demo.yaml")

        print(f"[INFO] API Base URL: {config.exchange.api_base_url}")
        print(f"[INFO] API Key ID: {config.exchange.api_key_id[:20]}...")
        print(f"[INFO] Private Key Path: {config.exchange.private_key_path}")

        # Initialize authenticator
        auth = KalshiAuth(
            api_key_id=config.exchange.api_key_id,
            private_key_path=config.exchange.private_key_path
        )

        print(f"\n[OK] Auth initialized successfully")

        # Test signing a request
        method = 'GET'
        path = '/portfolio/balance'
        body = ''

        headers = auth.sign_request(method, path, body)

        print(f"\n[INFO] Generated headers:")
        print(f"  KALSHI-ACCESS-KEY: {headers['KALSHI-ACCESS-KEY'][:30]}...")
        print(f"  KALSHI-ACCESS-SIGNATURE: {headers['KALSHI-ACCESS-SIGNATURE'][:50]}...")
        print(f"  KALSHI-ACCESS-TIMESTAMP: {headers['KALSHI-ACCESS-TIMESTAMP']}")
        print(f"  Content-Type: {headers['Content-Type']}")

        # Make actual API request
        url = f"{config.exchange.api_base_url}{path}"

        print(f"\n[INFO] Making request to: {url}")

        async with aiohttp.ClientSession() as session:
            async with session.request(
                method=method,
                url=url,
                headers=headers
            ) as response:
                print(f"\n[INFO] Response Status: {response.status}")
                print(f"[INFO] Response Headers:")
                for key, value in response.headers.items():
                    print(f"  {key}: {value}")

                response_text = await response.text()
                print(f"\n[INFO] Response Body:")
                print(response_text[:500])

                if response.status == 200:
                    response_json = await response.json()
                    print(f"\n[OK] Authentication successful!")
                    print(f"[INFO] Balance: ${response_json.get('balance', 0):.2f}")
                else:
                    print(f"\n[ERROR] Authentication failed with status {response.status}")
                    print(f"[ERROR] Response: {response_text}")

    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    asyncio.run(test_auth())
