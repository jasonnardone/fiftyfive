"""Order and related data models"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional
from datetime import datetime


class OrderSide(str, Enum):
    """Side of the market (yes/no contract)"""
    YES = "yes"
    NO = "no"


class OrderAction(str, Enum):
    """Buy or sell action"""
    BUY = "buy"
    SELL = "sell"


class OrderStatus(str, Enum):
    """Order lifecycle status"""
    PENDING = "pending"
    OPEN = "resting"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "canceled"
    REJECTED = "rejected"


class MarketStatus(str, Enum):
    """Market lifecycle status"""
    OPEN = "open"
    CLOSED = "closed"
    SETTLED = "settled"


@dataclass
class PriceLevel:
    """Order book price level"""
    price: int  # Price in cents (1-99)
    quantity: int  # Number of contracts

    def __post_init__(self):
        """Validate price level"""
        if not 1 <= self.price <= 99:
            raise ValueError(f"Price must be 1-99 cents, got {self.price}")
        if self.quantity < 0:
            raise ValueError(f"Quantity must be >= 0, got {self.quantity}")


@dataclass
class Order:
    """Order entity"""
    # Exchange identifiers
    order_id: Optional[str] = None  # Exchange order ID
    client_order_id: str = ""  # Client-generated UUID

    # Market and position
    market_ticker: str = ""
    side: OrderSide = OrderSide.YES
    action: OrderAction = OrderAction.BUY

    # Pricing and sizing
    price: float = 0.0  # [0.01-0.99]
    quantity: int = 0
    filled_quantity: int = 0
    remaining_quantity: int = 0

    # Status
    status: OrderStatus = OrderStatus.PENDING
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # Metadata
    error_message: Optional[str] = None

    def __post_init__(self):
        """Validate order"""
        if self.price < 0.01 or self.price > 0.99:
            raise ValueError(f"Price must be 0.01-0.99, got {self.price}")
        if self.quantity < 1:
            raise ValueError(f"Quantity must be >= 1, got {self.quantity}")
        if not self.client_order_id:
            import uuid
            self.client_order_id = str(uuid.uuid4())
        if self.remaining_quantity == 0 and self.quantity > 0:
            self.remaining_quantity = self.quantity

    @property
    def is_active(self) -> bool:
        """Check if order is active (can be filled or cancelled)"""
        return self.status in (OrderStatus.OPEN, OrderStatus.PARTIALLY_FILLED)

    @property
    def is_terminal(self) -> bool:
        """Check if order is in terminal state"""
        return self.status in (OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED)


@dataclass
class Fill:
    """Fill entity (partial or complete order execution)"""
    fill_id: str
    order_id: str
    market_ticker: str
    side: OrderSide
    action: OrderAction

    # Execution details
    price: float  # Execution price [0.01-0.99]
    quantity: int  # Filled quantity

    # Fees
    maker_fee: float = 0.0  # Negative (rebate)
    taker_fee: float = 0.0  # Positive (cost)

    # Timestamp
    filled_at: Optional[datetime] = None

    @property
    def net_proceeds(self) -> float:
        """Calculate net proceeds after fees"""
        gross = self.price * self.quantity
        return gross - self.maker_fee - self.taker_fee

    @property
    def is_maker(self) -> bool:
        """Check if this was a maker fill (rebate)"""
        return self.maker_fee < 0


@dataclass
class OrderBook:
    """Order book state for a market"""
    market_ticker: str

    # Bids (buy orders)
    yes_bids: list[PriceLevel]  # YES buy orders (descending price)
    no_bids: list[PriceLevel]   # NO buy orders (descending price)

    # Asks (sell orders)
    yes_asks: list[PriceLevel]  # YES sell orders (ascending price)
    no_asks: list[PriceLevel]   # NO sell orders (ascending price)

    # Metadata
    sequence: int = 0  # Sequence number for delta validation
    last_updated: Optional[datetime] = None

    def __post_init__(self):
        """Initialize empty lists if not provided"""
        self.yes_bids = self.yes_bids or []
        self.no_bids = self.no_bids or []
        self.yes_asks = self.yes_asks or []
        self.no_asks = self.no_asks or []

    def get_best_bid(self, side: OrderSide) -> Optional[PriceLevel]:
        """Get best bid for side"""
        levels = self.yes_bids if side == OrderSide.YES else self.no_bids
        return levels[0] if levels else None

    def get_best_ask(self, side: OrderSide) -> Optional[PriceLevel]:
        """Get best ask for side"""
        levels = self.yes_asks if side == OrderSide.YES else self.no_asks
        return levels[0] if levels else None

    def get_mid_price(self, side: OrderSide) -> Optional[float]:
        """Calculate mid price for side"""
        best_bid = self.get_best_bid(side)
        best_ask = self.get_best_ask(side)

        if best_bid and best_ask:
            return (best_bid.price + best_ask.price) / 200.0  # Convert cents to dollars
        return None

    def apply_delta(self, side: OrderSide, action: str, deltas: list[list[int]]) -> None:
        """Apply order book delta update

        Args:
            side: YES or NO
            action: 'bid' or 'ask'
            deltas: List of [price_cents, quantity] updates
        """
        # Select the correct book side
        if side == OrderSide.YES:
            book = self.yes_bids if action == 'bid' else self.yes_asks
        else:
            book = self.no_bids if action == 'bid' else self.no_asks

        # Apply each delta
        for price_cents, quantity in deltas:
            # Remove existing level
            book[:] = [level for level in book if level.price != price_cents]

            # Add new level if quantity > 0
            if quantity > 0:
                book.append(PriceLevel(price=price_cents, quantity=quantity))

        # Re-sort
        if action == 'bid':
            book.sort(key=lambda x: x.price, reverse=True)  # Descending for bids
        else:
            book.sort(key=lambda x: x.price)  # Ascending for asks

        # Update timestamp
        self.last_updated = datetime.utcnow()
