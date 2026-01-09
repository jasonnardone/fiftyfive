"""Token bucket rate limiter for API calls"""

import asyncio
import time
from typing import Optional


class TokenBucket:
    """Async token bucket rate limiter

    Implements token bucket algorithm with:
    - Configurable rate (tokens per second)
    - Maximum burst capacity
    - Async acquire() for rate-limited operations
    """

    def __init__(self, rate: float, capacity: int):
        """Initialize token bucket

        Args:
            rate: Tokens per second (e.g., 10.0 for 10 req/sec)
            capacity: Maximum burst capacity
        """
        if rate <= 0:
            raise ValueError(f"Rate must be > 0, got {rate}")
        if capacity < 1:
            raise ValueError(f"Capacity must be >= 1, got {capacity}")

        self.rate = rate
        self.capacity = capacity
        self._tokens = float(capacity)
        self._last_update = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self, tokens: int = 1, timeout: Optional[float] = None) -> bool:
        """Acquire tokens (blocks until available or timeout)

        Args:
            tokens: Number of tokens to acquire
            timeout: Maximum wait time in seconds (None = infinite)

        Returns:
            True if tokens acquired, False if timeout

        Raises:
            ValueError: If tokens > capacity
        """
        if tokens > self.capacity:
            raise ValueError(f"Requested {tokens} tokens exceeds capacity {self.capacity}")

        start_time = time.monotonic()

        while True:
            async with self._lock:
                # Refill tokens based on elapsed time
                now = time.monotonic()
                elapsed = now - self._last_update
                self._tokens = min(self.capacity, self._tokens + elapsed * self.rate)
                self._last_update = now

                # Check if enough tokens available
                if self._tokens >= tokens:
                    self._tokens -= tokens
                    return True

            # Check timeout
            if timeout is not None:
                elapsed_total = time.monotonic() - start_time
                if elapsed_total >= timeout:
                    return False

            # Wait before retry (use small interval to avoid busy-wait)
            await asyncio.sleep(0.01)

    def try_acquire(self, tokens: int = 1) -> bool:
        """Try to acquire tokens without blocking (NOT async-safe)

        WARNING: Only use from async context with proper locking

        Args:
            tokens: Number of tokens to acquire

        Returns:
            True if tokens acquired, False otherwise
        """
        # Refill tokens
        now = time.monotonic()
        elapsed = now - self._last_update
        self._tokens = min(self.capacity, self._tokens + elapsed * self.rate)
        self._last_update = now

        # Check and consume
        if self._tokens >= tokens:
            self._tokens -= tokens
            return True
        return False

    @property
    def available_tokens(self) -> float:
        """Get current available tokens (approximate)"""
        now = time.monotonic()
        elapsed = now - self._last_update
        return min(self.capacity, self._tokens + elapsed * self.rate)


class RateLimiter:
    """Rate limiter with separate read/write buckets"""

    def __init__(self, write_rps: int, read_rps: int, burst_size: int = 5):
        """Initialize rate limiter

        Args:
            write_rps: Write requests per second
            read_rps: Read requests per second
            burst_size: Burst capacity multiplier
        """
        self.write_bucket = TokenBucket(
            rate=float(write_rps),
            capacity=write_rps + burst_size
        )
        self.read_bucket = TokenBucket(
            rate=float(read_rps),
            capacity=read_rps + burst_size
        )

    async def acquire_write(self, timeout: Optional[float] = None) -> bool:
        """Acquire write token"""
        return await self.write_bucket.acquire(tokens=1, timeout=timeout)

    async def acquire_read(self, timeout: Optional[float] = None) -> bool:
        """Acquire read token"""
        return await self.read_bucket.acquire(tokens=1, timeout=timeout)
