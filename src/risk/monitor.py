"""Risk monitoring and kill switch

CRITICAL SAFETY FEATURE: Monitors risk limits and triggers kill switch
to prevent catastrophic losses.
"""

import asyncio
from typing import Optional, Callable
from dataclasses import dataclass
from datetime import datetime, date
from loguru import logger

from src.models.config import RiskConfig
from src.models.order import Order
from src.risk.position_tracker import PositionTracker


@dataclass
class RiskMetrics:
    """Risk metrics snapshot"""
    timestamp: datetime
    total_exposure: float
    total_pnl: float
    daily_pnl: float
    error_count: int
    total_requests: int
    consecutive_losses: int
    kill_switch_active: bool


class RiskMonitor:
    """Monitors risk limits and triggers kill switch"""

    def __init__(
        self,
        config: RiskConfig,
        position_tracker: PositionTracker,
        kill_switch_callback: Optional[Callable] = None
    ):
        """Initialize risk monitor

        Args:
            config: Risk configuration
            position_tracker: Position tracker instance
            kill_switch_callback: Async callback to trigger kill switch
        """
        self.config = config
        self.position_tracker = position_tracker
        self.kill_switch_callback = kill_switch_callback

        # Daily tracking
        self._daily_start_pnl = 0.0
        self._daily_start_date = date.today()

        # Error tracking
        self._error_count = 0
        self._total_requests = 0

        # Loss tracking
        self._consecutive_losses = 0
        self._last_trade_pnl = 0.0

        # Kill switch state
        self.kill_switch_active = False
        self._lock = asyncio.Lock()

        logger.info(
            f"Risk monitor initialized: "
            f"max_exposure_per_market={config.max_exposure_per_market}, "
            f"max_total_exposure={config.max_total_exposure}, "
            f"daily_loss_limit={config.daily_loss_limit}"
        )

    async def check_order_risk(self, order: Order) -> tuple[bool, Optional[str]]:
        """Check if order passes risk limits

        Args:
            order: Proposed order

        Returns:
            Tuple of (is_allowed, reason)
            - is_allowed: True if order can be submitted
            - reason: Reason for rejection if not allowed
        """
        async with self._lock:
            # Check kill switch
            if self.kill_switch_active:
                return False, "Kill switch is active"

            # Check market exposure
            current_exposure = self.position_tracker.get_market_exposure(order.market_ticker)
            order_value = order.quantity * order.price
            new_exposure = current_exposure + order_value

            if new_exposure > self.config.max_exposure_per_market:
                return False, (
                    f"Market exposure limit exceeded: "
                    f"{new_exposure:.2f} > {self.config.max_exposure_per_market:.2f}"
                )

            # Check total exposure
            total_exposure = self.position_tracker.get_total_exposure()
            new_total_exposure = total_exposure + order_value

            if new_total_exposure > self.config.max_total_exposure:
                return False, (
                    f"Total exposure limit exceeded: "
                    f"{new_total_exposure:.2f} > {self.config.max_total_exposure:.2f}"
                )

            # Check inventory limits
            inventory = self.position_tracker.get_inventory(order.market_ticker, order.side)
            new_inventory = inventory + (order.quantity if order.action.value == "buy" else -order.quantity)

            if abs(new_inventory) > self.config.max_inventory_skew:
                return False, (
                    f"Inventory skew limit exceeded: "
                    f"|{new_inventory}| > {self.config.max_inventory_skew}"
                )

            # Check contracts per side
            if abs(new_inventory) > self.config.max_contracts_per_side:
                return False, (
                    f"Contracts per side limit exceeded: "
                    f"|{new_inventory}| > {self.config.max_contracts_per_side}"
                )

            return True, None

    async def check_daily_loss(self) -> bool:
        """Check if daily loss limit exceeded

        Returns:
            True if limit exceeded (should trigger kill switch)
        """
        # Reset daily tracking if new day
        today = date.today()
        if today != self._daily_start_date:
            self._daily_start_pnl = self.position_tracker.get_total_pnl()
            self._daily_start_date = today
            self._consecutive_losses = 0
            logger.info(f"Daily tracking reset: start_pnl={self._daily_start_pnl:.2f}")

        # Calculate daily P&L
        current_pnl = self.position_tracker.get_total_pnl()
        daily_pnl = current_pnl - self._daily_start_pnl

        # Check loss limit
        if daily_pnl < -self.config.daily_loss_limit:
            logger.critical(
                f"DAILY LOSS LIMIT EXCEEDED: {daily_pnl:.2f} < -{self.config.daily_loss_limit:.2f}"
            )
            return True

        return False

    async def check_error_rate(self) -> bool:
        """Check if error rate threshold exceeded

        Returns:
            True if threshold exceeded (should trigger kill switch)
        """
        if self._total_requests < 10:
            return False  # Need minimum requests for statistical significance

        error_rate = self._error_count / self._total_requests

        if error_rate > self.config.error_rate_threshold:
            logger.critical(
                f"ERROR RATE THRESHOLD EXCEEDED: "
                f"{error_rate:.2%} > {self.config.error_rate_threshold:.2%} "
                f"({self._error_count}/{self._total_requests})"
            )
            return True

        return False

    async def check_consecutive_losses(self) -> bool:
        """Check if consecutive loss threshold exceeded

        Returns:
            True if threshold exceeded (should trigger kill switch)
        """
        if self._consecutive_losses >= self.config.consecutive_losses:
            logger.critical(
                f"CONSECUTIVE LOSS THRESHOLD EXCEEDED: "
                f"{self._consecutive_losses} >= {self.config.consecutive_losses}"
            )
            return True

        return False

    async def record_request(self, is_error: bool = False) -> None:
        """Record API request for error rate tracking

        Args:
            is_error: Whether the request resulted in an error
        """
        async with self._lock:
            self._total_requests += 1
            if is_error:
                self._error_count += 1

    async def record_trade(self, pnl: float) -> None:
        """Record trade P&L for consecutive loss tracking

        Args:
            pnl: Trade P&L
        """
        async with self._lock:
            if pnl < 0:
                self._consecutive_losses += 1
            else:
                self._consecutive_losses = 0

            self._last_trade_pnl = pnl

    async def check_kill_switch_conditions(self) -> bool:
        """Check all kill switch conditions

        Returns:
            True if kill switch should activate
        """
        async with self._lock:
            if self.kill_switch_active:
                return True

            # Check all conditions
            checks = [
                await self.check_daily_loss(),
                await self.check_error_rate(),
                await self.check_consecutive_losses()
            ]

            return any(checks)

    async def activate_kill_switch(self, reason: str) -> None:
        """Activate kill switch and trigger callback

        Args:
            reason: Reason for activation
        """
        async with self._lock:
            if self.kill_switch_active:
                return  # Already active

            logger.critical(f"🚨 KILL SWITCH ACTIVATED: {reason}")
            self.kill_switch_active = True

            # Trigger callback
            if self.kill_switch_callback:
                try:
                    await self.kill_switch_callback(reason)
                except Exception as e:
                    logger.error(f"Kill switch callback failed: {e}")

    async def get_metrics(self) -> RiskMetrics:
        """Get current risk metrics snapshot

        Returns:
            Risk metrics
        """
        async with self._lock:
            current_pnl = self.position_tracker.get_total_pnl()
            daily_pnl = current_pnl - self._daily_start_pnl

            return RiskMetrics(
                timestamp=datetime.utcnow(),
                total_exposure=self.position_tracker.get_total_exposure(),
                total_pnl=current_pnl,
                daily_pnl=daily_pnl,
                error_count=self._error_count,
                total_requests=self._total_requests,
                consecutive_losses=self._consecutive_losses,
                kill_switch_active=self.kill_switch_active
            )

    async def periodic_check(self) -> None:
        """Periodic risk check (call from main loop)"""
        should_kill = await self.check_kill_switch_conditions()

        if should_kill and not self.kill_switch_active:
            metrics = await self.get_metrics()
            reason = (
                f"daily_pnl={metrics.daily_pnl:.2f}, "
                f"error_rate={metrics.error_count}/{metrics.total_requests}, "
                f"consecutive_losses={metrics.consecutive_losses}"
            )
            await self.activate_kill_switch(reason)
