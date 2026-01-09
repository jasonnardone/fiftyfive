"""Market discovery and selection service"""

import asyncio
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from loguru import logger

from src.api.client import KalshiClient
from src.models.config import MarketFilterConfig


class MarketDiscovery:
    """Discovers and filters tradeable markets"""

    def __init__(
        self,
        api_client: KalshiClient,
        config: MarketFilterConfig
    ):
        """Initialize market discovery

        Args:
            api_client: Kalshi API client
            config: Market filter configuration
        """
        self.api_client = api_client
        self.config = config
        self._cached_markets: List[str] = []

    async def get_target_markets(self, limit: int = 10) -> List[str]:
        """Get list of target market tickers matching filters

        Args:
            limit: Maximum number of markets to return

        Returns:
            List of market tickers
        """
        logger.info("Starting market discovery...")

        try:
            # 1. Fetch all open markets (paginated)
            all_markets = await self._fetch_all_markets()
            logger.info(f"Fetched {len(all_markets)} open markets")

            # 2. Filter markets
            filtered_markets = []
            for market_data in all_markets:
                if self._matches_filters(market_data):
                    filtered_markets.append(market_data['ticker'])

            logger.info(f"Found {len(filtered_markets)} markets matching filters")
            
            # Cache result
            self._cached_markets = filtered_markets[:limit]
            
            return self._cached_markets

        except Exception as e:
            logger.error(f"Market discovery failed: {e}")
            return []

    async def _fetch_all_markets(self) -> List[Dict]:
        """Fetch all open markets handling pagination"""
        all_markets = []
        cursor = None
        
        while True:
            response = await self.api_client.get_markets(
                status='open',
                limit=200,  # Maximize page size
                cursor=cursor
            )
            
            markets = response.get('markets', [])
            all_markets.extend(markets)
            logger.info(f"Fetched page: {len(markets)} markets (Total: {len(all_markets)})")
            
            cursor = response.get('cursor')
            if not cursor or len(all_markets) > 10000:  # Safety limit
                if len(all_markets) > 10000:
                    logger.warning("Market limit (10000) reached, stopping discovery")
                break
                
            # Rate limit protection
            await asyncio.sleep(0.1)
            
        return all_markets

    def _matches_filters(self, market: Dict) -> bool:
        """Check if market matches configured filters"""
        # Volume filter
        volume = market.get('volume', 0)
        if volume < self.config.min_daily_volume:
            return False

        # Category filter
        category = market.get('category')
        if self.config.categories:
            if category not in self.config.categories:
                return False

        # Expiration filter
        if self.config.max_days_to_expiration:
            expiration = market.get('close_time') or market.get('expiration_time')
            if expiration:
                # Handle ISO format '2023-12-31T23:59:59Z'
                if isinstance(expiration, str):
                    try:
                        exp_time = datetime.fromisoformat(expiration.replace('Z', '+00:00'))
                        # Use timezone-aware current time (UTC)
                        now = datetime.now(exp_time.tzinfo) if exp_time.tzinfo else datetime.utcnow()
                        
                        days_to_exp = (exp_time - now).days
                        
                        if days_to_exp > self.config.max_days_to_expiration:
                            return False
                    except ValueError:
                        pass # Ignore parsing errors, assume valid

        # Note: Spread filtering typically requires order book snapshot.
        # We skip it here to avoid N+1 API calls.
        # Spread checks should happen during trading/quoting loop.
        
        return True
