"""Self-Trade Prevention (STP) Engine

CRITICAL SAFETY FEATURE: Prevents wash trading violations by ensuring
the bot never trades with itself on opposite sides of the market.

Kalshi compliance requirement: STP MUST be enforced before every order submission.
"""

import asyncio
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from loguru import logger

from src.models.order import Order, OrderSide, OrderAction, OrderStatus
from src.api.price_adapter import PriceAdapter


@dataclass
class ConflictingOrder:
    """Represents an order that conflicts with a new order"""
    order_id: str
    market_ticker: str
    side: OrderSide
    action: OrderAction
    price: float
    quantity: int


class STPEngine:
    """Self-Trade Prevention engine

    Maintains cache of active orders and prevents crossing submissions
    that would result in self-trading.
    """

    def __init__(self, cancel_delay: float = 0.05):
        """Initialize STP engine

        Args:
            cancel_delay: Delay in seconds after cancellation before submitting new order
        """
        self.cancel_delay = cancel_delay

        # Cache of active orders by market
        # Structure: {market_ticker: {order_id: Order}}
        self._orders: Dict[str, Dict[str, Order]] = {}
        self._lock = asyncio.Lock()

        logger.info(f"STP Engine initialized with cancel_delay={cancel_delay}s")

    async def add_order(self, order: Order) -> None:
        """Add order to STP cache

        Args:
            order: Order to add
        """
        async with self._lock:
            if order.market_ticker not in self._orders:
                self._orders[order.market_ticker] = {}

            self._orders[order.market_ticker][order.order_id] = order
            logger.debug(f"STP: Added order {order.order_id} to cache ({order.market_ticker})")

    async def remove_order(self, order_id: str, market_ticker: str) -> None:
        """Remove order from STP cache

        Args:
            order_id: Order ID to remove
            market_ticker: Market ticker
        """
        async with self._lock:
            if market_ticker in self._orders:
                self._orders[market_ticker].pop(order_id, None)
                logger.debug(f"STP: Removed order {order_id} from cache ({market_ticker})")

                # Clean up empty market
                if not self._orders[market_ticker]:
                    del self._orders[market_ticker]

    async def update_on_fill(
        self,
        order_id: str,
        market_ticker: str,
        filled_quantity: int
    ) -> None:
        """Update order in cache after partial/full fill

        Args:
            order_id: Order ID
            market_ticker: Market ticker
            filled_quantity: Quantity filled
        """
        async with self._lock:
            if market_ticker in self._orders and order_id in self._orders[market_ticker]:
                order = self._orders[market_ticker][order_id]
                order.filled_quantity += filled_quantity
                order.remaining_quantity -= filled_quantity

                # Remove if fully filled
                if order.remaining_quantity <= 0:
                    await self.remove_order(order_id, market_ticker)
                    logger.debug(f"STP: Order {order_id} fully filled, removed from cache")

    async def can_submit_order(self, new_order: Order) -> tuple[bool, List[ConflictingOrder]]:
        """Check if order can be submitted without self-trading

        Args:
            new_order: Proposed order to submit

        Returns:
            Tuple of (can_submit, conflicting_orders)
            - can_submit: True if order can be submitted immediately
            - conflicting_orders: List of orders that would cause self-trading
        """
        async with self._lock:
            conflicts = await self._find_conflicts(new_order)

            if conflicts:
                logger.warning(
                    f"STP: Order would cross with {len(conflicts)} existing order(s) "
                    f"on {new_order.market_ticker}"
                )
                return False, conflicts
            else:
                return True, []

    async def _find_conflicts(self, new_order: Order) -> List[ConflictingOrder]:
        """Find orders that would cross with new order

        A conflict occurs when:
        1. Same market
        2. Opposite side of trade (buy crosses with sell)
        3. Prices would match or cross

        Args:
            new_order: Proposed order

        Returns:
            List of conflicting orders
        """
        conflicts = []

        # Get orders for this market
        market_orders = self._orders.get(new_order.market_ticker, {})

        for existing_order in market_orders.values():
            # Skip if not active
            if not existing_order.is_active:
                continue

            # Check for conflict
            if self._would_cross(new_order, existing_order):
                conflicts.append(
                    ConflictingOrder(
                        order_id=existing_order.order_id,
                        market_ticker=existing_order.market_ticker,
                        side=existing_order.side,
                        action=existing_order.action,
                        price=existing_order.price,
                        quantity=existing_order.remaining_quantity
                    )
                )

        return conflicts

    def _would_cross(self, new_order: Order, existing_order: Order) -> bool:
        """Check if two orders would cross (result in self-trading)

        Args:
            new_order: Proposed new order
            existing_order: Existing active order

        Returns:
            True if orders would cross
        """
        # Same market required
        if new_order.market_ticker != existing_order.market_ticker:
            return False

        # Same side = no conflict (both buying or both selling same contract)
        if new_order.side == existing_order.side and new_order.action == existing_order.action:
            return False

        # Check price crossing
        # For YES contracts:
        #   - New BUY @ price X crosses with existing SELL @ price <= X
        #   - New SELL @ price X crosses with existing BUY @ price >= X
        # For NO contracts: same logic applies

        if new_order.action == OrderAction.BUY and existing_order.action == OrderAction.SELL:
            # New buy would cross with existing sell if new_price >= existing_price
            if new_order.price >= existing_order.price:
                return True

        elif new_order.action == OrderAction.SELL and existing_order.action == OrderAction.BUY:
            # New sell would cross with existing buy if new_price <= existing_price
            if new_order.price <= existing_order.price:
                return True

        # Also check complementarity constraint: yes_price + no_price >= 1.00
        if new_order.side != existing_order.side:
            yes_price = new_order.price if new_order.side == OrderSide.YES else existing_order.price
            no_price = new_order.price if new_order.side == OrderSide.NO else existing_order.price

            if not PriceAdapter.validate_complementarity(yes_price, no_price):
                logger.warning(
                    f"STP: Complementarity violation detected: "
                    f"YES={yes_price:.2f} + NO={no_price:.2f} < 1.00"
                )
                return True

        return False

    async def submit_with_stp(
        self,
        new_order: Order,
        cancel_callback,
        submit_callback
    ) -> Optional[Order]:
        """Submit order with STP enforcement

        If conflicts exist:
        1. Cancel all conflicting orders
        2. Wait cancel_delay seconds
        3. Submit new order

        Args:
            new_order: Order to submit
            cancel_callback: Async function(order_id) -> None to cancel order
            submit_callback: Async function(order) -> Order to submit order

        Returns:
            Submitted order or None if submission failed
        """
        # Check for conflicts
        can_submit, conflicts = await self.can_submit_order(new_order)

        if can_submit:
            # No conflicts - submit immediately
            logger.debug(f"STP: No conflicts, submitting order immediately")
            return await submit_callback(new_order)

        # Conflicts exist - cancel them first
        logger.info(f"STP: Cancelling {len(conflicts)} conflicting order(s)")

        for conflict in conflicts:
            try:
                await cancel_callback(conflict.order_id)
                await self.remove_order(conflict.order_id, conflict.market_ticker)
                logger.info(f"STP: Cancelled conflicting order {conflict.order_id}")
            except Exception as e:
                logger.error(f"STP: Failed to cancel order {conflict.order_id}: {e}")

        # Wait for cancellations to propagate
        logger.debug(f"STP: Waiting {self.cancel_delay}s for cancellations to propagate")
        await asyncio.sleep(self.cancel_delay)

        # Submit new order
        try:
            submitted_order = await submit_callback(new_order)
            logger.info(f"STP: Submitted order {submitted_order.order_id} after cancellations")
            return submitted_order
        except Exception as e:
            logger.error(f"STP: Failed to submit order after cancellations: {e}")
            return None

    async def get_active_orders(self, market_ticker: Optional[str] = None) -> List[Order]:
        """Get active orders from cache

        Args:
            market_ticker: Optional market filter

        Returns:
            List of active orders
        """
        async with self._lock:
            if market_ticker:
                return list(self._orders.get(market_ticker, {}).values())
            else:
                orders = []
                for market_orders in self._orders.values():
                    orders.extend(market_orders.values())
                return orders

    async def clear_market(self, market_ticker: str) -> None:
        """Clear all orders for a market (e.g., on market settlement)

        Args:
            market_ticker: Market to clear
        """
        async with self._lock:
            if market_ticker in self._orders:
                count = len(self._orders[market_ticker])
                del self._orders[market_ticker]
                logger.info(f"STP: Cleared {count} orders for market {market_ticker}")
