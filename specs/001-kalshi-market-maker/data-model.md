# Data Model: FiftyFive Entities

**Feature**: Kalshi Market Maker Bot  
**Date**: 2026-01-08

This document defines all core entities, their schemas, relationships, and state transitions.

---

## Entity Overview

- Market: Prediction market metadata and status
- OrderBook: Real-time bid/ask levels
- Order: Limit order on exchange
- Fill: Executed trade
- Position: Holdings and P&L for a market
- Config: System configuration with risk limits, strategy params

---

## 1. Market Entity

Represents a Kalshi prediction market.

**Fields:**
- ticker: str (unique ID)
- title: str
- category: str (sports, economics, politics)
- status: OPEN | CLOSED | SETTLED
- close_time: datetime
- volume_24h: float (USD)
- last_price: float [0.01-0.99]

**Validation:**
- status transitions: OPEN -> CLOSED -> SETTLED (irreversible)
- last_price must be [0.01, 0.99]

---

## 2. OrderBook Entity

Real-time order book state.

**Fields:**
- market_ticker: str
- yes_bids: List[PriceLevel] (sorted desc)
- yes_asks: List[PriceLevel] (sorted asc)
- no_bids: List[PriceLevel]
- no_asks: List[PriceLevel]
- sequence_number: int
- timestamp: datetime

**PriceLevel:**
- price: float [0.01-0.99]
- quantity: int

**Invariants:**
- sequence_number must increment by 1 (gaps trigger resync)
- staleness < 60 seconds (force resync if exceeded)

---

## 3. Order Entity

Limit order placed on exchange.

**Fields:**
- order_id: str (exchange ID)
- client_order_id: str (UUID)
- market_ticker: str
- side: YES | NO
- action: BUY | SELL  
- price: float [0.01-0.99]
- quantity: int
- status: PENDING | OPEN | FILLED | PARTIALLY_FILLED | CANCELLED | REJECTED

**State Transitions:**
PENDING -> OPEN -> PARTIALLY_FILLED -> FILLED
  |        |            |
  v        v            v
REJECTED CANCELLED CANCELLED

---

## 4. Fill Entity

Executed trade.

**Fields:**
- fill_id: str
- order_id: str
- market_ticker: str
- side: YES | NO
- price: float
- quantity: int
- is_maker: bool (true = provided liquidity)
- fee_rate: float (-0.005 maker, +0.007 taker)
- gross_value: float (price * quantity)
- net_value: float (gross_value + fee_amount)

**Calculations:**
fee_amount = gross_value * fee_rate
net_value = gross_value + fee_amount

---

## 5. Position Entity

Holdings in a market with P&L tracking.

**Fields:**
- market_ticker: str
- contracts_long: int (positive = long, negative = short)
- average_entry_price: float
- cost_basis: float
- market_value: float  
- unrealized_pnl: float (market_value - cost_basis)
- realized_pnl: float (locked-in P&L)
- fees_paid: float

**Validation:**
- contracts_long within risk limits (default ±20)
- position value <= max_exposure_per_market

---

## 6. Config Entity

System configuration from YAML.

**Top-level sections:**
- environment: production | demo | staging
- exchange: API URLs, rate limits
- risk: RiskConfig (limits, kill switch thresholds)
- strategy: StrategyConfig (pricing, spreads)
- execution: order refresh interval, STP settings
- data: WebSocket config, order book settings
- logging: log levels, rotation
- monitoring: alerts config

---

## 7. RiskConfig

**Fields:**
- max_exposure_per_market: float (default: 500 USD)
- max_total_exposure: float (default: 2000 USD)
- max_contracts_per_side: int (default: 20)
- daily_loss_limit: float (default: 100 USD)
- error_rate_threshold: float (default: 0.10)
- consecutive_losses: int (default: 5)
- inventory_target: int (default: 0)
- max_inventory_skew: int (default: 10)

---

## 8. StrategyConfig

**Fields:**
- name: pure_market_making | informed_market_making | volatility_harvesting
- market_filters: min_daily_volume, categories, max_spread
- pricing: base_spread, min_spread, max_spread, inventory_adjustment
- order_sizing: base_size, max_size
- rebalancing: enabled, interval

---

## 9. RateLimit (Runtime State)

**Fields:**
- rate: float (tokens per second)
- capacity: int (max burst)
- tokens: float (current available)
- last_update: float (monotonic time)

**Behavior:**
- Tokens replenish at `rate` per second
- Capped at `capacity`
- Each API call consumes 1 token
- Blocks if tokens < 1

---

## Key Relationships

- Market 1--1 OrderBook (each market has one current orderbook)
- Market 1--0..1 Position (only if we hold contracts)
- Market 1--* Order (multiple open orders per market)
- Order 1--* Fill (partial fills)
- Position aggregates all Fills for that market
- Config 1--1 all components (single source of truth)

---

## Summary

This data model provides type safety, clear state transitions, P&L accuracy, compliance validation, and full auditability. Ready for Phase 1 implementation.
