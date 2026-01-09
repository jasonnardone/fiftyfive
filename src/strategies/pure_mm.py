"""Pure Market Making Strategy

Provides liquidity by quoting both bid and ask on YES and NO contracts.
Profits from bid-ask spread capture.

Features:
- Mid-price based quoting with configurable spreads
- Inventory skew adjustment (widen spreads when inventory imbalanced)
- Risk-aware position sizing
"""

from typing import List, Optional
from loguru import logger

from src.strategies.base import Strategy, Quote
from src.models.order import OrderSide
from src.models.config import StrategyConfig
from src.data.orderbook_manager import OrderBookManager
from src.risk.position_tracker import PositionTracker


class PureMarketMakingStrategy(Strategy):
    """Pure market making strategy"""

    def __init__(
        self,
        config: StrategyConfig,
        orderbook_manager: OrderBookManager,
        position_tracker: PositionTracker
    ):
        """Initialize strategy

        Args:
            config: Strategy configuration
            orderbook_manager: Order book manager
            position_tracker: Position tracker
        """
        self.config = config
        self.orderbook_manager = orderbook_manager
        self.position_tracker = position_tracker

        # Extract config
        self.base_spread = config.pricing.base_spread
        self.min_spread = config.pricing.min_spread or self.base_spread / 2
        self.max_spread = config.pricing.max_spread or self.base_spread * 3
        self.inventory_adjustment = config.pricing.inventory_adjustment
        self.inventory_multiplier = config.pricing.inventory_multiplier
        self.volatility_adjustment = config.pricing.volatility_adjustment
        self.volatility_multiplier = config.pricing.volatility_multiplier

        self.base_size = config.order_sizing.base_size
        self.max_size = config.order_sizing.max_size

        logger.info(
            f"Pure MM strategy initialized: "
            f"base_spread={self.base_spread:.4f}, "
            f"base_size={self.base_size}"
        )

    @property
    def name(self) -> str:
        return "pure_market_making"

    async def calculate_quotes(self, market_ticker: str) -> List[Quote]:
        """Calculate bid/ask quotes for both YES and NO sides

        Args:
            market_ticker: Market ticker

        Returns:
            List of Quote objects [yes_quote, no_quote]
        """
        quotes = []

        # Calculate for both sides
        for side in [OrderSide.YES, OrderSide.NO]:
            quote = await self._calculate_quote(market_ticker, side)
            if quote:
                quotes.append(quote)

        return quotes

    async def _calculate_quote(self, market_ticker: str, side: OrderSide) -> Optional[Quote]:
        """Calculate quote for specific side

        Args:
            market_ticker: Market ticker
            side: Contract side (YES or NO)

        Returns:
            Quote or None if cannot quote
        """
        # Get mid price from order book
        mid_price = self.orderbook_manager.get_mid_price(market_ticker, side)
        if mid_price is None:
            logger.debug(f"No mid price available for {market_ticker} {side.value}")
            return None

        # Calculate spread (with inventory adjustment)
        spread = self._calculate_spread(market_ticker, side, mid_price)

        # Calculate bid/ask around mid
        half_spread = spread / 2.0
        bid_price = mid_price - half_spread
        ask_price = mid_price + half_spread

        # Clamp to valid range [0.01, 0.99]
        bid_price = max(0.01, min(0.99, bid_price))
        ask_price = max(0.01, min(0.99, ask_price))

        # Ensure bid < ask
        if bid_price >= ask_price:
            logger.warning(f"Invalid quote: bid={bid_price:.2f} >= ask={ask_price:.2f}")
            return None

        # Calculate sizes
        bid_size = self._calculate_size(market_ticker, side, "bid")
        ask_size = self._calculate_size(market_ticker, side, "ask")

        quote = Quote(
            market_ticker=market_ticker,
            side=side,
            bid_price=bid_price,
            bid_size=bid_size,
            ask_price=ask_price,
            ask_size=ask_size
        )

        logger.debug(
            f"Quote: {market_ticker} {side.value} "
            f"bid={bid_price:.2f}x{bid_size} "
            f"ask={ask_price:.2f}x{ask_size} "
            f"spread={spread:.4f}"
        )

        return quote

    def _calculate_spread(self, market_ticker: str, side: OrderSide, mid_price: float) -> float:
        """Calculate spread with inventory adjustment

        Wider spreads when:
        - Inventory is imbalanced (skewed long or short)
        - Market is volatile (TODO: implement volatility tracking)

        Args:
            market_ticker: Market ticker
            side: Contract side
            mid_price: Current mid price

        Returns:
            Spread in dollars
        """
        spread = self.base_spread

        # Apply inventory adjustment
        if self.inventory_adjustment:
            inventory = self.position_tracker.get_inventory(market_ticker, side)

            if inventory != 0:
                # Calculate inventory skew ratio [-1, 1]
                max_inventory = self.config.risk.max_inventory_skew
                skew_ratio = inventory / max_inventory

                # Apply multiplier (widen spread when inventory imbalanced)
                # Example: if skew_ratio = 0.5 and multiplier = 1.5, spread *= 1.25
                inventory_factor = 1.0 + (abs(skew_ratio) * (self.inventory_multiplier - 1.0))
                spread *= inventory_factor

                logger.debug(
                    f"Inventory adjustment: {market_ticker} {side.value} "
                    f"inventory={inventory}, factor={inventory_factor:.2f}"
                )

        # Apply volatility adjustment
        if self.volatility_adjustment:
            volatility = self.orderbook_manager.get_volatility(market_ticker, side)
            if volatility is not None and volatility > 0:
                # Add volatility premium (std dev * multiplier)
                vol_premium = volatility * self.volatility_multiplier
                spread += vol_premium
                
                logger.debug(
                    f"Volatility adjustment: {market_ticker} {side.value} "
                    f"vol={volatility:.4f}, premium={vol_premium:.4f}"
                )

        # Clamp spread to min/max
        spread = max(self.min_spread, min(self.max_spread, spread))

        return spread

    def _calculate_size(self, market_ticker: str, side: OrderSide, quote_side: str) -> int:
        """Calculate order size

        Args:
            market_ticker: Market ticker
            side: Contract side
            quote_side: 'bid' or 'ask'

        Returns:
            Order size in contracts
        """
        # Start with base size
        size = self.base_size

        # TODO: Implement dynamic sizing based on:
        # - Market liquidity (larger size in liquid markets)
        # - Volatility (smaller size in volatile markets)
        # - Current inventory (reduce size when inventory high)

        # Clamp to max size
        size = min(size, self.max_size)

        return size

    async def should_quote(self, market_ticker: str) -> bool:
        """Check if should quote this market

        Args:
            market_ticker: Market ticker

        Returns:
            True if should provide quotes
        """
        # Check if order book is available and not stale
        if self.orderbook_manager.is_stale(market_ticker):
            logger.debug(f"Order book stale for {market_ticker}")
            return False

        # Check if mid prices available
        yes_mid = self.orderbook_manager.get_mid_price(market_ticker, OrderSide.YES)
        no_mid = self.orderbook_manager.get_mid_price(market_ticker, OrderSide.NO)

        if yes_mid is None or no_mid is None:
            logger.debug(f"No mid prices for {market_ticker}")
            return False

        # TODO: Additional checks:
        # - Market status (open/closed)
        # - Time to expiration (don't quote close to expiration)
        # - Liquidity filters (min volume, max spread)

        return True

    async def on_fill(self, market_ticker: str, side: OrderSide, pnl: float) -> None:
        """Callback when order is filled

        Args:
            market_ticker: Market ticker
            side: Contract side
            pnl: Realized P&L from fill
        """
        logger.info(
            f"Fill received: {market_ticker} {side.value} pnl={pnl:.2f}"
        )

        # TODO: Implement fill-based adjustments:
        # - Track fill rate (% of quotes that get filled)
        # - Detect adverse selection (fills mostly on one side)
        # - Adjust spreads based on fill patterns
