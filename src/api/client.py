"""REST API client for Kalshi API v2"""

import aiohttp
from typing import Optional, Dict, Any, List
from loguru import logger

from src.api.auth import KalshiAuth
from src.utils.rate_limiter import RateLimiter
from src.models.config import ExchangeConfig


class KalshiClient:
    """Async REST API client for Kalshi with authentication and rate limiting"""

    def __init__(
        self,
        config: ExchangeConfig,
        rate_limiter: RateLimiter,
        session: Optional[aiohttp.ClientSession] = None
    ):
        """Initialize Kalshi API client

        Args:
            config: Exchange configuration
            rate_limiter: Rate limiter instance
            session: Optional aiohttp session (will create if not provided)
        """
        self.config = config
        self.rate_limiter = rate_limiter
        self.base_url = config.api_base_url
        self.session = session
        self._owned_session = session is None

        # Initialize authenticator
        self.auth = KalshiAuth(
            api_key_id=config.api_key_id,
            private_key_path=config.private_key_path
        )

    async def __aenter__(self):
        """Async context manager entry"""
        if self._owned_session:
            connector = aiohttp.TCPConnector(limit=50)
            timeout = aiohttp.ClientTimeout(total=10)
            self.session = aiohttp.ClientSession(connector=connector, timeout=timeout)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self._owned_session and self.session:
            await self.session.close()

    async def _request(
        self,
        method: str,
        path: str,
        body: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        is_write: bool = False
    ) -> Dict[str, Any]:
        """Execute authenticated API request with rate limiting

        Args:
            method: HTTP method
            path: API endpoint path
            body: Request body (for POST/PUT/DELETE)
            params: Query parameters
            is_write: Whether this is a write request (for rate limiting)

        Returns:
            Response JSON

        Raises:
            aiohttp.ClientError: On HTTP errors
        """
        # Acquire rate limit token
        if is_write:
            acquired = await self.rate_limiter.acquire_write(timeout=5.0)
        else:
            acquired = await self.rate_limiter.acquire_read(timeout=5.0)

        if not acquired:
            raise RuntimeError("Rate limit timeout")

        # Prepare request body
        body_str = ""
        if body:
            import json
            body_str = json.dumps(body)

        # Build full URL
        url = f"{self.base_url}{path}"

        # Extract the path portion for signing (everything after domain)
        # e.g., https://api.elections.kalshi.com/trade-api/v2/portfolio/balance -> /trade-api/v2/portfolio/balance
        from urllib.parse import urlparse
        parsed = urlparse(url)
        full_path = parsed.path

        # Get authentication headers (sign the full path including /trade-api/v2/)
        headers = self.auth.sign_request(method, full_path, body_str)

        # Execute request
        async with self.session.request(
            method=method,
            url=url,
            headers=headers,
            data=body_str if body else None,
            params=params
        ) as response:
            response.raise_for_status()
            return await response.json()

    # ============================================================================
    # Portfolio Endpoints
    # ============================================================================

    async def get_balance(self) -> Dict[str, Any]:
        """Get account balance

        Returns:
            Balance information (use 'balance' field, not 'balance_total')
        """
        return await self._request('GET', '/portfolio/balance', is_write=False)

    async def get_positions(self) -> List[Dict[str, Any]]:
        """Get current positions

        Returns:
            List of position objects
        """
        response = await self._request('GET', '/portfolio/positions', is_write=False)
        return response.get('positions', [])

    async def get_orders(
        self,
        ticker: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get orders

        Args:
            ticker: Optional market ticker filter
            status: Optional status filter

        Returns:
            List of order objects
        """
        params = {}
        if ticker:
            params['ticker'] = ticker
        if status:
            params['status'] = status

        response = await self._request('GET', '/portfolio/orders', params=params, is_write=False)
        return response.get('orders', [])

    async def get_fills(
        self,
        ticker: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get fill history

        Args:
            ticker: Optional market ticker filter
            limit: Maximum number of fills to return

        Returns:
            List of fill objects
        """
        params = {'limit': limit}
        if ticker:
            params['ticker'] = ticker

        response = await self._request('GET', '/portfolio/fills', params=params, is_write=False)
        return response.get('fills', [])

    async def place_order(
        self,
        ticker: str,
        side: str,
        action: str,
        count: int,
        yes_price: Optional[int] = None,
        no_price: Optional[int] = None,
        client_order_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Place limit order

        Args:
            ticker: Market ticker
            side: 'yes' or 'no'
            action: 'buy' or 'sell'
            count: Number of contracts
            yes_price: Price in cents (1-99) for YES orders
            no_price: Price in cents (1-99) for NO orders
            client_order_id: Optional client order ID

        Returns:
            Order object

        Raises:
            ValueError: If both yes_price and no_price provided or neither provided
        """
        if (yes_price is None) == (no_price is None):
            raise ValueError("Exactly one of yes_price or no_price must be provided")

        body = {
            'ticker': ticker,
            'action': action,
            'side': side,
            'count': count,
            'type': 'limit'
        }

        if yes_price is not None:
            body['yes_price'] = yes_price
        if no_price is not None:
            body['no_price'] = no_price
        if client_order_id:
            body['client_order_id'] = client_order_id

        response = await self._request('POST', '/portfolio/orders', body=body, is_write=True)
        return response

    async def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """Cancel order

        Args:
            order_id: Order ID to cancel

        Returns:
            Cancelled order object
        """
        response = await self._request('DELETE', f'/portfolio/orders/{order_id}', is_write=True)
        return response

    # ============================================================================
    # Market Data Endpoints
    # ============================================================================

    async def get_markets(
        self,
        status: Optional[str] = None,
        limit: int = 100,
        cursor: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get markets with pagination

        Args:
            status: Optional status filter ('open', 'closed', 'settled')
            limit: Maximum results per page
            cursor: Pagination cursor

        Returns:
            Markets response with 'markets' list and 'cursor'
        """
        params = {'limit': limit}
        if status:
            params['status'] = status
        if cursor:
            params['cursor'] = cursor

        return await self._request('GET', '/markets', params=params, is_write=False)

    async def get_market(self, ticker: str) -> Dict[str, Any]:
        """Get single market details

        Args:
            ticker: Market ticker

        Returns:
            Market object
        """
        response = await self._request('GET', f'/markets/{ticker}', is_write=False)
        return response.get('market', {})

    async def get_orderbook(self, ticker: str, depth: int = 10) -> Dict[str, Any]:
        """Get order book snapshot

        Args:
            ticker: Market ticker
            depth: Number of price levels per side

        Returns:
            Order book snapshot
        """
        params = {'depth': depth}
        return await self._request('GET', f'/markets/{ticker}/orderbook', params=params, is_write=False)

    # ============================================================================
    # Utility Methods
    # ============================================================================

    async def close(self):
        """Close client session"""
        if self._owned_session and self.session:
            await self.session.close()
