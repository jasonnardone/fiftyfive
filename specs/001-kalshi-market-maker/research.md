# Research: Technology Decisions for FiftyFive

**Feature**: Kalshi Market Maker Bot  
**Date**: 2026-01-08  
**Status**: Complete

This document consolidates research findings for critical technology decisions required to implement the FiftyFive market-making bot.

---

## 1. RSA-PSS Authentication for Kalshi API

### Decision
Use Python's `cryptography` library with RSA-PSS signature scheme for Kalshi API v2 authentication.

### Rationale
- **Security**: RSA-PSS provides resistance to cryptographic attacks vs deterministic PKCS#1 v1.5
- **API Requirement**: Kalshi API v2 explicitly requires RSA-PSS with MGF1(SHA256), salt_length=DIGEST_LENGTH
- **Library Maturity**: `cryptography` is standard Python library for cryptographic operations

### Alternatives Considered
- PyJWT: Rejected - designed for JWT tokens, not raw RSA-PSS signatures
- PyCryptodome: Rejected - less standardized, lacks asyncio support
- Manual OpenSSL: Rejected - error-prone, platform-dependent

---

## 2. Async WebSocket Patterns

### Decision
Use `websockets` library with asyncio for persistent connections. Implement auto-reconnect with exponential backoff, delta updates with sequence validation, periodic REST snapshots.

### Rationale
- **Library**: `websockets` is de facto standard for async WebSocket in Python
- **Resilience**: 24/7 operation requires robust reconnection (exponential backoff prevents exchange hammering)
- **Data Integrity**: Sequence numbers detect gaps, periodic snapshots prevent drift

### Alternatives Considered
- Socket.IO: Rejected - unnecessary complexity
- aiohttp WebSocket: Rejected - less mature than `websockets`
- Polling REST: Rejected - too slow (>500ms vs <100ms WebSocket)

---

## 3. Token Bucket Rate Limiting

### Decision
Implement token bucket algorithm with `asyncio.Lock` for thread-safe acquisition. Separate buckets for read (20/sec) and write (10/sec) with burst capacity.

### Rationale
- **Algorithm**: Token bucket allows controlled bursts while enforcing long-term limits
- **Precision**: `time.monotonic()` immune to clock skew
- **Async-Safe**: `asyncio.Lock` ensures atomic operations
- **Preemptive**: Rate limiting MUST happen before API calls

### Alternatives Considered
- Semaphore-based: Rejected - doesn't model replenishment accurately
- Lock-free: Rejected - race conditions in asyncio
- Redis: Rejected - unnecessary external dependency
- Leaky bucket: Rejected - doesn't allow burst behavior

---

## 4. Asyncio Performance Optimization

### Decision
Use `aiohttp.ClientSession` with connection pooling (50 max), TCP keep-alive, DNS caching. Optimistic state tracking and batch API calls.

### Rationale
- **Connection Pooling**: Reusing TCP connections saves ~50-100ms per request
- **Optimistic Updates**: <50ms latency requires immediate local state updates
- **Batch Operations**: Reduces network round-trips and rate limit consumption
- **DNS Caching**: Avoids repeated lookups (5min TTL)

### Alternatives Considered
- requests: Rejected - synchronous, blocks event loop
- httpx: Considered - less mature than aiohttp
- grpc: Rejected - Kalshi uses REST/WebSocket

---

## 5. Testing Strategies

### Decision
pytest with pytest-asyncio, pytest-mock for API mocking, hypothesis for property-based testing. Contract tests for schema validation, integration tests with demo API.

### Rationale
- **Async Testing**: pytest-asyncio natural for async test writing
- **Mocking**: Test edge cases without hitting production APIs
- **Property-Based**: Verify financial calculation invariants
- **Contract Tests**: Detect API schema drift
- **Demo Environment**: Test integration without real money

### Alternatives Considered
- unittest: Rejected - pytest has better async support
- responses: Rejected - pytest-mock more flexible for async
- QuickCheck: Rejected - hypothesis is Python-native

---

## 6. Kalshi API Specific Gotchas

### Price Normalization
API uses integer cents (1-99), internal uses floats (0.01-0.99). Use dedicated `PriceAdapter` class.

### Balance vs Balance_Total
Always use `balance` field (settled funds), NOT `balance_total` (includes unsettled).

### Cursor Pagination
`/markets` returns max 100 results. Loop until `cursor` field is null.

### Order Book Complementarity
Yes and No are complementary: `yes_price + no_price = $1.00`. Affects self-trade prevention logic.

### Fee Calculation
Maker rebate (-0.5%) vs taker fee (+0.7%). Track `is_taker` flag from fills.

---

## Summary

All technology decisions finalized with clear rationale:
1. RSA-PSS authentication with cryptography library
2. Robust WebSocket patterns with auto-reconnect  
3. Preemptive token bucket rate limiting
4. Connection pooling and optimistic updates for <50ms latency
5. Comprehensive testing with mocking and property-based tests
6. Deep understanding of Kalshi API quirks

Phase 1 design can now proceed confidently.
