"""WebSocket manager for real-time Kalshi data streams"""

import asyncio
import websockets
from typing import Optional, Dict, Callable, Any, Set
from datetime import datetime
from loguru import logger
import json

from src.api.auth import KalshiAuth
from src.models.config import WebSocketConfig


class WebSocketManager:
    """Manages WebSocket connection to Kalshi for real-time data

    Features:
    - Authentication with RSA-PSS signatures
    - Auto-reconnect with exponential backoff
    - Heartbeat monitoring
    - Channel subscription management
    - Message routing to callbacks
    """

    def __init__(
        self,
        ws_url: str,
        auth: KalshiAuth,
        config: WebSocketConfig
    ):
        """Initialize WebSocket manager

        Args:
            ws_url: WebSocket URL (wss://...)
            auth: Authentication instance
            config: WebSocket configuration
        """
        self.ws_url = ws_url
        self.auth = auth
        self.config = config

        # Connection state
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.connected = False
        self._reconnect_count = 0

        # Subscriptions
        self._subscriptions: Set[str] = set()
        self._message_handlers: Dict[str, Callable] = {}

        # Background tasks
        self._receive_task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._should_stop = False

        # Message sequencing
        self._last_heartbeat = datetime.utcnow()
        self._message_id = 0

        logger.info(f"WebSocket manager initialized: {ws_url}")

    async def connect(self) -> bool:
        """Establish WebSocket connection with authentication

        Returns:
            True if connection successful
        """
        try:
            # Get authentication headers
            # For WebSocket, we need to include auth in connection headers
            headers = self.auth.sign_request('GET', '/trade-api/ws/v2')

            # Connect
            logger.info(f"Connecting to WebSocket: {self.ws_url}")
            self.websocket = await websockets.connect(
                self.ws_url,
                additional_headers=headers,  # Changed from extra_headers for websockets 12+
                ping_interval=30,
                ping_timeout=10,
                close_timeout=10
            )

            self.connected = True
            self._reconnect_count = 0
            logger.info("WebSocket connected successfully")

            # Start background tasks
            self._receive_task = asyncio.create_task(self._receive_loop())
            # Heartbeat handled by websockets library
            
            return True

        except Exception as e:
            logger.error(f"WebSocket connection failed: {e}")
            self.connected = False
            return False

    async def disconnect(self) -> None:
        """Close WebSocket connection"""
        logger.info("Disconnecting WebSocket")
        self._should_stop = True

        # Cancel background tasks
        if self._receive_task:
            self._receive_task.cancel()

        # Close connection
        if self.websocket:
            await self.websocket.close()
            self.websocket = None

        self.connected = False
        logger.info("WebSocket disconnected")

    async def subscribe(self, channel: str, handler: Optional[Callable] = None, market_tickers: Optional[list[str]] = None) -> bool:
        """Subscribe to WebSocket channel

        Args:
            channel: Channel name (e.g., "orderbook_delta")
            handler: Optional message handler callback
            market_tickers: Optional list of market tickers to filter by

        Returns:
            True if subscription successful
        """
        if not self.connected:
            logger.error("Cannot subscribe: WebSocket not connected")
            return False

        try:
            # Send subscription message
            self._message_id += 1
            params = {"channels": [channel]}
            if market_tickers:
                params["market_tickers"] = market_tickers

            subscribe_msg = {
                "id": self._message_id,
                "cmd": "subscribe",
                "params": params
            }

            await self.websocket.send(json.dumps(subscribe_msg))

            # Store subscription key
            # For single-ticker subscriptions, we key by channel:ticker to route messages correctly
            if market_tickers and len(market_tickers) == 1:
                sub_key = f"{channel}:{market_tickers[0]}"
                self._subscriptions.add(sub_key)
                if handler:
                    self._message_handlers[sub_key] = handler
            else:
                self._subscriptions.add(channel)
                if handler:
                    self._message_handlers[channel] = handler

            logger.info(f"Subscribed to channel: {channel} (tickers={market_tickers})")
            return True

        except Exception as e:
            logger.error(f"Subscription failed for {channel}: {e}")
            return False

    async def unsubscribe(self, channel: str) -> bool:
        """Unsubscribe from channel

        Args:
            channel: Channel name

        Returns:
            True if unsubscription successful
        """
        if not self.connected:
            return False

        try:
            self._message_id += 1
            unsubscribe_msg = {
                "id": self._message_id,
                "cmd": "unsubscribe",
                "params": {
                    "channels": [channel]
                }
            }

            await self.websocket.send(json.dumps(unsubscribe_msg))
            self._subscriptions.discard(channel)
            self._message_handlers.pop(channel, None)

            logger.info(f"Unsubscribed from channel: {channel}")
            return True

        except Exception as e:
            logger.error(f"Unsubscription failed for {channel}: {e}")
            return False

    async def _receive_loop(self) -> None:
        """Background task: receive and process messages"""
        logger.info("WebSocket receive loop started")

        try:
            while not self._should_stop and self.connected:
                try:
                    # Receive message
                    # We rely on websockets library ping_timeout to detect dead connections
                    message = await self.websocket.recv()

                    # Parse JSON
                    data = json.loads(message)

                    # Handle message
                    await self._handle_message(data)

                except websockets.exceptions.ConnectionClosed:
                    logger.warning("WebSocket connection closed")
                    await self._reconnect()
                    break
        
        except asyncio.CancelledError:
            logger.info("WebSocket receive loop cancelled")
        except Exception as e:
            logger.error(f"WebSocket receive loop error: {e}")
            await self._reconnect()

    async def _handle_message(self, data: Dict[str, Any]) -> None:
        """Handle incoming WebSocket message

        Args:
            data: Parsed message data
        """
        msg_type = data.get('type')

        if msg_type == 'pong':
            # Heartbeat response
            self._last_heartbeat = datetime.utcnow()
            logger.debug("Received pong")

        elif msg_type == 'orderbook_delta':
            # Order book delta update
            await self._handle_orderbook_delta(data)

        elif msg_type == 'subscribed':
            # Subscription confirmation
            logger.info(f"Subscription confirmed: {data.get('sid')}")

        elif msg_type == 'error':
            # Error message
            logger.error(f"WebSocket error: {data.get('msg')}")

        else:
            logger.debug(f"Unknown message type: {msg_type}")

    async def _handle_orderbook_delta(self, data: Dict[str, Any]) -> None:
        """Handle orderbook_delta message

        Args:
            data: Delta message data
        """
        msg = data.get('msg', {})
        market_ticker = msg.get('market_ticker')

        if not market_ticker:
            logger.warning("orderbook_delta missing market_ticker")
            return

        # Route to handler
        channel = f"orderbook_delta:{market_ticker}"
        handler = self._message_handlers.get(channel)

        if handler:
            try:
                await handler(data)
            except Exception as e:
                logger.error(f"Handler error for {channel}: {e}")
        else:
            logger.debug(f"No handler registered for {channel}")

    async def _reconnect(self) -> None:
        """Attempt to reconnect with exponential backoff"""
        if not self.config.auto_reconnect:
            logger.info("Auto-reconnect disabled")
            return

        if self._reconnect_count >= self.config.max_reconnect_attempts:
            logger.error(f"Max reconnect attempts ({self.config.max_reconnect_attempts}) exceeded")
            return

        self._reconnect_count += 1

        # Calculate backoff delay
        delay = self.config.reconnect_delay * (2 ** (self._reconnect_count - 1))
        delay = min(delay, 60)  # Cap at 60 seconds

        logger.info(f"Reconnecting in {delay}s (attempt {self._reconnect_count}/{self.config.max_reconnect_attempts})")
        await asyncio.sleep(delay)

        # Disconnect cleanly
        if self.websocket:
            try:
                await self.websocket.close()
            except:
                pass
            self.websocket = None
            self.connected = False

        # Reconnect
        success = await self.connect()

        if success:
            # Re-subscribe to channels
            logger.info(f"Resubscribing to {len(self._subscriptions)} channel(s)")
            subscriptions_copy = list(self._subscriptions)
            self._subscriptions.clear()

            for channel in subscriptions_copy:
                handler = self._message_handlers.get(channel)
                await self.subscribe(channel, handler)

        else:
            # Retry
            await self._reconnect()

    def is_connected(self) -> bool:
        """Check if WebSocket is connected"""
        return self.connected and self.websocket is not None

    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.disconnect()
