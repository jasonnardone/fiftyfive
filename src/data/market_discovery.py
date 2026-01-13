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
        self._market_titles: Dict[str, str] = {}

    def get_market_titles(self) -> Dict[str, str]:
        """Get mapping of ticker to market title"""
        return self._market_titles.copy()

    async def get_target_markets(self, limit: int = 10) -> List[str]:
        """Get list of target market tickers matching filters using rigorous verification

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

            # 2. Pre-filter by volume and expiration (cheap checks)
            candidates = []
            for market_data in all_markets:
                if self._matches_basic_filters(market_data):
                    candidates.append(market_data)

            logger.info(f"Found {len(candidates)} candidates passing volume/expiration filters")
            
            # 3. Sort candidates
            if self.config.sort_by == 'expiration':
                candidates.sort(key=lambda m: m.get('close_time') or m.get('expiration_time') or '9999-12-31')
            elif self.config.sort_by == 'volume':
                candidates.sort(key=lambda m: int(m.get('volume', 0)), reverse=True)
            
            # 4. Detailed Verification (Fetch full details until we find enough valid markets)
            verified_markets = []
            max_scan = 200 # Scan up to 200 high-volume candidates
            
            logger.info(f"Scanning top {max_scan} candidates via API until {limit} valid markets found...")
            
            self._market_titles.clear()
            
            for i, candidate in enumerate(candidates[:max_scan]):
                if len(verified_markets) >= limit:
                    break
                    
                ticker = candidate['ticker']
                try:
                    # Fetch full details to get accurate category/series info
                    full_details = await self.api_client.get_market(ticker)
                    
                    if self._matches_category_strict(full_details):
                        verified_markets.append(ticker)
                        self._market_titles[ticker] = full_details.get('title', ticker)
                        logger.info(f"Accepted: {ticker} ({full_details.get('category')})")
                    else:
                        pass # Debug log is handled inside _matches_category_strict
                        
                    # Rate limit protection for detailed fetches
                    await asyncio.sleep(0.1) 
                    
                except Exception as e:
                    logger.warning(f"Failed to verify {ticker}: {e}")
            
            # Cache result
            self._cached_markets = verified_markets
            
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
                limit=200,
                cursor=cursor
            )
            
            markets = response.get('markets', [])
            all_markets.extend(markets)
            logger.info(f"Fetched page: {len(markets)} markets (Total: {len(all_markets)})")
            
            cursor = response.get('cursor')
            
            # Check safety limit if configured
            safety_limit = self.config.max_market_discovery_limit
            if safety_limit and safety_limit > 0 and len(all_markets) > safety_limit:
                logger.warning(f"Market limit ({safety_limit}) reached, stopping discovery")
                break

            if not cursor:
                break
                
            # Rate limit protection
            await asyncio.sleep(0.1)
            
        return all_markets

    def _matches_basic_filters(self, market: Dict) -> bool:
        """Check volume and expiration filters only (no category)"""
        ticker = market.get('ticker')
        
        # Volume filter
        volume = market.get('volume', 0)
        try:
            volume = int(volume)
        except (ValueError, TypeError):
            volume = 0

        if volume < self.config.min_daily_volume:
            return False

        # Expiration filter
        if self.config.max_days_to_expiration:
            expiration = market.get('close_time') or market.get('expiration_time')
            if expiration:
                if isinstance(expiration, str):
                    try:
                        exp_time = datetime.fromisoformat(expiration.replace('Z', '+00:00'))
                        now = datetime.now(exp_time.tzinfo) if exp_time.tzinfo else datetime.utcnow()
                        days_to_exp = (exp_time - now).days
                        
                        if days_to_exp > self.config.max_days_to_expiration:
                            return False
                        if days_to_exp < -1:
                            return False
                    except ValueError:
                        pass 

        return True

    def _matches_category_strict(self, market: Dict) -> bool:
        """Check category against strict config using full market details"""
        if not self.config.categories:
            return True
            
        category = market.get('category')
        allowed_cats = [c.lower() for c in self.config.categories]
        
        # 1. Check explicit category if present
        if category:
            if category.lower() in allowed_cats:
                return True
            # If explicit category mismatch, reject
            logger.debug(f"Rejected {market.get('ticker')}: Category '{category}' not in {self.config.categories}")
            return False
            
        # 2. Fallback: Infer from ticker if category is missing
        ticker = market.get('ticker', '')
        t_upper = ticker.upper()
        
        # Sports Keywords (Reject)
        if any(x in t_upper for x in ["NFL", "NBA", "MLB", "NHL", "ESPORTS", "SOCCER", "TENNIS", "UFC", "F1", "CFB", "CBB", "ATP", "CHALLENGER"]):
            logger.debug(f"Rejected {ticker}: Inferred category 'sports' (banned)")
            return False
            
        # Econ/Politics Keywords (Accept)
        # Note: We group these because if the config allows "economics" OR "politics", we generally want these.
        # If the user strictly wanted ONLY economics but not politics, this might be too loose,
        # but given the data quality, it's a necessary compromise.
        if any(x in t_upper for x in ["FED", "CPI", "GDP", "INFLATION", "RATE", "UNEMPLOYMENT", "DEBT", "INX", "NASDAQ", "SP500", "DJIA", "TREASURY", "YIELD", "GAS", "OIL", "GOLD", "ELECTION", "SENATE", "HOUSE", "PRESIDENT", "VOTE", "POLL", "APPROVAL", "NOMINATION", "SUPREME", "COURT", "LAW"]):
            logger.info(f"Accepted {ticker}: Inferred category 'econ/politics'")
            return True
            
        # 3. Unknown (Accept)
        logger.info(f"Accepted {ticker}: Category unknown/misc (no keyword match)")
        return True
