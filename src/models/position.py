"""Position tracking models"""

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime

from src.models.order import OrderSide


@dataclass
class Position:
    """Position in a market"""
    market_ticker: str
    side: OrderSide  # YES or NO contract

    # Quantities
    quantity: int = 0  # Net position (positive = long, negative = short)
    total_cost: float = 0.0  # Total cost basis

    # P&L tracking
    realized_pnl: float = 0.0  # Realized P&L from closed positions
    unrealized_pnl: float = 0.0  # Unrealized P&L from open positions

    # Fees
    total_fees: float = 0.0  # Cumulative fees paid

    # Timestamps
    opened_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @property
    def average_price(self) -> float:
        """Calculate average entry price"""
        if self.quantity == 0:
            return 0.0
        return self.total_cost / abs(self.quantity)

    @property
    def market_value(self, current_price: float = 0.0) -> float:
        """Calculate current market value

        Args:
            current_price: Current market price

        Returns:
            Market value of position
        """
        return self.quantity * current_price

    @property
    def is_flat(self) -> bool:
        """Check if position is flat (no exposure)"""
        return self.quantity == 0

    def update_from_fill(
        self,
        action: str,
        fill_quantity: int,
        fill_price: float,
        fees: float
    ) -> None:
        """Update position from fill

        Args:
            action: 'buy' or 'sell'
            fill_quantity: Quantity filled
            fill_price: Fill price
            fees: Fees paid
        """
        # Update fees
        self.total_fees += abs(fees)

        # Calculate fill cost
        fill_cost = fill_quantity * fill_price

        if action == "buy":
            # Buying increases position
            if self.quantity >= 0:
                # Adding to long or opening long
                self.quantity += fill_quantity
                self.total_cost += fill_cost
            else:
                # Reducing short position
                if fill_quantity <= abs(self.quantity):
                    # Partially or fully closing short
                    pnl = (self.average_price - fill_price) * fill_quantity
                    self.realized_pnl += pnl
                    self.quantity += fill_quantity
                    self.total_cost += fill_cost
                else:
                    # Closing short and opening long
                    close_qty = abs(self.quantity)
                    open_qty = fill_quantity - close_qty

                    # Realize P&L on closed portion
                    pnl = (self.average_price - fill_price) * close_qty
                    self.realized_pnl += pnl

                    # Open new long position
                    self.quantity = open_qty
                    self.total_cost = open_qty * fill_price

        else:  # action == "sell"
            # Selling decreases position
            if self.quantity <= 0:
                # Adding to short or opening short
                self.quantity -= fill_quantity
                self.total_cost += fill_cost
            else:
                # Reducing long position
                if fill_quantity <= self.quantity:
                    # Partially or fully closing long
                    pnl = (fill_price - self.average_price) * fill_quantity
                    self.realized_pnl += pnl
                    self.quantity -= fill_quantity
                    self.total_cost -= fill_cost
                else:
                    # Closing long and opening short
                    close_qty = self.quantity
                    open_qty = fill_quantity - close_qty

                    # Realize P&L on closed portion
                    pnl = (fill_price - self.average_price) * close_qty
                    self.realized_pnl += pnl

                    # Open new short position
                    self.quantity = -open_qty
                    self.total_cost = open_qty * fill_price

        self.updated_at = datetime.utcnow()

    def calculate_unrealized_pnl(self, current_price: float) -> float:
        """Calculate unrealized P&L at current price

        Args:
            current_price: Current market price

        Returns:
            Unrealized P&L
        """
        if self.quantity == 0:
            return 0.0

        if self.quantity > 0:
            # Long position
            self.unrealized_pnl = (current_price - self.average_price) * self.quantity
        else:
            # Short position
            self.unrealized_pnl = (self.average_price - current_price) * abs(self.quantity)

        return self.unrealized_pnl

    @property
    def total_pnl(self) -> float:
        """Total P&L (realized + unrealized)"""
        return self.realized_pnl + self.unrealized_pnl

    @property
    def net_pnl(self) -> float:
        """Net P&L after fees"""
        return self.total_pnl - self.total_fees
