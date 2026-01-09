"""Base strategy interface"""

from abc import ABC, abstractmethod
from typing import List, Optional, Tuple
from dataclasses import dataclass

from src.models.order import Order, OrderSide


@dataclass
class Quote:
    """Bid/ask quote for a market"""
    market_ticker: str
    side: OrderSide

    # Bid side
    bid_price: Optional[float] = None
    bid_size: int = 0

    # Ask side
    ask_price: Optional[float] = None
    ask_size: int = 0

    @property
    def spread(self) -> Optional[float]:
        """Calculate spread"""
        if self.bid_price is not None and self.ask_price is not None:
            return self.ask_price - self.bid_price
        return None

    @property
    def mid_price(self) -> Optional[float]:
        """Calculate mid price"""
        if self.bid_price is not None and self.ask_price is not None:
            return (self.bid_price + self.ask_price) / 2.0
        return None


class Strategy(ABC):
    """Base strategy interface"""

    @abstractmethod
    async def calculate_quotes(self, market_ticker: str) -> List[Quote]:
        """Calculate quotes for market

        Args:
            market_ticker: Market ticker

        Returns:
            List of quotes (typically YES and NO quotes)
        """
        pass

    @abstractmethod
    async def should_quote(self, market_ticker: str) -> bool:
        """Check if strategy should quote this market

        Args:
            market_ticker: Market ticker

        Returns:
            True if should provide quotes
        """
        pass

    @abstractmethod
    async def on_fill(self, market_ticker: str, side: OrderSide, pnl: float) -> None:
        """Callback when order is filled

        Args:
            market_ticker: Market ticker
            side: Contract side
            pnl: Realized P&L from fill
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Strategy name"""
        pass
