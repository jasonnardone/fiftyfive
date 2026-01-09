"""FiftyFive - Kalshi Market Maker Bot

Main entry point for the automated market-making bot.
"""

import asyncio
import argparse
import signal
import sys
from typing import Optional, List
from datetime import datetime
from loguru import logger
import aiohttp

from src.config.loader import load_config
from src.models.config import Config
from src.models.order import OrderSide
from src.utils.logger import setup_logger
from src.utils.rate_limiter import RateLimiter
from src.utils.alerts import AlertDispatcher
from src.api.auth import KalshiAuth
from src.api.client import KalshiClient
from src.api.websocket import WebSocketManager
from src.data.orderbook_manager import OrderBookManager
from src.data.market_discovery import MarketDiscovery
from src.execution.stp_engine import STPEngine
from src.execution.order_manager import OrderManager
from src.risk.position_tracker import PositionTracker
from src.risk.monitor import RiskMonitor
from src.strategies.pure_mm import PureMarketMakingStrategy


class FiftyFiveBot:
    """Main bot orchestrator"""

    def __init__(self, config: Config, dry_run: bool = False):
        """Initialize bot

        Args:
            config: Configuration
            dry_run: If True, simulate orders without actual submission
        """
        self.config = config
        self.dry_run = dry_run
        self._running = False
        self._shutdown_event = asyncio.Event()

        # Components (initialized in setup())
        self.session: Optional[aiohttp.ClientSession] = None
        self.api_client: Optional[KalshiClient] = None
        self.ws_manager: Optional[WebSocketManager] = None
        self.orderbook_manager: Optional[OrderBookManager] = None
        self.market_discovery: Optional[MarketDiscovery] = None
        self.alert_dispatcher: Optional[AlertDispatcher] = None
        self.stp_engine: Optional[STPEngine] = None
        self.position_tracker: Optional[PositionTracker] = None
        self.risk_monitor: Optional[RiskMonitor] = None
        self.order_manager: Optional[OrderManager] = None
        self.strategy: Optional[PureMarketMakingStrategy] = None

        # Markets we're quoting
        self._active_markets: List[str] = []

        logger.info(
            f"FiftyFive initialized: environment={config.environment}, "
            f"dry_run={dry_run}"
        )

    async def setup(self) -> None:
        """Initialize all components"""
        logger.info("Setting up components...")

        # Create HTTP session with connection pooling
        connector = aiohttp.TCPConnector(
            limit=self.config.advanced.max_concurrent_requests
        )
        timeout = aiohttp.ClientTimeout(total=self.config.advanced.request_timeout)
        self.session = aiohttp.ClientSession(connector=connector, timeout=timeout)

        # Initialize rate limiter
        rate_limiter = RateLimiter(
            write_rps=self.config.exchange.rate_limits.write_rps,
            read_rps=self.config.exchange.rate_limits.read_rps,
            burst_size=self.config.exchange.rate_limits.burst_size
        )

        # Initialize API client
        self.api_client = KalshiClient(
            config=self.config.exchange,
            rate_limiter=rate_limiter,
            session=self.session
        )

        # Test authentication
        try:
            balance = await self.api_client.get_balance()
            logger.info(f"✓ Authentication successful - Balance: ${balance.get('balance', 0):.2f}")
        except Exception as e:
            logger.error(f"✗ Authentication failed: {e}")
            raise

        # Initialize WebSocket manager
        auth = KalshiAuth(
            api_key_id=self.config.exchange.api_key_id,
            private_key_path=self.config.exchange.private_key_path
        )
        self.ws_manager = WebSocketManager(
            ws_url=self.config.exchange.ws_url,
            auth=auth,
            config=self.config.data.websocket
        )

        # Connect WebSocket
        connected = await self.ws_manager.connect()
        if connected:
            logger.info("✓ WebSocket connected")
        else:
            logger.error("✗ WebSocket connection failed")
            raise RuntimeError("WebSocket connection failed")

        # Initialize OrderBook manager
        self.orderbook_manager = OrderBookManager(
            api_client=self.api_client,
            ws_manager=self.ws_manager,
            snapshot_interval=self.config.data.websocket.snapshot_refresh_interval,
            staleness_threshold=self.config.data.orderbook.staleness_threshold
        )

        # Initialize Market Discovery
        self.market_discovery = MarketDiscovery(
            api_client=self.api_client,
            config=self.config.strategy.market_filters
        )

        # Initialize Alert Dispatcher
        self.alert_dispatcher = AlertDispatcher(config=self.config.monitoring.alerts)
        await self.alert_dispatcher.start()

        # Initialize STP engine
        self.stp_engine = STPEngine(
            cancel_delay=self.config.execution.stp_cancel_delay
        )

        # Initialize position tracker
        self.position_tracker = PositionTracker()

        # Initialize risk monitor
        self.risk_monitor = RiskMonitor(
            config=self.config.risk,
            position_tracker=self.position_tracker,
            kill_switch_callback=self._kill_switch_triggered,
            alert_dispatcher=self.alert_dispatcher
        )

        # Initialize order manager
        self.order_manager = OrderManager(
            api_client=self.api_client,
            stp_engine=self.stp_engine,
            risk_monitor=self.risk_monitor,
            position_tracker=self.position_tracker
        )

        # Sync existing orders (populate STP cache)
        await self.order_manager.sync_orders()

        # Initialize strategy
        self.strategy = PureMarketMakingStrategy(
            config=self.config.strategy,
            orderbook_manager=self.orderbook_manager,
            position_tracker=self.position_tracker
        )

        logger.info("✓ All components initialized")

    async def discover_markets(self) -> List[str]:
        """Discover markets matching strategy filters

        Returns:
            List of market tickers
        """
        if not self.market_discovery:
            logger.error("Market discovery not initialized")
            return []

        return await self.market_discovery.get_target_markets(limit=10)

    async def subscribe_markets(self, tickers: List[str]) -> None:
        """Subscribe to market order books

        Args:
            tickers: List of market tickers
        """
        logger.info(f"Subscribing to {len(tickers)} market(s)...")

        for ticker in tickers:
            success = await self.orderbook_manager.subscribe_market(ticker)
            if success:
                self._active_markets.append(ticker)
                logger.info(f"✓ Subscribed: {ticker}")
            else:
                logger.error(f"✗ Failed to subscribe: {ticker}")

        # Start snapshot sync
        await self.orderbook_manager.start_snapshot_sync()

    async def refresh_quotes(self) -> None:
        """Refresh quotes for all active markets"""
        if self.dry_run:
            logger.info("[DRY-RUN] Would refresh quotes")

        for ticker in self._active_markets:
            try:
                # Check if should quote
                should_quote = await self.strategy.should_quote(ticker)
                if not should_quote:
                    continue

                # Calculate quotes
                quotes = await self.strategy.calculate_quotes(ticker)

                for quote in quotes:
                    if self.dry_run:
                        # Dry-run mode: log only
                        logger.info(
                            f"[DRY-RUN] Would place: {quote.market_ticker} {quote.side.value} "
                            f"bid {quote.bid_size}@{quote.bid_price:.2f} "
                            f"ask {quote.ask_size}@{quote.ask_price:.2f}"
                        )
                    else:
                        # Place bid
                        if quote.bid_price and quote.bid_size > 0:
                            await self.order_manager.place_order(
                                market_ticker=quote.market_ticker,
                                side=quote.side,
                                action="buy",
                                price=quote.bid_price,
                                quantity=quote.bid_size
                            )

                        # Place ask
                        if quote.ask_price and quote.ask_size > 0:
                            await self.order_manager.place_order(
                                market_ticker=quote.market_ticker,
                                side=quote.side,
                                action="sell",
                                price=quote.ask_price,
                                quantity=quote.ask_size
                            )

            except Exception as e:
                logger.error(f"Quote refresh error for {ticker}: {e}")

    async def process_fills_loop(self) -> None:
        """Background task: process fills"""
        logger.info("Fill processing loop started")

        while self._running:
            try:
                fills = await self.order_manager.process_fills()

                for fill in fills:
                    # Notify strategy
                    await self.strategy.on_fill(
                        market_ticker=fill.market_ticker,
                        side=fill.side,
                        pnl=fill.net_proceeds
                    )

                    # Record trade for risk monitor
                    await self.risk_monitor.record_trade(pnl=fill.net_proceeds)

                await asyncio.sleep(5)  # Check fills every 5 seconds

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Fill processing error: {e}")
                await asyncio.sleep(5)

    async def risk_monitoring_loop(self) -> None:
        """Background task: monitor risk"""
        logger.info("Risk monitoring loop started")

        while self._running:
            try:
                await self.risk_monitor.periodic_check()

                # Log metrics every minute
                metrics = await self.risk_monitor.get_metrics()
                logger.info(
                    f"Risk metrics: "
                    f"exposure=${metrics.total_exposure:.2f}, "
                    f"daily_pnl=${metrics.daily_pnl:.2f}, "
                    f"total_pnl=${metrics.total_pnl:.2f}"
                )

                await asyncio.sleep(60)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Risk monitoring error: {e}")
                await asyncio.sleep(60)

    async def quote_refresh_loop(self) -> None:
        """Background task: refresh quotes"""
        interval = self.config.execution.order_refresh_interval
        logger.info(f"Quote refresh loop started (interval={interval}s)")

        while self._running:
            try:
                await self.refresh_quotes()
                await asyncio.sleep(interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Quote refresh error: {e}")
                await asyncio.sleep(interval)

    async def run(self) -> None:
        """Main trading loop"""
        self._running = True

        try:
            # Setup
            await self.setup()

            # Discover and subscribe to markets
            markets = await self.discover_markets()
            if not markets:
                logger.error("No markets found")
                return

            await self.subscribe_markets(markets)

            logger.info("🚀 FiftyFive is running...")
            logger.info(f"Strategy: {self.strategy.name}")
            logger.info(f"Markets: {len(self._active_markets)}")
            logger.info(f"Dry-run: {self.dry_run}")

            # Start background tasks
            tasks = [
                asyncio.create_task(self.quote_refresh_loop()),
                asyncio.create_task(self.process_fills_loop()),
                asyncio.create_task(self.risk_monitoring_loop())
            ]

            # Wait for shutdown signal
            await self._shutdown_event.wait()

            # Cancel tasks
            logger.info("Cancelling background tasks...")
            for task in tasks:
                task.cancel()

            await asyncio.gather(*tasks, return_exceptions=True)

        except Exception as e:
            logger.error(f"Fatal error: {e}")
            raise

        finally:
            await self.shutdown()

    async def shutdown(self) -> None:
        """Graceful shutdown"""
        logger.info("Shutting down...")
        self._running = False

        # Cancel all orders
        if self.order_manager:
            await self.order_manager.cancel_all_orders()

        # Stop snapshot sync
        if self.orderbook_manager:
            await self.orderbook_manager.stop_snapshot_sync()

        # Disconnect WebSocket
        if self.ws_manager:
            await self.ws_manager.disconnect()

        # Close HTTP session
        if self.session:
            await self.session.close()

        # Stop alert dispatcher
        if self.alert_dispatcher:
            await self.alert_dispatcher.stop()

        logger.info("Shutdown complete")

    async def _kill_switch_triggered(self, reason: str) -> None:
        """Callback when kill switch activates

        Args:
            reason: Reason for kill switch
        """
        logger.critical(f"🚨 KILL SWITCH: {reason}")
        logger.critical("Initiating emergency shutdown...")

        # Cancel all orders immediately
        if self.order_manager:
            await self.order_manager.cancel_all_orders()

        # Trigger shutdown
        self._shutdown_event.set()

    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down...")
        self._shutdown_event.set()


async def main():
    """Main entry point"""
    # Parse arguments
    parser = argparse.ArgumentParser(description="FiftyFive - Kalshi Market Maker Bot")
    parser.add_argument(
        '--config',
        type=str,
        required=True,
        help='Path to configuration file'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Simulate orders without actual submission'
    )

    args = parser.parse_args()

    # Load configuration
    try:
        config = load_config(args.config)
    except Exception as e:
        print(f"Failed to load configuration: {e}")
        sys.exit(1)

    # Setup logger
    setup_logger(
        log_dir=config.logging.log_dir,
        level=config.logging.level,
        rotation=config.logging.log_rotation,
        retention_days=config.logging.retention_days
    )

    # Print banner
    logger.info("=" * 60)
    logger.info("FiftyFive v1.0.0 - Kalshi Market Maker Bot")
    logger.info("=" * 60)
    logger.info(f"Environment: {config.environment}")
    logger.info(f"Dry-run: {args.dry_run}")
    logger.info(f"Config: {args.config}")
    logger.info("=" * 60)

    # Create and run bot
    bot = FiftyFiveBot(config, dry_run=args.dry_run)

    # Setup signal handlers
    signal.signal(signal.SIGINT, bot.signal_handler)
    signal.signal(signal.SIGTERM, bot.signal_handler)

    # Run
    try:
        await bot.run()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
