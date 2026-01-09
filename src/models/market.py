"""Market data models"""

from dataclasses import dataclass
from typing import Optional
from datetime import datetime

from src.models.order import MarketStatus


@dataclass
class Market:
    """Market entity"""
    ticker: str
    title: str
    category: str
    status: MarketStatus

    # Contract details
    yes_sub_title: Optional[str] = None
    no_sub_title: Optional[str] = None

    # Market data
    volume: int = 0  # 24h volume
    open_interest: int = 0
    liquidity: int = 0

    # Price data
    yes_bid: Optional[float] = None
    yes_ask: Optional[float] = None
    no_bid: Optional[float] = None
    no_ask: Optional[float] = None
    last_price: Optional[float] = None

    # Timing
    close_time: Optional[datetime] = None
    expiration_time: Optional[datetime] = None
    created_at: Optional[datetime] = None

    # Settlement
    result: Optional[str] = None  # 'yes' or 'no'
    settled_at: Optional[datetime] = None

    @property
    def is_active(self) -> bool:
        """Check if market is actively trading"""
        return self.status == MarketStatus.OPEN

    @property
    def is_settled(self) -> bool:
        """Check if market is settled"""
        return self.status == MarketStatus.SETTLED

    @property
    def yes_spread(self) -> Optional[float]:
        """Calculate YES spread (ask - bid)"""
        if self.yes_bid is not None and self.yes_ask is not None:
            return self.yes_ask - self.yes_bid
        return None

    @property
    def no_spread(self) -> Optional[float]:
        """Calculate NO spread (ask - bid)"""
        if self.no_bid is not None and self.no_ask is not None:
            return self.no_ask - self.no_bid
        return None

    @property
    def yes_mid(self) -> Optional[float]:
        """Calculate YES mid price"""
        if self.yes_bid is not None and self.yes_ask is not None:
            return (self.yes_bid + self.yes_ask) / 2.0
        return None

    @property
    def no_mid(self) -> Optional[float]:
        """Calculate NO mid price"""
        if self.no_bid is not None and self.no_ask is not None:
            return (self.no_bid + self.no_ask) / 2.0
        return None

    def is_liquid(self, min_volume: float = 10000, max_spread: float = 0.10) -> bool:
        """Check if market meets liquidity criteria

        Args:
            min_volume: Minimum 24h volume
            max_spread: Maximum allowed spread

        Returns:
            True if market is sufficiently liquid
        """
        # Check volume
        if self.volume < min_volume:
            return False

        # Check spread
        yes_spread = self.yes_spread
        no_spread = self.no_spread

        if yes_spread is not None and yes_spread > max_spread:
            return False
        if no_spread is not None and no_spread > max_spread:
            return False

        return True

    def update_from_orderbook(
        self,
        yes_bid: Optional[float],
        yes_ask: Optional[float],
        no_bid: Optional[float],
        no_ask: Optional[float]
    ) -> None:
        """Update market data from order book

        Args:
            yes_bid: Best YES bid
            yes_ask: Best YES ask
            no_bid: Best NO bid
            no_ask: Best NO ask
        """
        self.yes_bid = yes_bid
        self.yes_ask = yes_ask
        self.no_bid = no_bid
        self.no_ask = no_ask
