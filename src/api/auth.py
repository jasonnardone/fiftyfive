"""RSA-PSS signature authentication for Kalshi API"""

import base64
import hashlib
from pathlib import Path
from typing import Dict
from datetime import datetime, timezone

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend


class KalshiAuth:
    """Handles RSA-PSS signature authentication for Kalshi API v2"""

    def __init__(self, api_key_id: str, private_key_path: str):
        """Initialize authenticator

        Args:
            api_key_id: API key UUID from Kalshi
            private_key_path: Path to RSA private key PEM file

        Raises:
            FileNotFoundError: If private key file not found
            ValueError: If private key is invalid
        """
        self.api_key_id = api_key_id

        # Load private key
        key_path = Path(private_key_path)
        if not key_path.exists():
            raise FileNotFoundError(f"Private key not found: {private_key_path}")

        with open(key_path, 'rb') as f:
            self.private_key = serialization.load_pem_private_key(
                f.read(),
                password=None,
                backend=default_backend()
            )

    def sign_request(
        self,
        method: str,
        path: str,
        body: str = ""
    ) -> Dict[str, str]:
        """Generate authentication headers for API request

        Args:
            method: HTTP method (GET, POST, DELETE, etc.)
            path: Request path (e.g., /portfolio/orders)
            body: Request body (empty string for GET requests)

        Returns:
            Dictionary of authentication headers

        Raises:
            ValueError: If signing fails
        """
        # Get current timestamp in milliseconds
        timestamp = str(int(datetime.now(timezone.utc).timestamp() * 1000))

        # Construct message to sign: timestamp + method + path + body
        message = timestamp + method.upper() + path + body

        # Create signature using RSA-PSS with SHA256
        try:
            signature_bytes = self.private_key.sign(
                message.encode('utf-8'),
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.DIGEST_LENGTH
                ),
                hashes.SHA256()
            )
        except Exception as e:
            raise ValueError(f"Failed to sign request: {e}") from e

        # Base64 encode signature
        signature_b64 = base64.b64encode(signature_bytes).decode('utf-8')

        # Return authentication headers
        return {
            'KALSHI-ACCESS-KEY': self.api_key_id,
            'KALSHI-ACCESS-SIGNATURE': signature_b64,
            'KALSHI-ACCESS-TIMESTAMP': timestamp,
            'Content-Type': 'application/json'
        }

    def get_headers(self, method: str, path: str, body: str = "") -> Dict[str, str]:
        """Alias for sign_request for clearer API"""
        return self.sign_request(method, path, body)
