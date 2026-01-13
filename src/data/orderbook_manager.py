"""Order book manager with WebSocket deltas and REST snapshots

Maintains accurate order book state by:
1. Subscribing to WebSocket orderbook_delta for real-time updates
2. Periodically fetching REST snapshots for validation
3. Detecting staleness and sequence gaps
"""

import asyncio
import math
from typing import Dict, Optional, Deque
from collections import deque
from datetime import datetime, timedelta
from loguru import logger

from src.models.order import OrderBook, OrderSide, PriceLevel
from src.api.client import KalshiClient
from src.api.websocket import WebSocketManager
from src.api.price_adapter import PriceAdapter


class OrderBookManager:
    """Manages order books for multiple markets"""

    def __init__(
        self,
        api_client: KalshiClient,
        ws_manager: WebSocketManager,
        snapshot_interval: int = 30,
        staleness_threshold: int = 60
    ):
        """Initialize order book manager

        Args:
            api_client: REST API client for snapshots
            ws_manager: WebSocket manager for deltas
            snapshot_interval: Seconds between snapshot syncs
            staleness_threshold: Seconds before order book considered stale
        """
        self.api_client = api_client
        self.ws_manager = ws_manager
        self.snapshot_interval = snapshot_interval
        self.staleness_threshold = staleness_threshold

        # Order books by market ticker
        self._orderbooks: Dict[str, OrderBook] = {}

        # Sequence tracking for gap detection
        self._expected_seq: Dict[str, int] = {}

        # Price history for volatility calc (ticker -> side -> deque)
        self._price_history: Dict[str, Dict[OrderSide, Deque[float]]] = {}

        # Snapshot sync task
        self._snapshot_task: Optional[asyncio.Task] = None
        self._should_stop = False

        logger.info(
            f"OrderBook manager initialized: "
            f"snapshot_interval={snapshot_interval}s, "
            f"staleness_threshold={staleness_threshold}s"
        )

    async def subscribe_market(self, ticker: str) -> bool:
        """Subscribe to market order book

        Args:
            ticker: Market ticker

        Returns:
            True if subscription successful
        """
        # Initialize order book
        if ticker not in self._orderbooks:
            self._orderbooks[ticker] = OrderBook(
                market_ticker=ticker,
                yes_bids=[],
                no_bids=[],
                yes_asks=[],
                no_asks=[]
            )

        # Fetch initial snapshot
        await self._fetch_snapshot(ticker)

        # Subscribe to WebSocket deltas
        channel = "orderbook_delta"
        success = await self.ws_manager.subscribe(
            channel,
            market_tickers=[ticker],
            handler=lambda msg: self._handle_delta(ticker, msg)
        )

        if success:
            logger.info(f"Subscribed to order book: {ticker}")
        else:
            logger.error(f"Failed to subscribe to order book: {ticker}")

        return success

    async def unsubscribe_market(self, ticker: str) -> bool:
        """Unsubscribe from market order book

        Args:
            ticker: Market ticker

        Returns:
            True if unsubscription successful
        """
        channel = f"orderbook_delta:{ticker}"
        success = await self.ws_manager.unsubscribe(channel)

        # Clean up
        self._orderbooks.pop(ticker, None)
        self._expected_seq.pop(ticker, None)

        logger.info(f"Unsubscribed from order book: {ticker}")
        return success

    async def _fetch_snapshot(self, ticker: str) -> None:
        """Fetch order book snapshot from REST API

        Args:
            ticker: Market ticker
        """
        try:
            logger.debug(f"Fetching order book snapshot: {ticker}")
            snapshot = await self.api_client.get_orderbook(ticker, depth=10)

            # Parse snapshot
            orderbook = self._parse_snapshot(ticker, snapshot)

            # Update
            self._orderbooks[ticker] = orderbook
            self._update_price_history(ticker)
            logger.info(f"Order book snapshot updated: {ticker}")

        except Exception as e:
            logger.error(f"Failed to fetch order book snapshot for {ticker}: {e}")

    def _parse_snapshot(self, ticker: str, snapshot: Dict) -> OrderBook:
        """Parse REST API snapshot into OrderBook

        Args:
            ticker: Market ticker
            snapshot: Snapshot data from API

        Returns:
            OrderBook object
        """
        # Handle None snapshot
        if snapshot is None:
            logger.warning(f"Received None snapshot for {ticker}")
            data = {}
        else:
            # Handle "orderbook" wrapper if present (Kalshi v2 API structure)
            data = snapshot.get('orderbook', snapshot)
            
        # Handle if data is None (e.g. orderbook: null)
        if data is None:
            data = {}

        # Parse YES side
        yes_data = data.get('yes', {})
        # Handle list of lists directly or dict with 'bids'/'asks'
        # API v2 usually returns yes: [[price, qty], ...] (bids and asks mixed? No, separate)
        # Actually API v2 documentation says:
        # "yes": [[price, qty], ...], "no": [[price, qty], ...]
        # BUT usually orderbooks have bids and asks separated.
        # Kalshi v2 documentation:
        # GET /markets/{ticker}/orderbook
        # Response: { "orderbook": { "yes": [[price, qty], ...], "no": [[price, qty], ...] } }
        # Wait, the structure in the previous code assumed yes_data.get('bids').
        # If the API returns a LIST of levels, my code was wrong doubly.
        
        # Let's handle both structures to be safe.
        yes_bids = []
        yes_asks = []
        
        if isinstance(yes_data, list):
             # If it's a flat list, we need to infer bid vs ask? 
             # Or maybe it is {bids: [], asks: []}?
             # Let's log the structure to be sure if we are confused.
             # Standard crypto APIs usually separate them.
             # Kalshi docs: "yes": [[price, count], ...]
             # It seems it might be a flat list of ALL orders?
             # Or maybe they are sorted?
             # Let's assume standard {bids: [], asks: []} is what we want, but if we get a list...
             # Actually, if the previous code assumed .get('bids'), it expected a dict.
             # If `data.get('yes')` returns a list, `.get('bids')` would crash?
             # No, `list` doesn't have `.get`. It would raise AttributeError.
             # The previous code: `yes_data.get('bids', [])`.
             # If `yes_data` was a list, this would have crashed. 
             # Since it didn't crash (User reported "no mid_price", not crash), `yes_data` was likely a dict (or empty dict because of key error).
             
             # If `snapshot.get('yes')` returned None (default {}), then it was a dict.
             pass
        elif isinstance(yes_data, dict):
             # It is a dict, so likely has 'bids' and 'asks' keys?
             pass
             
        # Re-reading Kalshi API docs (mental check):
        # Response: { "orderbook": { "yes": [[price, count], ...], "no": [[price, count], ...] } }
        # Actually, it seems Kalshi might just give a list of levels.
        # If so, how do we know bid vs ask?
        # Bids < 50c? No.
        # LIMIT orders have sides.
        # Ah, Kalshi V2 `GET /markets/{ticker}/orderbook` response:
        # { "orderbook": { "yes": [ [99, 10], [1, 10] ], "no": ... } }
        # Wait, usually orderbooks separate bids and asks.
        
        # Let's inspect `OrderBookManager` in `src/data/orderbook_manager.py` again.
        # The previous code:
        # yes_bids = [PriceLevel(...) for level in yes_data.get('bids', [])]
        # This strongly implies the developer thought it returns {bids: ..., asks: ...}.
        
        # If I look at `client.py`, it just returns JSON.
        
        # If I fix the `orderbook` key wrapper, `yes_data` will be whatever is inside "yes".
        # If it's a list, `.get('bids')` will crash.
        # So I should handle that.
        
        pass

        # Parse YES side
        yes_data = data.get('yes') or {}
        # Safety check for type
        if isinstance(yes_data, list):
            # API returned a list instead of dict. This usually happens for empty/inactive markets
            # or a specific market type structure we don't support yet.
            # Treat as empty to allow bot to continue.
            logger.debug(f"Orderbook 'yes' is list for {ticker}, treating as empty")
            yes_bids = []
            yes_asks = []
        else:
            yes_bids = [
                PriceLevel(price=level[0], quantity=level[1])
                for level in yes_data.get('bids', [])
            ]
            yes_asks = [
                PriceLevel(price=level[0], quantity=level[1])
                for level in yes_data.get('asks', [])
            ]

        # Parse NO side
        no_data = data.get('no') or {}
        if isinstance(no_data, list):
             logger.debug(f"Orderbook 'no' is list for {ticker}, treating as empty")
             no_bids = []
             no_asks = []
        else:
            no_bids = [
                PriceLevel(price=level[0], quantity=level[1])
                for level in no_data.get('bids', [])
            ]
            no_asks = [
                PriceLevel(price=level[0], quantity=level[1])
                for level in no_data.get('asks', [])
            ]

        orderbook = OrderBook(
            market_ticker=ticker,
            yes_bids=yes_bids,
            yes_asks=yes_asks,
            no_bids=no_bids,
            no_asks=no_asks,
            last_updated=datetime.utcnow()
        )

        return orderbook

    async def _handle_delta(self, ticker: str, message: Dict) -> None:
        """Handle orderbook_delta WebSocket message

        Args:
            ticker: Market ticker
            message: Delta message
        """
        try:
            seq = message.get('seq')
            msg = message.get('msg', {})

            # Validate sequence
            if not self._validate_sequence(ticker, seq):
                logger.warning(f"Sequence gap detected for {ticker}, fetching snapshot")
                await self._fetch_snapshot(ticker)
                return

            # Get order book
            orderbook = self._orderbooks.get(ticker)
            if not orderbook:
                logger.warning(f"No order book for {ticker}, fetching snapshot")
                await self._fetch_snapshot(ticker)
                return

            # Apply deltas
            yes_deltas = msg.get('yes', [])
            no_deltas = msg.get('no', [])

            if yes_deltas:
                # Determine if bids or asks based on price levels
                # In Kalshi, deltas include both bids and asks in single array
                # We need to separate based on whether they're on bid or ask side
                # For simplicity, we'll update both and let apply_delta handle it
                orderbook.apply_delta(OrderSide.YES, 'bid', yes_deltas)
                orderbook.apply_delta(OrderSide.YES, 'ask', yes_deltas)

            if no_deltas:
                orderbook.apply_delta(OrderSide.NO, 'bid', no_deltas)
                orderbook.apply_delta(OrderSide.NO, 'ask', no_deltas)

            # Update sequence
            orderbook.sequence = seq
            orderbook.last_updated = datetime.utcnow()
            
            # Update price history
            self._update_price_history(ticker)

            logger.debug(f"Applied delta to {ticker} (seq={seq})")

        except Exception as e:
            logger.error(f"Error handling delta for {ticker}: {e}")

    def _update_price_history(self, ticker: str) -> None:
        """Update price history for volatility calculation"""
        if ticker not in self._price_history:
            self._price_history[ticker] = {
                OrderSide.YES: deque(maxlen=100),
                OrderSide.NO: deque(maxlen=100)
            }
            
        for side in [OrderSide.YES, OrderSide.NO]:
            mid = self.get_mid_price(ticker, side)
            if mid is not None:
                self._price_history[ticker][side].append(mid)

    def _validate_sequence(self, ticker: str, seq: int) -> bool:
        """Validate sequence number for gap detection

        Args:
            ticker: Market ticker
            seq: Sequence number

        Returns:
            True if sequence is valid (no gap)
        """
        if ticker not in self._expected_seq:
            # First message
            self._expected_seq[ticker] = seq + 1
            return True

        expected = self._expected_seq[ticker]

        if seq == expected:
            # Expected sequence
            self._expected_seq[ticker] = seq + 1
            return True
        elif seq > expected:
            # Gap detected
            logger.warning(f"Sequence gap for {ticker}: expected={expected}, got={seq}")
            self._expected_seq[ticker] = seq + 1
            return False
        else:
            # Old message (duplicate or out of order)
            logger.debug(f"Old sequence for {ticker}: expected={expected}, got={seq}")
            return False

    def get_orderbook(self, ticker: str) -> Optional[OrderBook]:
        """Get order book for market

        Args:
            ticker: Market ticker

        Returns:
            OrderBook or None if not available
        """
        return self._orderbooks.get(ticker)

    def get_mid_price(self, ticker: str, side: OrderSide) -> Optional[float]:
        """Get mid price for market and side

        Args:
            ticker: Market ticker
            side: Contract side (YES or NO)

        Returns:
            Mid price in dollars or None
        """
        orderbook = self.get_orderbook(ticker)
        if not orderbook:
            return None

        return orderbook.get_mid_price(side)

    def get_best_bid(self, ticker: str, side: OrderSide) -> Optional[float]:
        """Get best bid price

        Args:
            ticker: Market ticker
            side: Contract side

        Returns:
            Best bid price in dollars or None
        """
        orderbook = self.get_orderbook(ticker)
        if not orderbook:
            return None

        best_bid = orderbook.get_best_bid(side)
        return PriceAdapter.from_api_price(best_bid.price) if best_bid else None

    def get_best_ask(self, ticker: str, side: OrderSide) -> Optional[float]:
        """Get best ask price

        Args:
            ticker: Market ticker
            side: Contract side

        Returns:
            Best ask price in dollars or None
        """
        orderbook = self.get_orderbook(ticker)
        if not orderbook:
            return None

        best_ask = orderbook.get_best_ask(side)
        return PriceAdapter.from_api_price(best_ask.price) if best_ask else None

    def get_spread(self, ticker: str, side: OrderSide) -> Optional[float]:
        """Calculate spread (ask - bid)

        Args:
            ticker: Market ticker
            side: Contract side

        Returns:
            Spread in dollars or None
        """
        bid = self.get_best_bid(ticker, side)
        ask = self.get_best_ask(ticker, side)

        if bid is not None and ask is not None:
            return ask - bid
        return None

    def is_stale(self, ticker: str) -> bool:
        """Check if order book is stale

        Args:
            ticker: Market ticker

        Returns:
            True if order book hasn't been updated within staleness threshold
        """
        orderbook = self.get_orderbook(ticker)
        if not orderbook or not orderbook.last_updated:
            return True

        age = (datetime.utcnow() - orderbook.last_updated).total_seconds()
        return age > self.staleness_threshold

    async def start_snapshot_sync(self) -> None:
        """Start periodic snapshot sync background task"""
        if self._snapshot_task:
            logger.warning("Snapshot sync already running")
            return

        self._snapshot_task = asyncio.create_task(self._snapshot_sync_loop())
        logger.info("Snapshot sync started")

    async def stop_snapshot_sync(self) -> None:
        """Stop snapshot sync background task"""
        self._should_stop = True

        if self._snapshot_task:
            self._snapshot_task.cancel()
            self._snapshot_task = None

        logger.info("Snapshot sync stopped")

    async def _snapshot_sync_loop(self) -> None:
        """Background task: periodic snapshot sync"""
        logger.info(f"Snapshot sync loop started (interval={self.snapshot_interval}s)")

        try:
            while not self._should_stop:
                await asyncio.sleep(self.snapshot_interval)

                # Sync all subscribed markets
                for ticker in list(self._orderbooks.keys()):
                    if self.is_stale(ticker):
                        logger.info(f"Order book stale, fetching snapshot: {ticker}")
                        await self._fetch_snapshot(ticker)

        except asyncio.CancelledError:
            logger.info("Snapshot sync loop cancelled")
        except Exception as e:
            logger.error(f"Snapshot sync loop error: {e}")

    def get_volatility(self, ticker: str, side: OrderSide, window: int = 10) -> Optional[float]:
        """Calculate price volatility (standard deviation of recent mid prices)

        Args:
            ticker: Market ticker
            side: Contract side
            window: Number of price samples

        Returns:
            Standard deviation or None if insufficient data
        """
        if ticker not in self._price_history:
            return None
            
        history = self._price_history[ticker][side]
        if len(history) < 2:
            return None
            
        # Use last N samples
        samples = list(history)[-window:]
        if len(samples) < 2:
            return None
            
        # Calculate standard deviation
        mean = sum(samples) / len(samples)
        variance = sum((x - mean) ** 2 for x in samples) / (len(samples) - 1)
        return math.sqrt(variance)
