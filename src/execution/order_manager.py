"""Order manager with STP and risk integration

Orchestrates order placement by:
1. Checking risk limits
2. Enforcing self-trade prevention
3. Submitting orders via API
4. Tracking active orders
5. Processing fills
"""

import asyncio
from typing import Dict, List, Optional, Set
from datetime import datetime
from loguru import logger
import uuid

from src.models.order import Order, OrderSide, OrderAction, OrderStatus, Fill
from src.api.client import KalshiClient
from src.api.price_adapter import PriceAdapter
from src.execution.stp_engine import STPEngine
from src.risk.monitor import RiskMonitor
from src.risk.position_tracker import PositionTracker


class OrderManager:
    """Manages order lifecycle with STP and risk checks"""

    def __init__(
        self,
        api_client: KalshiClient,
        stp_engine: STPEngine,
        risk_monitor: RiskMonitor,
        position_tracker: PositionTracker
    ):
        """Initialize order manager

        Args:
            api_client: REST API client
            stp_engine: Self-trade prevention engine
            risk_monitor: Risk monitor
            position_tracker: Position tracker
        """
        self.api_client = api_client
        self.stp_engine = stp_engine
        self.risk_monitor = risk_monitor
        self.position_tracker = position_tracker

        # Active orders cache
        self._active_orders: Dict[str, Order] = {}

        # Order placement statistics
        self._orders_placed = 0
        self._orders_rejected = 0
        self._orders_filled = 0
        self._maker_fills = 0

        logger.info("Order manager initialized")

    async def place_order(
        self,
        market_ticker: str,
        side: OrderSide,
        action: OrderAction,
        price: float,
        quantity: int
    ) -> Optional[Order]:
        """Place order with STP and risk checks

        Args:
            market_ticker: Market ticker
            side: Contract side (YES or NO)
            action: Buy or sell
            price: Price in dollars [0.01-0.99]
            quantity: Number of contracts

        Returns:
            Order object if successful, None otherwise
        """
        # Create order object
        order = Order(
            client_order_id=str(uuid.uuid4()),
            market_ticker=market_ticker,
            side=side,
            action=action,
            price=price,
            quantity=quantity,
            status=OrderStatus.PENDING
        )

        logger.info(
            f"Placing order: {market_ticker} {side.value} {action.value} "
            f"{quantity}@{price:.2f}"
        )

        # Step 1: Check risk limits
        is_allowed, reason = await self.risk_monitor.check_order_risk(order)
        if not is_allowed:
            logger.warning(f"Order rejected by risk monitor: {reason}")
            self._orders_rejected += 1
            await self.risk_monitor.record_request(is_error=True)
            return None

        # Step 2: Submit with STP
        try:
            submitted_order = await self.stp_engine.submit_with_stp(
                new_order=order,
                cancel_callback=self._cancel_order_api,
                submit_callback=self._submit_order_api
            )

            if submitted_order:
                # Add to STP cache and active orders
                await self.stp_engine.add_order(submitted_order)
                self._active_orders[submitted_order.order_id] = submitted_order
                self._orders_placed += 1

                logger.info(
                    f"Order placed successfully: {submitted_order.order_id} "
                    f"({market_ticker} {side.value} {action.value} {quantity}@{price:.2f})"
                )

                await self.risk_monitor.record_request(is_error=False)
                return submitted_order
            else:
                logger.error("Order submission failed")
                self._orders_rejected += 1
                await self.risk_monitor.record_request(is_error=True)
                return None

        except Exception as e:
            logger.error(f"Order placement error: {e}")
            self._orders_rejected += 1
            await self.risk_monitor.record_request(is_error=True)
            return None

    async def _submit_order_api(self, order: Order) -> Order:
        """Submit order via API

        Args:
            order: Order to submit

        Returns:
            Order with exchange order ID

        Raises:
            Exception: On API error
        """
        # Convert price to cents
        price_cents = PriceAdapter.to_api_price(order.price)

        # Determine which price parameter to use
        if order.side == OrderSide.YES:
            yes_price = price_cents
            no_price = None
        else:
            yes_price = None
            no_price = price_cents

        # Submit via API
        response = await self.api_client.place_order(
            ticker=order.market_ticker,
            side=order.side.value,
            action=order.action.value,
            count=order.quantity,
            yes_price=yes_price,
            no_price=no_price,
            client_order_id=order.client_order_id
        )

        # Parse response
        order.order_id = response.get('order_id')
        order.status = OrderStatus.OPEN
        order.created_at = datetime.utcnow()

        return order

    async def _cancel_order_api(self, order_id: str) -> None:
        """Cancel order via API

        Args:
            order_id: Order ID to cancel
        """
        await self.api_client.cancel_order(order_id)

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel order

        Args:
            order_id: Order ID to cancel

        Returns:
            True if cancellation successful
        """
        try:
            await self._cancel_order_api(order_id)

            # Update local state
            if order_id in self._active_orders:
                order = self._active_orders[order_id]
                order.status = OrderStatus.CANCELLED
                await self.stp_engine.remove_order(order_id, order.market_ticker)
                del self._active_orders[order_id]

            logger.info(f"Order cancelled: {order_id}")
            return True

        except Exception as e:
            logger.error(f"Order cancellation failed: {e}")
            return False

    async def cancel_all_orders(self, market_ticker: Optional[str] = None) -> int:
        """Cancel all orders (optionally filtered by market)

        Args:
            market_ticker: Optional market filter

        Returns:
            Number of orders cancelled
        """
        orders_to_cancel = []

        for order_id, order in self._active_orders.items():
            if market_ticker is None or order.market_ticker == market_ticker:
                orders_to_cancel.append(order_id)

        logger.info(f"Cancelling {len(orders_to_cancel)} order(s)")

        # Cancel in parallel
        results = await asyncio.gather(
            *[self.cancel_order(order_id) for order_id in orders_to_cancel],
            return_exceptions=True
        )

        cancelled = sum(1 for r in results if r is True)
        logger.info(f"Cancelled {cancelled}/{len(orders_to_cancel)} order(s)")

        return cancelled

    async def sync_orders(self) -> None:
        """Sync orders from exchange (on startup or after disconnect)"""
        logger.info("Syncing orders from exchange")

        try:
            # Fetch all active orders from API
            orders = await self.api_client.get_orders(status='open')

            # Update local cache and STP
            synced_count = 0
            for order_data in orders:
                order = self._parse_order_from_api(order_data)

                if order and order.is_active:
                    self._active_orders[order.order_id] = order
                    await self.stp_engine.add_order(order)
                    synced_count += 1

            logger.info(f"Synced {synced_count} active order(s)")

        except Exception as e:
            logger.error(f"Order sync failed: {e}")

    async def process_fills(self) -> List[Fill]:
        """Fetch and process recent fills

        Returns:
            List of new fills
        """
        try:
            # Fetch recent fills
            fills_data = await self.api_client.get_fills(limit=100)

            fills = []
            for fill_data in fills_data:
                fill = self._parse_fill_from_api(fill_data)
                if fill:
                    # Update position
                    self.position_tracker.update_from_fill(fill)

                    # Update STP cache
                    await self.stp_engine.update_on_fill(
                        order_id=fill.order_id,
                        market_ticker=fill.market_ticker,
                        filled_quantity=fill.quantity
                    )

                    # Remove from active if fully filled
                    if fill.order_id in self._active_orders:
                        order = self._active_orders[fill.order_id]
                        order.filled_quantity += fill.quantity
                        order.remaining_quantity -= fill.quantity

                        if order.remaining_quantity <= 0:
                            order.status = OrderStatus.FILLED
                            del self._active_orders[fill.order_id]
                            await self.stp_engine.remove_order(fill.order_id, fill.market_ticker)

                    self._orders_filled += 1
                    if fill.is_maker:
                        self._maker_fills += 1
                        
                    fills.append(fill)

                    logger.info(
                        f"Fill processed: {fill.market_ticker} {fill.side.value} "
                        f"{fill.action.value} {fill.quantity}@{fill.price:.2f} "
                        f"(fees={fill.maker_fee + fill.taker_fee:.2f})"
                    )

            return fills

        except Exception as e:
            logger.error(f"Fill processing error: {e}")
            return []

    def _parse_order_from_api(self, order_data: Dict) -> Optional[Order]:
        """Parse order from API response

        Args:
            order_data: Order data from API

        Returns:
            Order object or None if parsing fails
        """
        try:
            # Parse price (convert cents to dollars)
            yes_price = order_data.get('yes_price')
            no_price = order_data.get('no_price')

            if yes_price:
                price = PriceAdapter.from_api_price(yes_price)
                side = OrderSide.YES
            elif no_price:
                price = PriceAdapter.from_api_price(no_price)
                side = OrderSide.NO
            else:
                return None

            order = Order(
                order_id=order_data['order_id'],
                client_order_id=order_data.get('client_order_id', ''),
                market_ticker=order_data['ticker'],
                side=side,
                action=OrderAction(order_data['action']),
                price=price,
                quantity=order_data['quantity'],
                filled_quantity=order_data.get('filled_quantity', 0),
                remaining_quantity=order_data.get('remaining_quantity', order_data['quantity']),
                status=OrderStatus(order_data['status'])
            )

            return order

        except Exception as e:
            logger.error(f"Failed to parse order: {e}")
            return None

    def _parse_fill_from_api(self, fill_data: Dict) -> Optional[Fill]:
        """Parse fill from API response

        Args:
            fill_data: Fill data from API

        Returns:
            Fill object or None if parsing fails
        """
        try:
            # Parse price
            yes_price = fill_data.get('yes_price')
            no_price = fill_data.get('no_price')

            if yes_price:
                price = PriceAdapter.from_api_price(yes_price)
                side = OrderSide.YES
            elif no_price:
                price = PriceAdapter.from_api_price(no_price)
                side = OrderSide.NO
            else:
                return None

            # Calculate fees (Kalshi: -0.5% maker, +0.7% taker)
            # Negative = rebate, Positive = cost
            is_taker = fill_data.get('is_taker', False)
            trade_value = price * fill_data['count']

            if is_taker:
                maker_fee = 0.0
                taker_fee = trade_value * 0.007  # 0.7%
            else:
                maker_fee = -trade_value * 0.005  # -0.5% (rebate)
                taker_fee = 0.0

            fill = Fill(
                fill_id=fill_data['trade_id'],
                order_id=fill_data['order_id'],
                market_ticker=fill_data['ticker'],
                side=side,
                action=OrderAction(fill_data['action']),
                price=price,
                quantity=fill_data['count'],
                maker_fee=maker_fee,
                taker_fee=taker_fee,
                filled_at=datetime.fromisoformat(fill_data['created_time'].replace('Z', '+00:00'))
            )

            return fill

        except Exception as e:
            logger.error(f"Failed to parse fill: {e}")
            return None

    def get_active_orders(self, market_ticker: Optional[str] = None) -> List[Order]:
        """Get active orders

        Args:
            market_ticker: Optional market filter

        Returns:
            List of active orders
        """
        if market_ticker:
            return [
                order for order in self._active_orders.values()
                if order.market_ticker == market_ticker
            ]
        else:
            return list(self._active_orders.values())

    def get_statistics(self) -> Dict:
        """Get order placement statistics

        Returns:
            Statistics dictionary
        """
        return {
            'orders_placed': self._orders_placed,
            'orders_rejected': self._orders_rejected,
            'orders_filled': self._orders_filled,
            'maker_fills': self._maker_fills,
            'active_orders': len(self._active_orders)
        }
