"""Position tracking and P&L calculation"""

from typing import Dict, Optional
from loguru import logger

from src.models.position import Position
from src.models.order import OrderSide, Fill


class PositionTracker:
    """Tracks positions across all markets"""

    def __init__(self):
        """Initialize position tracker"""
        # Structure: {market_ticker: {side: Position}}
        self._positions: Dict[str, Dict[OrderSide, Position]] = {}

        logger.info("Position tracker initialized")

    def get_position(self, market_ticker: str, side: OrderSide) -> Optional[Position]:
        """Get position for market and side

        Args:
            market_ticker: Market ticker
            side: Contract side (YES or NO)

        Returns:
            Position or None if no position exists
        """
        return self._positions.get(market_ticker, {}).get(side)

    def get_or_create_position(self, market_ticker: str, side: OrderSide) -> Position:
        """Get existing position or create new one

        Args:
            market_ticker: Market ticker
            side: Contract side

        Returns:
            Position object
        """
        if market_ticker not in self._positions:
            self._positions[market_ticker] = {}

        if side not in self._positions[market_ticker]:
            self._positions[market_ticker][side] = Position(
                market_ticker=market_ticker,
                side=side
            )

        return self._positions[market_ticker][side]

    def update_from_fill(self, fill: Fill) -> None:
        """Update position from fill

        Args:
            fill: Fill object
        """
        position = self.get_or_create_position(fill.market_ticker, fill.side)

        # Calculate fees (maker negative = rebate, taker positive = cost)
        fees = fill.maker_fee + fill.taker_fee

        # Update position
        position.update_from_fill(
            action=fill.action.value,
            fill_quantity=fill.quantity,
            fill_price=fill.price,
            fees=fees
        )

        logger.info(
            f"Position updated from fill: {fill.market_ticker} {fill.side.value} "
            f"{fill.action.value} {fill.quantity}@{fill.price:.2f} "
            f"(qty={position.quantity}, avg={position.average_price:.2f}, "
            f"realized_pnl={position.realized_pnl:.2f})"
        )

    def get_market_exposure(self, market_ticker: str) -> float:
        """Calculate total exposure (notional value) for market

        Args:
            market_ticker: Market ticker

        Returns:
            Total exposure in dollars
        """
        if market_ticker not in self._positions:
            return 0.0

        exposure = 0.0
        for position in self._positions[market_ticker].values():
            exposure += abs(position.quantity * position.average_price)

        return exposure

    def get_total_exposure(self) -> float:
        """Calculate total exposure across all markets

        Returns:
            Total exposure in dollars
        """
        total = 0.0
        for market_ticker in self._positions.keys():
            total += self.get_market_exposure(market_ticker)
        return total

    def get_inventory(self, market_ticker: str, side: OrderSide) -> int:
        """Get net inventory (signed quantity) for market/side

        Args:
            market_ticker: Market ticker
            side: Contract side

        Returns:
            Net inventory (positive = long, negative = short, 0 = flat)
        """
        position = self.get_position(market_ticker, side)
        return position.quantity if position else 0

    def get_realized_pnl(self, market_ticker: Optional[str] = None) -> float:
        """Get realized P&L

        Args:
            market_ticker: Optional market filter

        Returns:
            Realized P&L
        """
        if market_ticker:
            if market_ticker not in self._positions:
                return 0.0
            return sum(pos.realized_pnl for pos in self._positions[market_ticker].values())
        else:
            total = 0.0
            for positions in self._positions.values():
                total += sum(pos.realized_pnl for pos in positions.values())
            return total

    def get_unrealized_pnl(
        self,
        market_ticker: Optional[str] = None,
        prices: Optional[Dict[tuple[str, OrderSide], float]] = None
    ) -> float:
        """Get unrealized P&L at current prices

        Args:
            market_ticker: Optional market filter
            prices: Dict of {(market_ticker, side): current_price}

        Returns:
            Unrealized P&L
        """
        if not prices:
            prices = {}

        if market_ticker:
            if market_ticker not in self._positions:
                return 0.0

            total = 0.0
            for side, position in self._positions[market_ticker].items():
                current_price = prices.get((market_ticker, side), position.average_price)
                total += position.calculate_unrealized_pnl(current_price)
            return total
        else:
            total = 0.0
            for ticker, positions in self._positions.items():
                for side, position in positions.items():
                    current_price = prices.get((ticker, side), position.average_price)
                    total += position.calculate_unrealized_pnl(current_price)
            return total

    def get_total_pnl(
        self,
        market_ticker: Optional[str] = None,
        prices: Optional[Dict[tuple[str, OrderSide], float]] = None
    ) -> float:
        """Get total P&L (realized + unrealized)

        Args:
            market_ticker: Optional market filter
            prices: Dict of {(market_ticker, side): current_price}

        Returns:
            Total P&L
        """
        realized = self.get_realized_pnl(market_ticker)
        unrealized = self.get_unrealized_pnl(market_ticker, prices)
        return realized + unrealized

    def get_all_positions(self) -> Dict[str, Dict[OrderSide, Position]]:
        """Get all positions

        Returns:
            Dictionary of positions
        """
        return self._positions

    def clear_market(self, market_ticker: str) -> None:
        """Clear positions for a market (e.g., on settlement)

        Args:
            market_ticker: Market to clear
        """
        if market_ticker in self._positions:
            del self._positions[market_ticker]
            logger.info(f"Cleared positions for market {market_ticker}")
