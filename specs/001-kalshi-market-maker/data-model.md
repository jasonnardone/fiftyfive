# Data Model: FiftyFive Entities

**Feature**: Kalshi Market Maker Bot  
**Date**: 2026-01-11
**Status**: Updated to match implementation

This document defines all core entities, their schemas, relationships, and state transitions based on the current implementation in `src/models/`.

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

Represents a Kalshi prediction market. Defined in `src/models/market.py`.

**Fields:**
- ticker: str (unique ID)
- title: str
- category: str
- status: MarketStatus (OPEN | CLOSED | SETTLED)

**Contract Details:**
- yes_sub_title: Optional[str]
- no_sub_title: Optional[str]

**Market Data:**
- volume: int (24h volume)
- open_interest: int
- liquidity: int

**Price Data:**
- yes_bid: Optional[float]
- yes_ask: Optional[float]
- no_bid: Optional[float]
- no_ask: Optional[float]
- last_price: Optional[float]

**Timing & Settlement:**
- close_time: Optional[datetime]
- expiration_time: Optional[datetime]
- created_at: Optional[datetime]
- result: Optional[str] ('yes' or 'no')
- settled_at: Optional[datetime]

---

## 2. OrderBook Entity

Real-time order book state. Defined in `src/models/order.py`.

**Fields:**
- market_ticker: str
- yes_bids: List[PriceLevel] (descending)
- yes_asks: List[PriceLevel] (ascending)
- no_bids: List[PriceLevel] (descending)
- no_asks: List[PriceLevel] (ascending)
- sequence: int (Sequence number for delta validation)
- last_updated: Optional[datetime]

**PriceLevel:**
- price: int (Price in cents 1-99)
- quantity: int (Number of contracts)

---

## 3. Order Entity

Limit order placed on exchange. Defined in `src/models/order.py`.

**Fields:**
- order_id: Optional[str] (Exchange ID)
- client_order_id: str (UUID)
- market_ticker: str
- side: OrderSide (YES | NO)
- action: OrderAction (BUY | SELL)
- price: float [0.01-0.99]
- quantity: int
- filled_quantity: int
- remaining_quantity: int
- status: OrderStatus
- created_at: Optional[datetime]
- updated_at: Optional[datetime]
- error_message: Optional[str]

**OrderStatus Enum:**
- PENDING
- OPEN ("resting")
- PARTIALLY_FILLED
- FILLED
- CANCELLED
- REJECTED

---

## 4. Fill Entity

Executed trade. Defined in `src/models/order.py`.

**Fields:**
- fill_id: str
- order_id: str
- market_ticker: str
- side: OrderSide
- action: OrderAction
- price: float (Execution price)
- quantity: int
- maker_fee: float (Negative = rebate)
- taker_fee: float (Positive = cost)
- filled_at: Optional[datetime]

**Calculated Properties:**
- net_proceeds: float (gross_value - fees)
- is_maker: bool (maker_fee < 0)

---

## 5. Position Entity

Holdings in a market with P&L tracking. Defined in `src/models/position.py`.

**Fields:**
- market_ticker: str
- side: OrderSide
- quantity: int (Net position: positive=long, negative=short)
- total_cost: float (Total cost basis)
- realized_pnl: float
- unrealized_pnl: float
- total_fees: float
- opened_at: Optional[datetime]
- updated_at: Optional[datetime]

**Calculated Properties:**
- average_price: float
- market_value: float
- is_flat: bool
- total_pnl: float (realized + unrealized)
- net_pnl: float (total_pnl - total_fees)

---

## 6. Config Entity

System configuration from YAML. Defined in `src/models/config.py`.

**Top-level sections:**
- environment: str
- exchange: ExchangeConfig
- risk: RiskConfig
- strategy: StrategyConfig
- execution: ExecutionConfig
- data: DataConfig
- logging: LoggingConfig
- monitoring: MonitoringConfig

---

## 7. RiskConfig

**Fields:**
- max_exposure_per_market: float
- max_total_exposure: float
- max_contracts_per_side: int
- daily_loss_limit: float
- error_rate_threshold: float
- consecutive_losses: int
- inventory_target: int
- max_inventory_skew: int

---

## 8. StrategyConfig

**Fields:**
- name: str
- market_filters: dict
- pricing: dict
- order_sizing: dict
- rebalancing: dict

---

## Key Relationships

- Market 1--1 OrderBook
- Market 1--0..1 Position
- Market 1--* Order
- Order 1--* Fill
- Position aggregates Fills
- Config defines system behavior

---

## Summary

This data model reflects the Python dataclasses implemented in the `src/models` package. It serves as the authoritative reference for the application's state.
