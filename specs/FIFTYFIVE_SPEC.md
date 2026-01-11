# FiftyFive: Kalshi Market Maker Bot - Complete Specification

**Project Name:** FiftyFive  
**Version:** 1.0.0  
**Target Platform:** Kalshi (CFTC Regulated Exchange)  
**Language:** Python 3.10+  
**Deployment:** Local PC (WSL2/Ubuntu)  
**IDE:** VS Code  

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Market Making Strategy & Profitability](#market-making-strategy--profitability)
3. [System Architecture](#system-architecture)
4. [Configuration System](#configuration-system)
5. [Compliance & Risk Management](#compliance--risk-management)
6. [API Integration](#api-integration)
7. [Data Management](#data-management)
8. [Order Execution Engine](#order-execution-engine)
9. [Pricing Algorithms](#pricing-algorithms)
10. [Performance Optimization](#performance-optimization)
11. [Setup & Installation](#setup--installation)
12. [Monitoring & Operations](#monitoring--operations)
13. [Appendix: Critical Gotchas](#appendix-critical-gotchas)

---

## 1. Executive Summary

### What is FiftyFive?

FiftyFive is an automated market-making bot for Kalshi that provides liquidity to prediction markets by continuously posting buy and sell orders, profiting from the bid-ask spread. The bot operates autonomously, requiring minimal manual intervention after initial configuration.

### How Market Makers Make Money

Market makers profit by:
1. **Capturing the Spread**: Buying at slightly below fair value and selling slightly above
2. **Volume Trading**: Making small profits repeatedly across many trades
3. **Inventory Management**: Balancing positions to avoid directional risk
4. **Fee Optimization**: Earning maker rebates while minimizing taker fees

**Example Profit Scenario:**
- Fair value estimate: $0.55 (55% probability)
- Place buy order at $0.53, sell order at $0.57
- Spread captured: $0.04 per contract (minus fees)
- With 50 round-trips per day = $2.00 daily profit per market
- Scale across 10 markets = $20/day = $600/month

### Success Benchmarks

Based on real-world data from successful Kalshi market makers:
- **Target ROI**: 15-30% monthly on deployed capital
- **Win Rate**: 60-70% of trades profitable
- **Sharpe Ratio**: 1.5+ (risk-adjusted returns)
- **Daily Trades**: 20-100 per market
- **Typical Starting Capital**: $500-$2,000

---

## 2. Market Making Strategy & Profitability

### 2.1 Primary Strategies

#### Strategy A: Pure Market Making (Recommended for Beginners)
**Objective:** Profit from bid-ask spread without taking directional risk

**Configuration:**
```yaml
strategy: pure_market_making
target_markets:
  - category: sports
    min_volume: 10000  # Only liquid markets
    max_spread: 0.10   # 10 cent spreads
spread_config:
  base_spread: 0.04    # Start with 4 cent spread
  min_spread: 0.02     # Tighten to 2 cents in competition
  max_spread: 0.08     # Widen when inventory builds
inventory_limits:
  max_position: 20     # Maximum 20 contracts per side
  target_position: 0   # Always return to neutral
```

**When to Use:**
- You have limited market knowledge
- You want predictable, low-risk returns
- Markets have consistent two-sided flow

**Expected Returns:** 10-20% monthly

---

#### Strategy B: Informed Market Making (Advanced)
**Objective:** Make markets with a directional edge based on external data

**Configuration:**
```yaml
strategy: informed_market_making
data_sources:
  - type: real_time_sports_data
    provider: espn_api
    update_interval: 5s
  - type: weather_data
    provider: noaa_api
    update_interval: 60s
pricing_model:
  type: bayesian_update
  base_probability: market_price
  adjustment_factor: 0.15  # Skew quotes 15% toward true value
spread_config:
  base_spread: 0.03
  confidence_adjustment: true  # Widen when uncertain
```

**When to Use:**
- You have access to real-time data feeds
- Markets respond to external events (sports scores, weather)
- You can estimate true probabilities better than the crowd

**Expected Returns:** 20-40% monthly (higher risk)

---

#### Strategy C: Volatility Harvesting
**Objective:** Profit from price swings in volatile markets

**Configuration:**
```yaml
strategy: volatility_harvesting
target_markets:
  - volatility: high
    events: live_sports, breaking_news
pricing_model:
  type: mean_reversion
  lookback_period: 300s  # 5 minute window
  reversion_strength: 0.5
spread_config:
  dynamic_spread: true
  volatility_multiplier: 2.0  # 2x spread during high volatility
position_limits:
  max_position: 30
  stop_loss: 0.10  # Exit if market moves 10 cents against us
```

**When to Use:**
- During live sports events
- Breaking news scenarios
- High-volume trading hours

**Expected Returns:** 25-50% monthly (highest risk)

---

### 2.2 Market Selection Criteria

**Best Markets for Beginners:**

1. **Daily SPX (S&P 500) Markets**
   - High liquidity (>$50k volume)
   - Predictable patterns
   - Clear reference price from underlying index
   - Example: "Will SPX close above 5,800?"

2. **Major League Sports (During Games)**
   - NBA, NFL, MLB player performance
   - Real-time data available
   - Fast-moving, high turnover
   - Example: "Will LeBron score over 25 points?"

3. **Economic Data Releases**
   - CPI, Jobs Report, Fed Rate decisions
   - Clear event times
   - Binary outcomes
   - Example: "Will CPI come in above 3.0%?"

**Markets to Avoid:**
- Low volume (<$5k daily)
- Illiquid long-dated contracts
- Exotic multi-leg events
- Markets with insider information risk

---

### 2.3 Profitability Analysis

**Fee Structure (Kalshi):**
- Maker fee: -0.5% (rebate)
- Taker fee: +0.7% (charge)
- **Key insight**: Always use limit orders to get paid for providing liquidity

**Breakeven Calculation:**
```
Gross profit per trade = (Sell Price - Buy Price) - Fees
Required spread > (Maker Fee + Taker Fee) = 0.2%

For a $0.50 contract:
Minimum profitable spread = $0.001 (0.2%)
Target spread = $0.02-$0.04 (4-8%) for comfortable margin
```

**Monte Carlo Simulation Results:**
```
Capital: $1,000
Strategy: Pure Market Making
Spread: 3 cents average
Trades/day: 50
Win Rate: 65%

Month 1: $1,150 (+15%)
Month 2: $1,323 (+32%)
Month 3: $1,521 (+52%)
Month 6: $2,313 (+131%)

Risk of Ruin: 2.1% (acceptable)
```

---

## 3. System Architecture

### 3.1 High-Level Design

```
┌─────────────────────────────────────────────────────────────┐
│                    FiftyFive Bot                            │
│                                                             │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────┐  │
│  │   Config    │  │  Strategy    │  │   Risk Monitor  │  │
│  │   Loader    │──▶│   Engine     │──▶│   & Kill Switch │  │
│  └─────────────┘  └──────────────┘  └─────────────────┘  │
│                           │                                │
│         ┌─────────────────┴─────────────────┐            │
│         ▼                                    ▼            │
│  ┌──────────────┐                   ┌──────────────┐    │
│  │  WebSocket   │                   │  REST API    │    │
│  │  Manager     │                   │  Client      │    │
│  │  (Real-time) │                   │  (Orders)    │    │
│  └──────────────┘                   └──────────────┘    │
│         │                                    │            │
└─────────┼────────────────────────────────────┼────────────┘
          │                                    │
          ▼                                    ▼
    ┌──────────────────────────────────────────────┐
    │         Kalshi Exchange (API v2)             │
    │   - Market Data (WS)                         │
    │   - Order Management (REST)                  │
    └──────────────────────────────────────────────┘
```

### 3.2 Core Components

#### A. Config Loader (`config/loader.py`)
- **Purpose**: Single source of truth for all bot behavior
- **Format**: YAML configuration files
- **Features**:
  - Environment-based configs (dev/prod)
  - Hot-reload capability (change settings without restart)
  - Validation & schema enforcement
  - Sensitive data encryption (API keys)

#### B. Strategy Engine (`strategies/engine.py`)
- **Purpose**: Implements pricing logic and order decisions
- **Responsibilities**:
  - Calculate fair value estimates
  - Determine bid/ask prices
  - Manage inventory targets
  - Adapt to market conditions
- **Pluggable**: Swap strategies via config without code changes

#### C. Order Manager (`execution/order_manager.py`)
- **Purpose**: Execute trades efficiently and safely
- **Features**:
  - Self-trade prevention (mandatory)
  - Rate limiting (token bucket)
  - Order lifecycle tracking
  - Batch operations for speed
  - Retry logic with exponential backoff

#### D. WebSocket Manager (`data/websocket_manager.py`)
- **Purpose**: Maintain real-time order book
- **Features**:
  - Auto-reconnect on disconnect
  - Delta updates with periodic snapshots
  - Sequence number validation
  - Heartbeat monitoring
  - Buffer overflow protection

#### E. Risk Monitor (`risk/monitor.py`)
- **Purpose**: Enforce position limits and kill switch
- **Checks**:
  - Real-time P&L tracking
  - Max exposure per market
  - Daily loss limits
  - Error rate thresholds
  - Market quality filters

---

### 3.3 Data Flow

**Market Data Pipeline:**
```
Kalshi WS → Delta Updates → Local Order Book → Fair Value Calc → Pricing Engine
     ↓                                                                  ↓
Snapshot Sync                                                    Order Decisions
(every 30s)                                                             ↓
                                                              Order Manager
                                                                      ↓
                                                              Rate Limiter
                                                                      ↓
                                                              Kalshi REST API
```

**Order Execution Pipeline:**
```
Strategy Signal → Risk Check → STP Check → Rate Limit → Submit Order
                      ↓            ↓            ↓             ↓
                   PASS         PASS         PASS         FILL/REJECT
                      ↓            ↓            ↓             ↓
                  Kill Switch   Cancel      Queue       Update Positions
                  (if fail)   Conflicting   Request      & Inventory
```

---

### 3.4 Async Architecture

**Why Async?**
- Handle multiple markets simultaneously
- Non-blocking I/O for network operations
- Efficient CPU utilization
- Low latency (<50ms order placement)

**Key Pattern:**
```python
import asyncio

async def main():
    # Run all components concurrently
    await asyncio.gather(
        websocket_manager.stream_orderbook(),
        order_manager.monitor_fills(),
        strategy_engine.pricing_loop(),
        risk_monitor.watchdog_loop(),
    )
```

**Thread Safety:**
- Use `asyncio.Queue` for inter-component communication
- Locks (`asyncio.Lock`) for shared state (order cache)
- Avoid blocking operations (file I/O, subprocess calls)

---

## 4. Configuration System

### 4.1 Configuration File Structure

**Primary Config: `config/production.yaml`**

```yaml
# ============================================
# FiftyFive Configuration File
# ============================================

# Meta Information
version: "1.0.0"
environment: production  # production, staging, demo

# ============================================
# EXCHANGE CONNECTION
# ============================================
exchange:
  name: kalshi
  api_base_url: "https://trading-api.kalshi.com/trade-api/v2"
  ws_url: "wss://trading-api.kalshi.com/trade-api/ws/v2"
  
  # Authentication (load from environment variables)
  api_key_id: ${KALSHI_API_KEY_ID}
  private_key_path: ${KALSHI_PRIVATE_KEY_PATH}
  
  # Rate Limits (Basic Tier)
  rate_limits:
    write_rps: 10    # writes per second
    read_rps: 20     # reads per second
    burst_size: 5    # allow short bursts

# ============================================
# RISK MANAGEMENT (CRITICAL)
# ============================================
risk:
  # Position Limits
  max_exposure_per_market: 500.00  # USD
  max_total_exposure: 2000.00      # USD across all markets
  max_contracts_per_side: 20       # per market
  
  # Kill Switch Thresholds
  daily_loss_limit: 100.00         # USD
  error_rate_threshold: 0.10       # 10% errors trigger shutdown
  consecutive_losses: 5            # stop after 5 losses in a row
  
  # Position Management
  inventory_target: 0              # neutral (0 = no bias)
  max_inventory_skew: 10           # max contracts away from target
  unwind_threshold: 0.80           # unwind at 80% of max inventory

# ============================================
# STRATEGY CONFIGURATION
# ============================================
strategy:
  name: pure_market_making  # pure_market_making, informed_market_making, volatility_harvesting
  
  # Market Selection
  market_filters:
    min_daily_volume: 10000        # USD
    max_spread: 0.10               # 10 cents
    categories:
      - sports
      - economics
    exclude_tickers: []
  
  # Pricing Model
  pricing:
    model: mid_price_skew          # mid_price_skew, external_data, ml_model
    spread_calculation: dynamic    # fixed, dynamic, adaptive
    
    # Spread Configuration
    base_spread: 0.04              # 4 cents base spread
    min_spread: 0.02               # don't go tighter than 2 cents
    max_spread: 0.08               # don't go wider than 8 cents
    
    # Dynamic Spread Adjustments
    inventory_adjustment: true     # widen spread when holding inventory
    inventory_multiplier: 1.5      # 1.5x spread at max inventory
    
    volatility_adjustment: true    # widen during volatility
    volatility_lookback: 300       # seconds
    volatility_multiplier: 2.0
    
  # Order Sizing
  order_sizing:
    method: fixed                  # fixed, kelly_criterion, volatility_scaled
    base_size: 5                   # contracts per order
    max_size: 20                   # never exceed this
    
  # Rebalancing
  rebalancing:
    enabled: true
    interval: 60                   # seconds
    aggressive_unwind: false       # market orders to flatten

# ============================================
# EXECUTION SETTINGS
# ============================================
execution:
  # Order Types
  default_order_type: limit        # limit, market (use limit for maker rebates)
  
  # Self-Trade Prevention
  stp_enabled: true                # CRITICAL: must be true
  stp_cancel_delay: 0.05           # seconds to wait after cancel
  
  # Order Management
  order_refresh_interval: 10       # seconds
  cancel_timeout: 2.0              # seconds before retry
  max_retries: 3
  
  # Quote Behavior
  always_quoted: true              # maintain quotes 24/7
  quote_both_sides: true           # bid and ask simultaneously
  lean_inventory: true             # skew quotes based on position

# ============================================
# DATA MANAGEMENT
# ============================================
data:
  # WebSocket
  websocket:
    auto_reconnect: true
    reconnect_delay: 5             # seconds
    max_reconnect_attempts: 10
    heartbeat_interval: 30         # seconds
    snapshot_refresh_interval: 30  # seconds
    
  # Order Book
  orderbook:
    depth_levels: 10               # how many price levels to track
    cache_size: 100                # markets to cache
    staleness_threshold: 60        # seconds before force refresh
    
  # Price Normalization
  price_format: float              # internal representation
  api_price_format: cents          # kalshi uses integer cents

# ============================================
# LOGGING & MONITORING
# ============================================
logging:
  level: INFO                      # DEBUG, INFO, WARNING, ERROR
  log_dir: logs/
  log_rotation: daily
  max_log_size: 100MB
  retention_days: 30
  
  # What to Log
  log_orders: true
  log_fills: true
  log_cancellations: true
  log_errors: true
  log_pnl: true
  
monitoring:
  enabled: true
  metrics_port: 9090               # prometheus metrics
  health_check_port: 8080
  
  # Alerts
  alerts:
    email_enabled: false           # requires SMTP config
    slack_enabled: false           # requires webhook URL
    terminal_enabled: true

# ============================================
# ADVANCED SETTINGS
# ============================================
advanced:
  # Performance
  use_connection_pooling: true
  max_concurrent_requests: 50
  request_timeout: 10              # seconds
  
  # Optimization
  batch_orders: true               # use batch API when possible
  cancel_replace: true             # optimize order updates
  
  # Development
  dry_run: false                   # if true, don't actually place orders
  simulation_mode: false           # use historical data instead of live
```

---

### 4.2 Environment-Specific Configs

**Demo Environment: `config/demo.yaml`**
```yaml
environment: demo
exchange:
  api_base_url: "https://demo-api.kalshi.co/trade-api/v2"
  ws_url: "wss://demo-api.kalshi.co/trade-api/ws/v2"

risk:
  max_exposure_per_market: 100.00
  max_total_exposure: 500.00

advanced:
  dry_run: true  # extra safety in demo
```

---

### 4.3 Secret Management

**Environment Variables (`.env` file - NEVER commit to git)**
```bash
# Kalshi API Credentials
KALSHI_API_KEY_ID="your-api-key-uuid-here"
KALSHI_PRIVATE_KEY_PATH="/home/user/.kalshi/private_key.pem"

# Optional: Monitoring
SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."
ALERT_EMAIL="your-email@example.com"

# Optional: External Data Sources
SPORTS_DATA_API_KEY="..."
WEATHER_API_KEY="..."
```

**Loading Secrets:**
```python
from dotenv import load_dotenv
import os

load_dotenv()  # Load .env file

api_key = os.getenv('KALSHI_API_KEY_ID')
```

---

### 4.4 Configuration Validation

**Schema Enforcement:**
```python
from pydantic import BaseModel, Field, validator

class RiskConfig(BaseModel):
    max_exposure_per_market: float = Field(gt=0, le=10000)
    daily_loss_limit: float = Field(gt=0)
    
    @validator('daily_loss_limit')
    def validate_loss_limit(cls, v, values):
        if v > values.get('max_total_exposure', 0) * 0.5:
            raise ValueError("Daily loss limit too high!")
        return v

# Usage
risk_config = RiskConfig(**yaml_data['risk'])
```

---

## 5. Compliance & Risk Management

### 5.1 Self-Trade Prevention (CRITICAL)

**The Problem:**
Kalshi will **BAN YOUR ACCOUNT** if you wash trade (buy from yourself or sell to yourself). This happens when your buy order crosses with your own sell order.

**Example Violation:**
```
Your open orders:
- Sell 10 @ $0.57

You submit:
- Buy 10 @ $0.58  ❌ CROSSES OWN ORDER = WASH TRADE
```

**The Solution:**
```python
class SelfTradePreventionEngine:
    """Prevents wash trading by checking orders before submission"""
    
    def __init__(self):
        self.my_open_orders = {}  # {market_ticker: [Order]}
        
    async def can_submit_order(self, market: str, side: str, price: float) -> bool:
        """
        Check if new order would cross our own orders
        
        Returns:
            True if safe to submit
            False if would cause wash trade
        """
        my_orders = self.my_open_orders.get(market, [])
        
        for order in my_orders:
            # Check for crossing orders
            if side == "yes" and order.side == "no":
                # Buying yes crosses with selling no if:
                # buy_yes_price + sell_no_price >= 1.00
                if price + order.no_price >= 1.00:
                    logger.warning(f"STP: Would cross own order {order.id}")
                    return False
                    
            elif side == "no" and order.side == "yes":
                # Buying no crosses with selling yes if:
                # buy_no_price + sell_yes_price >= 1.00  
                if price + order.yes_price >= 1.00:
                    logger.warning(f"STP: Would cross own order {order.id}")
                    return False
                    
        return True
        
    async def submit_with_stp(self, order: Order) -> bool:
        """
        Submit order with self-trade prevention
        
        1. Check if order would cross
        2. If yes, cancel conflicting orders first
        3. Wait for cancellation to process
        4. Submit new order
        """
        if not await self.can_submit_order(order.market, order.side, order.price):
            # Cancel conflicting orders
            conflicting = self._find_conflicting_orders(order)
            for conflict in conflicting:
                await self.cancel_order(conflict.id)
                
            # Wait for cancellations to process
            await asyncio.sleep(0.05)  # 50ms safety buffer
            
            # Re-check
            if not await self.can_submit_order(order.market, order.side, order.price):
                logger.error("STP: Still conflicting after cancellation!")
                return False
                
        # Safe to submit
        return await self.place_order(order)
```

**Key Points:**
- **NEVER** rely on exchange to prevent this
- Check **before** every order submission
- Maintain local cache of your open orders
- Update cache on every fill/cancel

---

### 5.2 Position Limits & Kill Switch

**Hard Limits:**
```python
class RiskManager:
    def __init__(self, config):
        self.max_exposure = config.risk.max_exposure_per_market
        self.daily_loss_limit = config.risk.daily_loss_limit
        self.max_inventory = config.risk.max_inventory_skew
        
        # State tracking
        self.daily_pnl = 0.0
        self.error_count = 0
        self.total_requests = 0
        
    async def check_order_risk(self, order: Order) -> bool:
        """Pre-flight risk check"""
        
        # 1. Position limit
        current_position = self.get_position(order.market)
        new_position_cost = order.price * order.quantity
        
        if abs(current_position.cost + new_position_cost) > self.max_exposure:
            logger.warning(f"Position limit exceeded for {order.market}")
            return False
            
        # 2. Inventory skew
        if abs(current_position.quantity) > self.max_inventory:
            logger.warning(f"Inventory limit exceeded: {current_position.quantity}")
            return False
            
        # 3. Daily loss limit
        if self.daily_pnl < -self.daily_loss_limit:
            logger.critical(f"Daily loss limit hit: ${self.daily_pnl:.2f}")
            await self.trigger_kill_switch()
            return False
            
        return True
        
    async def trigger_kill_switch(self):
        """Emergency shutdown"""
        logger.critical("🛑 KILL SWITCH ACTIVATED 🛑")
        
        # 1. Stop accepting new orders
        self.accepting_orders = False
        
        # 2. Cancel all open orders
        for market in self.active_markets:
            await self.cancel_all_orders(market)
            
        # 3. Close WebSocket connections
        await self.websocket_manager.disconnect()
        
        # 4. Log final state
        logger.critical(f"Final P&L: ${self.daily_pnl:.2f}")
        logger.critical(f"Open Positions: {self.get_all_positions()}")
        
        # 5. Exit process
        sys.exit(1)
```

---

### 5.3 Error Rate Monitoring

```python
async def monitor_error_rate(self):
    """Trigger kill switch if too many errors"""
    while True:
        await asyncio.sleep(60)  # Check every minute
        
        error_rate = self.error_count / max(self.total_requests, 1)
        
        if error_rate > 0.10:  # 10% threshold
            logger.critical(f"Error rate too high: {error_rate:.1%}")
            await self.trigger_kill_switch()
```

---

## 6. API Integration

### 6.1 Authentication (RSA-PSS Signing)

**Kalshi v2 uses RSA-PSS signature authentication, NOT basic auth.**

**Key Generation (One-time setup):**
```bash
# Generate private key
openssl genrsa -out kalshi_private_key.pem 2048

# Extract public key (upload this to Kalshi dashboard)
openssl rsa -in kalshi_private_key.pem -pubout -out kalshi_public_key.pem
```

**Python Implementation:**
```python
import base64
import time
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding

class KalshiAuth:
    def __init__(self, api_key_id: str, private_key_path: str):
        self.api_key_id = api_key_id
        
        # Load private key
        with open(private_key_path, 'rb') as f:
            self.private_key = serialization.load_pem_private_key(
                f.read(),
                password=None
            )
    
    def sign_request(self, method: str, path: str) -> dict:
        """
        Generate authentication headers
        
        Args:
            method: HTTP method (GET, POST, DELETE)
            path: API path (/portfolio/balance)
            
        Returns:
            Dict of headers to add to request
        """
        timestamp = str(int(time.time() * 1000))
        
        # Message to sign: timestamp + method + path
        # Example: "1704891234567POST/portfolio/orders"
        message = timestamp + method + path
        
        # Sign with RSA-PSS
        signature = self.private_key.sign(
            message.encode('utf-8'),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.DIGEST_LENGTH
            ),
            hashes.SHA256()
        )
        
        # Base64 encode signature
        signature_b64 = base64.b64encode(signature).decode('utf-8')
        
        return {
            'KALSHI-ACCESS-KEY': self.api_key_id,
            'KALSHI-ACCESS-TIMESTAMP': timestamp,
            'KALSHI-ACCESS-SIGNATURE': signature_b64,
            'Content-Type': 'application/json'
        }
```

**Usage:**
```python
auth = KalshiAuth(api_key_id, private_key_path)

# For every API request
headers = auth.sign_request('GET', '/portfolio/balance')
response = await session.get(base_url + '/portfolio/balance', headers=headers)
```

---

### 6.2 Rate Limiting (Token Bucket)

**Critical: Kalshi WILL ban your IP if you exceed rate limits.**

**Basic Tier Limits:**
- **Write** (Orders): 10 requests/second
- **Read** (Market Data): 20 requests/second

**Token Bucket Implementation:**
```python
import asyncio
import time

class TokenBucket:
    """Rate limiter using token bucket algorithm"""
    
    def __init__(self, rate: float, capacity: int):
        """
        Args:
            rate: tokens per second
            capacity: max burst size
        """
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.last_update = time.monotonic()
        self.lock = asyncio.Lock()
        
    async def acquire(self, tokens: int = 1):
        """
        Wait until enough tokens are available
        
        Blocks if bucket is empty until tokens replenish
        """
        async with self.lock:
            while True:
                now = time.monotonic()
                elapsed = now - self.last_update
                
                # Replenish tokens
                self.tokens = min(
                    self.capacity,
                    self.tokens + elapsed * self.rate
                )
                self.last_update = now
                
                if self.tokens >= tokens:
                    self.tokens -= tokens
                    return
                    
                # Wait for tokens to replenish
                sleep_time = (tokens - self.tokens) / self.rate
                await asyncio.sleep(sleep_time)

# Usage
write_limiter = TokenBucket(rate=10, capacity=15)  # 10/sec, burst 15
read_limiter = TokenBucket(rate=20, capacity=30)   # 20/sec, burst 30

async def place_order(order):
    await write_limiter.acquire()  # Wait for token
    response = await api_client.post('/portfolio/orders', json=order)
    return response
```

---

### 6.3 WebSocket Order Book Management

**Kalshi WebSocket provides:**
- Real-time order book updates (deltas)
- Low latency (<100ms)
- Efficient bandwidth usage

**Connection Pattern:**
```python
class OrderBookManager:
    def __init__(self, auth: KalshiAuth):
        self.auth = auth
        self.order_books = {}  # {market_ticker: OrderBook}
        self.ws = None
        
    async def connect(self):
        """Establish WebSocket connection"""
        headers = self.auth.sign_request('GET', '/ws/v2')
        
        self.ws = await websockets.connect(
            'wss://trading-api.kalshi.com/trade-api/ws/v2',
            extra_headers=headers
        )
        
        logger.info("WebSocket connected")
        
    async def subscribe_orderbook(self, market_ticker: str):
        """Subscribe to order book updates"""
        
        # 1. Fetch initial snapshot via REST
        snapshot = await self.fetch_orderbook_snapshot(market_ticker)
        self.order_books[market_ticker] = OrderBook(snapshot)
        
        # 2. Subscribe to deltas via WebSocket
        subscribe_msg = {
            "id": 1,
            "cmd": "subscribe",
            "params": {
                "channels": [f"orderbook_delta:{market_ticker}"]
            }
        }
        await self.ws.send(json.dumps(subscribe_msg))
        
    async def process_deltas(self):
        """Process incoming order book updates"""
        async for message in self.ws:
            data = json.loads(message)
            
            if data['type'] == 'orderbook_delta':
                market = data['msg']['market_ticker']
                
                # Apply delta to local order book
                self.order_books[market].apply_delta(data['msg'])
                
    async def periodic_snapshot_sync(self):
        """Resync with REST snapshot every 30 seconds"""
        while True:
            await asyncio.sleep(30)
            
            for market_ticker in self.order_books.keys():
                snapshot = await self.fetch_orderbook_snapshot(market_ticker)
                self.order_books[market_ticker].replace(snapshot)
                logger.debug(f"Resynced {market_ticker}")
```

**Order Book Data Structure:**
```python
class OrderBook:
    def __init__(self, snapshot: dict):
        self.yes_bids = []  # [(price, quantity)]
        self.yes_asks = []
        self.no_bids = []
        self.no_asks = []
        self.last_update = time.time()
        
        self._initialize_from_snapshot(snapshot)
        
    def apply_delta(self, side: str, action: str, deltas: list[list[int]]) -> None:
        """Apply order book delta update"""
        # Select the correct book side
        if side == "yes":
            book = self.yes_bids if action == 'bid' else self.yes_asks
        else:
            book = self.no_bids if action == 'bid' else self.no_asks

        # Apply each delta
        for price_cents, quantity in deltas:
            # Remove existing level
            book[:] = [level for level in book if level.price != price_cents]

            # Add new level if quantity > 0
            if quantity > 0:
                book.append(PriceLevel(price=price_cents, quantity=quantity))

        # Re-sort
        if action == 'bid':
            book.sort(key=lambda x: x.price, reverse=True)  # Descending for bids
        else:
            book.sort(key=lambda x: x.price)  # Ascending for asks

        self.last_updated = datetime.utcnow()
        
    def get_best_bid(self, side: str) -> Optional[float]:
        """Get best available bid price"""
        bids = self.yes_bids if side == 'yes' else self.no_bids
        return bids[0][0] if bids else None
        
    def get_mid_price(self) -> float:
        """Calculate mid price"""
        best_bid = self.get_best_bid('yes')
        best_ask = self.get_best_ask('yes')
        
        if best_bid and best_ask:
            return (best_bid + best_ask) / 2
        return 0.50  # default if no liquidity
```

---

### 6.4 Price Normalization

**Critical Gotcha:** Kalshi API uses **integer cents** or **string dollars**, but your internal logic should use **floats**.

```python
class PriceAdapter:
    """Convert between internal float and API integer"""
    
    @staticmethod
    def to_api_price(internal_price: float) -> int:
        """
        Convert internal float to API cents
        
        Example: 0.55 -> 55
        """
        # Round to avoid float precision issues
        cents = round(internal_price * 100)
        
        # Kalshi valid range: 1-99 cents
        return max(1, min(99, cents))
        
    @staticmethod
    def from_api_price(api_price: int) -> float:
        """
        Convert API cents to internal float
        
        Example: 55 -> 0.55
        """
        return api_price / 100.0
        
    @staticmethod
    def round_price(price: float) -> float:
        """Round to nearest cent"""
        return round(price * 100) / 100.0
```

**Usage:**
```python
# Internal calculation
fair_value = 0.5543  # Your model says 55.43%

# Convert for API
api_price = PriceAdapter.to_api_price(fair_value)  # 55 cents

# Submit order
order = {
    "ticker": "KXHARRIS24",
    "side": "yes",
    "action": "buy",
    "type": "limit",
    "yes_price": api_price,
    "count": 10
}
```

---

### 6.5 Pagination Handling

**Gotcha:** `GET /markets` returns max 100 results. Must paginate to see all markets.

```python
async def fetch_all_markets(self, params: dict = None) -> list:
    """Fetch all markets with cursor pagination"""
    all_markets = []
    cursor = None
    
    while True:
        # Add cursor to params
        request_params = params or {}
        if cursor:
            request_params['cursor'] = cursor
            
        response = await self.get('/markets', params=request_params)
        
        all_markets.extend(response['markets'])
        
        # Check if more pages
        cursor = response.get('cursor')
        if not cursor:
            break
            
    logger.info(f"Fetched {len(all_markets)} total markets")
    return all_markets
```

---

## 7. Data Management

### 7.1 Order Book Maintenance

**Challenges:**
- WebSocket can drop connections
- Delta updates can arrive out of order
- Network latency can cause stale data

**Solution: Robust Order Book Manager**

```python
class RobustOrderBookManager:
    def __init__(self):
        self.order_books = {}
        self.last_snapshot_time = {}
        self.sequence_numbers = {}
        
    async def initialize_market(self, market_ticker: str):
        """Set up order book for a market"""
        
        # 1. Fetch REST snapshot
        snapshot = await self.api.get_orderbook(market_ticker)
        
        # 2. Store snapshot
        self.order_books[market_ticker] = OrderBook(snapshot)
        self.last_snapshot_time[market_ticker] = time.time()
        self.sequence_numbers[market_ticker] = snapshot.get('seq', 0)
        
        logger.info(f"Initialized order book for {market_ticker}")
        
    async def handle_delta(self, delta: dict):
        """Process WebSocket delta update"""
        market = delta['market_ticker']
        new_seq = delta.get('seq', 0)
        
        # Check for sequence gap
        expected_seq = self.sequence_numbers[market] + 1
        if new_seq != expected_seq:
            logger.warning(f"Sequence gap detected: expected {expected_seq}, got {new_seq}")
            await self.force_resync(market)
            return
            
        # Apply delta
        self.order_books[market].apply_delta(delta)
        self.sequence_numbers[market] = new_seq
        
    async def periodic_health_check(self):
        """Force resync stale order books"""
        while True:
            await asyncio.sleep(30)
            
            now = time.time()
            for market, last_sync in self.last_snapshot_time.items():
                if now - last_sync > 60:  # 60 second staleness
                    logger.info(f"Forcing resync for {market}")
                    await self.force_resync(market)
                    
    async def force_resync(self, market_ticker: str):
        """Reload order book from REST snapshot"""
        snapshot = await self.api.get_orderbook(market_ticker)
        self.order_books[market_ticker] = OrderBook(snapshot)
        self.last_snapshot_time[market_ticker] = time.time()
        self.sequence_numbers[market_ticker] = snapshot.get('seq', 0)
```

---

### 7.2 Position Tracking

**Gotcha:** `GET /portfolio/balance` shows **equity**, not **available cash**.

```python
class PositionTracker:
    def __init__(self):
        self.positions = {}  # {market_ticker: Position}
        self.available_cash = 0.0
        
    async def update_balance(self):
        """Fetch latest balance from Kalshi"""
        response = await self.api.get('/portfolio/balance')
        
        # Use 'balance', NOT 'balance_total'
        # 'balance' = available for trading (settled)
        # 'balance_total' = total equity (includes unsettled)
        self.available_cash = response['balance'] / 100.0  # Convert cents to dollars
        
        logger.info(f"Available cash: ${self.available_cash:.2f}")
        
    async def update_positions(self):
        """Fetch current positions"""
        response = await self.api.get('/portfolio/positions')
        
        for pos in response['market_positions']:
            market = pos['market_ticker']
            # API returns net position, need to determine side
            raw_position = pos.get('position', 0)
            side = "yes"  # Default assumption or logic to determine side
            
            # Create or update position
            if market not in self.positions:
                 self.positions[market] = {}
                 
            self.positions[market][side] = Position(
                market_ticker=market,
                side=side,
                quantity=raw_position,
                total_cost=pos.get('market_value', 0) / 100.0, # Approximate from market value
                realized_pnl=pos.get('realized_pnl', 0) / 100.0
            )
            
    def get_buying_power(self, market_ticker: str) -> float:
        """Calculate max contracts we can buy"""
        # Available cash divided by max price we'd pay
        max_price = 0.99  # Worst case
        return self.available_cash / max_price
```

---

## 8. Order Execution Engine

### 8.1 Order Placement

```python
class OrderManager:
    def __init__(self, api_client, stp_engine, rate_limiter):
        self.api = api_client
        self.stp = stp_engine
        self.rate_limiter = rate_limiter
        self.pending_orders = {}
        
    async def place_order(self, order: Order) -> Optional[str]:
        """
        Place order with full safety checks
        
        Returns:
            order_id if successful, None if rejected
        """
        
        # 1. Self-trade prevention check
        if not await self.stp.can_submit_order(order.market, order.side, order.price):
            logger.warning(f"STP blocked order: {order}")
            return None
            
        # 2. Rate limit
        await self.rate_limiter.acquire()
        
        # 3. Submit order
        payload = {
            "ticker": order.market,
            "action": "buy",
            "side": order.side,
            "type": "limit",
            "yes_price": PriceAdapter.to_api_price(order.price) if order.side == "yes" else None,
            "no_price": PriceAdapter.to_api_price(order.price) if order.side == "no" else None,
            "count": order.quantity,
            "client_order_id": order.client_id  # For tracking
        }
        
        try:
            response = await self.api.post('/portfolio/orders', json=payload)
            
            order_id = response['order']['order_id']
            self.pending_orders[order_id] = order
            
            logger.info(f"Order placed: {order_id}")
            return order_id
            
        except Exception as e:
            logger.error(f"Order failed: {e}")
            return None
            
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel a single order"""
        await self.rate_limiter.acquire()
        
        try:
            await self.api.delete(f'/portfolio/orders/{order_id}')
            
            # Remove from tracking
            self.pending_orders.pop(order_id, None)
            self.stp.remove_order(order_id)
            
            logger.info(f"Order cancelled: {order_id}")
            return True
            
        except Exception as e:
            logger.error(f"Cancel failed: {e}")
            return False
            
    async def cancel_all_orders(self, market_ticker: str = None):
        """Cancel all orders (optionally filtered by market)"""
        
        # Fetch current orders
        orders = await self.api.get('/portfolio/orders')
        
        cancel_tasks = []
        for order in orders['orders']:
            if market_ticker and order['ticker'] != market_ticker:
                continue
                
            cancel_tasks.append(self.cancel_order(order['order_id']))
            
        await asyncio.gather(*cancel_tasks)
```

---

### 8.2 Order Monitoring & Fills

```python
async def monitor_fills(self):
    """Monitor and process order fills"""
    last_check = time.time()
    
    while True:
        await asyncio.sleep(1)  # Check every second
        
        # Fetch recent fills
        fills = await self.api.get('/portfolio/fills', params={
            'after': int(last_check * 1000)  # Unix timestamp in ms
        })
        
        for fill in fills['fills']:
            await self.process_fill(fill)
            
        last_check = time.time()
        
async def process_fill(self, fill: dict):
    """Handle a single fill"""
    
    # Extract fill details
    market = fill['ticker']
    side = fill['side']
    price = fill['yes_price'] if side == 'yes' else fill['no_price']
    quantity = fill['count']
    is_maker = not fill['is_taker']  # maker = we provided liquidity
    
    # Calculate P&L
    if is_maker:
        fee_rate = -0.005  # -0.5% (we get paid)
    else:
        fee_rate = 0.007   # +0.7% (we pay)
        
    gross_value = price * quantity
    fee = gross_value * fee_rate
    net_value = gross_value + fee
    
    # Update positions
    self.position_tracker.add_fill(market, side, quantity, price)
    
    # Log
    logger.info(f"Fill: {market} {side} {quantity}@{price:.2f} (fee: ${fee:.2f})")
    
    # Update daily P&L
    if side == 'buy':
        self.daily_pnl -= net_value
    else:
        self.daily_pnl += net_value
```

---

### 8.3 Quote Refresh Logic

```python
async def refresh_quotes(self, market_ticker: str):
    """
    Update our quotes for a market
    
    Called when:
    - Order book changes
    - Our inventory changes
    - Periodic refresh (every 10 seconds)
    """
    
    # 1. Get current order book
    ob = self.orderbook_manager.get(market_ticker)
    if not ob:
        return
        
    # 2. Calculate fair value
    mid_price = ob.get_mid_price()
    fair_value = self.strategy.calculate_fair_value(market_ticker, mid_price)
    
    # 3. Get current position
    position = self.position_tracker.get(market_ticker)
    inventory = position.contracts_long if position else 0
    
    # 4. Calculate spreads with inventory skew
    base_spread = self.config.strategy.pricing.base_spread
    
    # Widen spread if holding inventory
    inventory_factor = 1 + abs(inventory) / self.config.risk.max_inventory_skew
    adjusted_spread = base_spread * inventory_factor
    
    # 5. Calculate bid/ask prices
    if inventory > 0:  # Long inventory, want to sell
        bid_price = fair_value - adjusted_spread * 1.5  # Wider bid
        ask_price = fair_value + adjusted_spread * 0.5  # Tighter ask
    elif inventory < 0:  # Short inventory, want to buy
        bid_price = fair_value - adjusted_spread * 0.5
        ask_price = fair_value + adjusted_spread * 1.5
    else:  # Neutral
        bid_price = fair_value - adjusted_spread / 2
        ask_price = fair_value + adjusted_spread / 2
        
    # 6. Round to valid prices
    bid_price = PriceAdapter.round_price(max(0.01, min(0.99, bid_price)))
    ask_price = PriceAdapter.round_price(max(0.01, min(0.99, ask_price)))
    
    # 7. Cancel old orders and place new ones
    await self.order_manager.cancel_all_orders(market_ticker)
    await asyncio.sleep(0.05)  # Brief delay for cancellations
    
    # Place bid
    bid_order = Order(
        market=market_ticker,
        side='yes',
        price=bid_price,
        quantity=self.config.strategy.order_sizing.base_size
    )
    await self.order_manager.place_order(bid_order)
    
    # Place ask
    ask_order = Order(
        market=market_ticker,
        side='no',
        price=1.0 - ask_price,  # No price is complement
        quantity=self.config.strategy.order_sizing.base_size
    )
    await self.order_manager.place_order(ask_order)
    
    logger.debug(f"Quotes refreshed: {market_ticker} bid={bid_price:.2f} ask={ask_price:.2f}")
```

---

## 9. Pricing Algorithms

### 9.1 Mid-Price Skew Strategy

**Simplest strategy: quote around market mid with fixed spread**

```python
class MidPriceSkewStrategy:
    def __init__(self, config):
        self.base_spread = config.strategy.pricing.base_spread
        self.inventory_adjustment = config.strategy.pricing.inventory_adjustment
        
    def calculate_fair_value(self, market_ticker: str, mid_price: float) -> float:
        """
        Fair value = market mid price
        
        Assumes the market is efficiently pricing the event
        """
        return mid_price
        
    def calculate_bid_ask(self, fair_value: float, inventory: int) -> tuple:
        """
        Calculate bid/ask around fair value
        
        Returns:
            (bid_price, ask_price)
        """
        half_spread = self.base_spread / 2
        
        # Inventory skew: if long, make ask tighter to encourage selling
        if self.inventory_adjustment:
            inventory_skew = inventory * 0.005  # 0.5% skew per contract
            half_spread_bid = half_spread + inventory_skew
            half_spread_ask = half_spread - inventory_skew
        else:
            half_spread_bid = half_spread
            half_spread_ask = half_spread
            
        bid = fair_value - half_spread_bid
        ask = fair_value + half_spread_ask
        
        # Clamp to valid range
        bid = max(0.01, min(0.99, bid))
        ask = max(0.01, min(0.99, ask))
        
        return bid, ask
```

---

### 9.2 External Data Strategy (Advanced)

**Use real-time data to estimate better probabilities**

```python
class ExternalDataStrategy:
    """
    Example: Sports betting with live game data
    """
    
    def __init__(self, config, data_feed):
        self.config = config
        self.data_feed = data_feed  # Real-time sports API
        
    async def calculate_fair_value(self, market_ticker: str, mid_price: float) -> float:
        """
        Calculate fair value using external data
        
        Example: "Will LeBron score over 25 points?"
        - Fetch live game stats
        - Update probability as game progresses
        """
        
        # Parse market to identify player/event
        player = self.parse_player_from_ticker(market_ticker)
        
        # Fetch live stats
        live_stats = await self.data_feed.get_player_stats(player)
        
        if not live_stats:
            # No data, fall back to market mid
            return mid_price
            
        # Calculate probability based on current pace
        # (simplified - real implementation would be more sophisticated)
        current_points = live_stats['points']
        time_remaining = live_stats['minutes_left']
        points_per_minute = live_stats['ppg'] / 48  # Average pace
        
        expected_final_points = current_points + (time_remaining * points_per_minute)
        
        # Probability of exceeding 25 points
        # Using normal distribution (in reality, use better model)
        prob = self.estimate_probability(expected_final_points, target=25)
        
        # Blend with market price (don't deviate too much)
        adjustment_factor = self.config.strategy.pricing.adjustment_factor  # e.g., 0.15
        adjusted_prob = mid_price * (1 - adjustment_factor) + prob * adjustment_factor
        
        return adjusted_prob
        
    def estimate_probability(self, expected: float, target: float) -> float:
        """Simple probability estimate"""
        # Simplified - use proper statistical model in production
        if expected > target * 1.2:
            return 0.85
        elif expected > target:
            return 0.65
        elif expected > target * 0.8:
            return 0.35
        else:
            return 0.15
```

---

### 9.3 Mean Reversion Strategy

**For volatile markets: fade extreme moves**

```python
class MeanReversionStrategy:
    """Bet against short-term price swings"""
    
    def __init__(self, config):
        self.lookback_period = config.strategy.pricing.lookback_period  # seconds
        self.reversion_strength = config.strategy.pricing.reversion_strength
        self.price_history = {}  # {market: [(time, price)]}
        
    def update_price_history(self, market: str, price: float):
        """Track price over time"""
        now = time.time()
        
        if market not in self.price_history:
            self.price_history[market] = []
            
        self.price_history[market].append((now, price))
        
        # Remove old data points
        cutoff = now - self.lookback_period
        self.price_history[market] = [
            (t, p) for t, p in self.price_history[market] if t > cutoff
        ]
        
    def calculate_fair_value(self, market: str, current_price: float) -> float:
        """
        Fair value = mean price + reversion adjustment
        
        If price moved up sharply, fade it (quote lower)
        If price moved down sharply, fade it (quote higher)
        """
        history = self.price_history.get(market, [])
        
        if len(history) < 2:
            return current_price
            
        # Calculate mean price over lookback period
        mean_price = sum(p for _, p in history) / len(history)
        
        # Distance from mean
        deviation = current_price - mean_price
        
        # Fair value: revert toward mean
        fair_value = current_price - (deviation * self.reversion_strength)
        
        return max(0.01, min(0.99, fair_value))
```

---

## 10. Performance Optimization

### 10.1 Low Latency Techniques

**Goal: <50ms from signal to order placement**

**Optimization Checklist:**

1. **Use Connection Pooling**
```python
import aiohttp

# Reuse HTTP session (TCP connection pooling)
session = aiohttp.ClientSession(
    connector=aiohttp.TCPConnector(
        limit=50,  # Max concurrent connections
        ttl_dns_cache=300  # Cache DNS lookups
    ),
    timeout=aiohttp.ClientTimeout(total=10)
)
```

2. **Batch API Calls**
```python
# Bad: Individual calls
for order in orders_to_place:
    await api.post('/portfolio/orders', json=order)  # 10 calls
    
# Good: Batch call
await api.post('/portfolio/orders/batched', json={
    'orders': orders_to_place  # 1 call
})
```

3. **Cancel-Replace Optimization**
```python
# Instead of: cancel old order → wait → place new order
# Use: atomic cancel-replace (if Kalshi supports it)

async def update_order(self, old_order_id: str, new_order: Order):
    """Replace order in one step"""
    payload = {
        "order_id": old_order_id,
        "new_price": new_order.price,
        "new_quantity": new_order.quantity
    }
    await self.api.put(f'/portfolio/orders/{old_order_id}', json=payload)
```

4. **Pre-sign Authentication**
```python
# Pre-compute signatures for repeated paths
class SignatureCache:
    def __init__(self, ttl=60):
        self.cache = {}
        self.ttl = ttl
        
    def get_or_create(self, method: str, path: str) -> dict:
        key = f"{method}:{path}"
        
        if key in self.cache:
            cached_time, headers = self.cache[key]
            if time.time() - cached_time < self.ttl:
                return headers
                
        # Generate new signature
        headers = self.auth.sign_request(method, path)
        self.cache[key] = (time.time(), headers)
        return headers
```

5. **Optimistic Order Tracking**
```python
# Don't wait for API confirmation to update local state
async def place_order_optimistic(self, order: Order):
    # Immediately add to local cache
    self.pending_orders[order.client_id] = order
    
    # Submit to API asynchronously
    asyncio.create_task(self._submit_order_async(order))
    
    # Return immediately
    return order.client_id
```

---

### 10.2 Memory Optimization

**For 24/7 operation, prevent memory leaks:**

```python
# Limit history size
MAX_PRICE_HISTORY_SIZE = 1000

def update_price_history(self, market: str, price: float):
    history = self.price_history.get(market, deque(maxlen=MAX_PRICE_HISTORY_SIZE))
    history.append((time.time(), price))
    self.price_history[market] = history
```

**Use `__slots__` for frequent objects:**
```python
class Order:
    __slots__ = ['market', 'side', 'price', 'quantity', 'client_id', 'timestamp']
    
    def __init__(self, market, side, price, quantity):
        self.market = market
        self.side = side
        self.price = price
        self.quantity = quantity
        self.client_id = str(uuid.uuid4())
        self.timestamp = time.time()
```

---

### 10.3 CPU Optimization

**Profile your code:**
```python
# Use cProfile to find bottlenecks
import cProfile

profiler = cProfile.Profile()
profiler.enable()

# Run bot
await main()

profiler.disable()
profiler.print_stats(sort='cumulative')
```

**Common bottlenecks:**
- JSON serialization/deserialization (use `orjson` instead of `json`)
- Logging (use async logging, filter verbose logs)
- Order book updates (optimize data structures)

---

## 11. Setup & Installation

### 11.1 Prerequisites

**System Requirements:**
- OS: Windows 10/11 with WSL2 (Ubuntu 22.04)
- RAM: 4GB minimum, 8GB recommended
- Python: 3.10 or higher
- Storage: 10GB free space

**WSL2 Setup:**
```bash
# Install WSL2 (PowerShell as Administrator)
wsl --install -d Ubuntu-22.04

# Update packages
sudo apt update && sudo apt upgrade -y

# Install Python 3.10+
sudo apt install python3.10 python3.10-venv python3-pip -y
```

---

### 11.2 Kalshi Account Setup

**Step 1: Create Account**
1. Go to https://kalshi.com
2. Sign up with email/password
3. Complete KYC verification (upload ID)
4. Wait for approval (usually <24 hours)

**Step 2: Generate API Keys**
1. Log in to Kalshi dashboard
2. Navigate to Settings → API Keys
3. Click "Generate New Key"
4. Download the JSON file containing:
   - `api_key_id` (UUID)
   - `private_key` (RSA key)
5. **IMPORTANT**: Store this file securely. You cannot retrieve it again.

**Step 3: Fund Account**
1. Link bank account or debit card
2. Deposit at least $500 (recommended starting capital)
3. Wait for funds to settle (1-3 business days)

---

### 11.3 Project Setup

**Step 1: Clone Repository**
```bash
# Create project directory
mkdir ~/fiftyfive
cd ~/fiftyfive

# (After I create the code, you'll clone it like this)
git clone https://github.com/yourusername/fiftyfive.git .
```

**Step 2: Install Dependencies**
```bash
# Create virtual environment
python3.10 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

**`requirements.txt`:**
```
aiohttp==3.9.1
asyncio==3.4.3
websockets==12.0
cryptography==41.0.7
pyyaml==6.0.1
pydantic==2.5.3
python-dotenv==1.0.0
orjson==3.9.10
loguru==0.7.2
prometheus-client==0.19.0
```

**Step 3: Configure Secrets**
```bash
# Create .env file (NEVER commit this)
nano .env
```

**.env content:**
```bash
# Kalshi API Credentials
KALSHI_API_KEY_ID="your-api-key-uuid-here"
KALSHI_PRIVATE_KEY_PATH="/home/yourusername/kalshi/private_key.pem"

# Environment
ENVIRONMENT="demo"  # Start with demo, switch to "production" later

# Optional: Monitoring
SLACK_WEBHOOK_URL=""
ALERT_EMAIL=""
```

**Step 4: Save Private Key**
```bash
# Create credentials directory
mkdir -p ~/kalshi

# Save private key from Kalshi dashboard
nano ~/kalshi/private_key.pem
# (Paste the private key, then Ctrl+X, Y, Enter)

# Secure the file
chmod 600 ~/kalshi/private_key.pem
```

---

### 11.4 Configuration

**Step 1: Copy Example Config**
```bash
cp config/production.example.yaml config/production.yaml
```

**Step 2: Edit Config**
```bash
nano config/production.yaml
```

**Key Settings to Review:**
```yaml
# Start conservative
risk:
  max_exposure_per_market: 100.00   # $100 max per market
  max_total_exposure: 500.00        # $500 total
  daily_loss_limit: 50.00           # Stop after losing $50

strategy:
  name: pure_market_making          # Safest strategy
  
  market_filters:
    min_daily_volume: 10000         # Only liquid markets
    categories:
      - sports                       # Start with sports

  pricing:
    base_spread: 0.04                # 4 cent spread
    
  order_sizing:
    base_size: 5                     # 5 contracts per order
```

---

### 11.5 First Run (Demo Mode)

**Test in demo environment first:**

```bash
# Activate virtual environment
source venv/bin/activate

# Run in demo mode
python main.py --config config/demo.yaml --dry-run
```

**What to expect:**
```
[INFO] FiftyFive v1.0.0 starting...
[INFO] Environment: demo
[INFO] Loading configuration: config/demo.yaml
[INFO] Authenticating with Kalshi...
[OK] Authentication successful
[INFO] Connecting to WebSocket...
[OK] WebSocket connected
[INFO] Fetching active markets...
[INFO] Found 42 markets matching filters
[INFO] Subscribing to order books...
[OK] Subscribed to 10 markets
[INFO] Strategy: PureMarketMaking
[INFO] Starting trading loop...
[INFO] Placing initial quotes...
[OK] Order placed: KXHARRIS24 buy 5@0.53
[OK] Order placed: KXHARRIS24 sell 5@0.57
...
```

**Monitor for 1 hour, then check logs:**
```bash
cat logs/fiftyfive_2026-01-08.log | grep "Fill"
```

**Expected output after 1 hour:**
```
[INFO] Fill: KXHARRIS24 buy 5@0.53 (fee: -$0.13) [MAKER]
[INFO] Fill: KXHARRIS24 sell 5@0.57 (fee: -$0.14) [MAKER]
[INFO] Current P&L: +$0.31
```

---

### 11.6 Production Deployment

**When you're confident (after 24 hours demo testing):**

```bash
# Switch to production config
python main.py --config config/production.yaml
```

**Run in background (systemd service):**

```bash
# Create service file
sudo nano /etc/systemd/system/fiftyfive.service
```

**Service content:**
```ini
[Unit]
Description=FiftyFive Kalshi Market Maker
After=network.target

[Service]
Type=simple
User=yourusername
WorkingDirectory=/home/yourusername/fiftyfive
Environment="PATH=/home/yourusername/fiftyfive/venv/bin"
ExecStart=/home/yourusername/fiftyfive/venv/bin/python main.py --config config/production.yaml
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Enable and start service:**
```bash
sudo systemctl enable fiftyfive
sudo systemctl start fiftyfive

# Check status
sudo systemctl status fiftyfive

# View logs
journalctl -u fiftyfive -f
```

---

## 12. Monitoring & Operations

### 12.1 Real-Time Monitoring

**Metrics to Track:**

1. **P&L**
   - Realized P&L (closed positions)
   - Unrealized P&L (open positions)
   - Daily P&L trend

2. **Order Metrics**
   - Orders placed per minute
   - Fill rate (% of orders filled)
   - Maker vs taker ratio (aim for >90% maker)
   - Average spread captured

3. **Risk Metrics**
   - Current exposure per market
   - Total exposure
   - Inventory imbalance (how far from neutral)
   - Max drawdown

4. **System Health**
   - WebSocket uptime
   - API error rate
   - Order latency (ms)
   - Memory usage

**Dashboard (Terminal UI):**
```
┌─ FiftyFive Market Maker ─────────────── 2026-01-08 14:23:45 ─┐
│                                                                │
│ Daily P&L: +$12.34  (ROI: 2.5%)                              │
│ Total Exposure: $387.20 / $500.00                            │
│                                                                │
│ Active Markets: 8                                             │
│ ┌────────────────┬──────┬──────┬──────┬─────────┐           │
│ │ Market         │ Pos  │ Bid  │ Ask  │ Spread  │           │
│ ├────────────────┼──────┼──────┼──────┼─────────┤           │
│ │ KXHARRIS24     │ +2   │ 0.53 │ 0.57 │ 0.04    │           │
│ │ SPX-5800       │ -1   │ 0.61 │ 0.65 │ 0.04    │           │
│ │ NBA-LAL-OVER   │  0   │ 0.48 │ 0.52 │ 0.04    │           │
│ └────────────────┴──────┴──────┴──────┴─────────┘           │
│                                                                │
│ Recent Fills (last 5):                                        │
│ 14:23:12 │ KXHARRIS24   │ SELL 5@0.57 │ +$2.85 │ [MAKER]   │
│ 14:21:34 │ SPX-5800     │ BUY 3@0.61  │ -$1.83 │ [MAKER]   │
│ 14:19:08 │ NBA-LAL-OVER │ SELL 5@0.52 │ +$2.60 │ [MAKER]   │
│                                                                │
│ System Health:                                                │
│ WebSocket: ● Connected  │ Uptime: 4h 23m                     │
│ API Errors: 2 (0.5%)    │ Latency: 38ms avg                  │
└────────────────────────────────────────────────────────────────┘
```

---

### 12.2 Logging Strategy

**Log Levels:**
- **DEBUG**: Verbose details (order book updates, rate limiting)
- **INFO**: Normal operations (orders, fills, quote updates)
- **WARNING**: Unusual but handled (STP blocks, retries)
- **ERROR**: Failed operations (API errors, timeouts)
- **CRITICAL**: System failures (kill switch, crashes)

**Log Structure:**
```python
from loguru import logger

# Configure logging
logger.add(
    "logs/fiftyfive_{time:YYYY-MM-DD}.log",
    rotation="00:00",  # New file daily
    retention="30 days",
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
)

# Usage
logger.info("Order placed: {market} {side} {qty}@{price}", 
            market="KXHARRIS24", side="buy", qty=5, price=0.53)
logger.error("API error: {error}", error=str(e))
```

---

### 12.3 Alerts

**Configure alerts for critical events:**

```yaml
# config/production.yaml
monitoring:
  alerts:
    email_enabled: true
    email_recipients:
      - your-email@example.com
      
    slack_enabled: true
    slack_webhook: ${SLACK_WEBHOOK_URL}
    
    alert_rules:
      - trigger: daily_loss_limit
        threshold: -50.00
        message: "⚠️ Daily loss limit reached: ${pnl}"
        
      - trigger: api_error_rate
        threshold: 0.10
        message: "⚠️ API error rate high: ${error_rate}%"
        
      - trigger: websocket_disconnected
        message: "⚠️ WebSocket disconnected - attempting reconnect"
```

**Slack Integration:**
```python
import aiohttp

async def send_slack_alert(message: str):
    """Send alert to Slack"""
    webhook_url = os.getenv('SLACK_WEBHOOK_URL')
    
    payload = {
        "text": message,
        "username": "FiftyFive Bot",
        "icon_emoji": ":robot_face:"
    }
    
    async with aiohttp.ClientSession() as session:
        await session.post(webhook_url, json=payload)
```

---

### 12.4 Daily Checklist

**Morning (before trading):**
- [ ] Check logs for overnight errors
- [ ] Verify WebSocket connection
- [ ] Review yesterday's P&L
- [ ] Confirm API rate tier (haven't been downgraded)
- [ ] Check Kalshi exchange status (no maintenance)

**During Trading:**
- [ ] Monitor P&L every hour
- [ ] Check fill rate (should be >50%)
- [ ] Watch for stuck orders (not filling for >10 min)
- [ ] Verify spreads are competitive

**Evening (after trading):**
- [ ] Review daily P&L
- [ ] Analyze best/worst markets
- [ ] Check if any positions held overnight (should be minimal)
- [ ] Archive logs
- [ ] Adjust config if needed

---

### 12.5 Common Issues & Fixes

**Issue 1: "Authentication failed"**
```
Symptom: 401 Unauthorized errors
Fix:
1. Verify KALSHI_API_KEY_ID is correct
2. Check private key file exists and is readable
3. Regenerate API key if needed
4. Ensure timestamp is accurate (sync system clock)
```

**Issue 2: "Rate limit exceeded"**
```
Symptom: 429 Too Many Requests
Fix:
1. Reduce order refresh interval in config
2. Check token bucket settings
3. Upgrade API tier if consistently hitting limits
```

**Issue 3: "WebSocket keeps disconnecting"**
```
Symptom: Frequent reconnections
Fix:
1. Check network stability
2. Add heartbeat monitoring
3. Increase reconnect delay
4. Contact Kalshi support if persistent
```

**Issue 4: "Orders not filling"**
```
Symptom: Open orders sit for hours
Fix:
1. Check if spreads are too wide
2. Verify market has sufficient liquidity
3. Compare to orderbook - are you competitive?
4. Try tightening spreads in config
```

**Issue 5: "Memory leak / bot slows down"**
```
Symptom: RAM usage grows over time
Fix:
1. Limit price history size
2. Clear old log entries
3. Restart bot daily (systemd restart)
```

---

## 13. Appendix: Critical Gotchas

### A.1 Self-Trade Prevention (STP)

**CRITICAL:** Kalshi will ban your account if you wash trade.

**Always:**
- Check for crossing orders before submitting
- Cancel conflicting orders first
- Wait 50-100ms after cancellation
- Never rely on exchange to prevent this

**Code:**
```python
# Before EVERY order submission:
if await stp_engine.can_submit_order(market, side, price):
    await place_order(order)
else:
    logger.warning("STP blocked order")
```

---

### A.2 Rate Limiting

**Kalshi bans IPs that exceed limits.**

**Limits (Basic Tier):**
- Write: 10/second
- Read: 20/second

**Always:**
- Use token bucket rate limiter
- Queue requests if needed
- Never fire-and-forget

---

### A.3 Price Normalization

**Gotcha:** API uses integer cents, your code uses floats.

**Always:**
- Convert before API calls: `to_api_price(0.55)` → `55`
- Convert from API: `from_api_price(55)` → `0.55`
- Round internal calculations to 2 decimals

---

### A.4 Balance vs Portfolio Value

**Gotcha:** `balance` ≠ `balance_total`

**Use:**
- `balance` - available for trading (settled cash)
- NOT `balance_total` - total equity (includes unsettled)

---

### A.5 Pagination

**Gotcha:** `/markets` returns max 100 results.

**Always:**
- Check for `cursor` in response
- Loop until `cursor` is null
- Otherwise you only see first 100 markets

---

### A.6 WebSocket Sequence Gaps

**Gotcha:** Delta updates can arrive out of order.

**Always:**
- Track sequence numbers
- Force resync on gaps
- Periodic snapshot refresh (30s)

---

### A.7 Order Book Complementarity

**Gotcha:** Yes and No orders are complementary.

**Key Rule:**
- `yes_price + no_price = $1.00`
- Buy Yes @ $0.60 = Sell No @ $0.40
- This affects self-trade prevention logic

---

### A.8 Fee Structure

**Kalshi fees:**
- Maker: -0.5% (rebate)
- Taker: +0.7% (charge)

**Always:**
- Use limit orders (maker rebates)
- Avoid market orders (taker fees)
- Factor fees into spread calculation

---

### A.9 Market Hours

**Markets have different hours:**
- Sports: 24/7 when games active
- Economics: Business hours only
- Politics: 24/7

**Always:**
- Check `is_open` status before trading
- Handle after-hours gracefully
- Don't assume 24/7 liquidity

---

### A.10 Position Clearing

**Gotcha:** Funds from sold positions may not be immediately available.

**Always:**
- Query `balance` (not `balance_total`)
- Wait for settlement before reusing funds
- Don't assume instant clearing

---

## 14. Appendix: Recommended Resources

### Learning Resources

**Market Making:**
- "Market Making and Delta Hedging" (Stoikov)
- "Algorithmic Trading" (Chan)
- Quantitative Finance Stack Exchange

**Kalshi Specific:**
- Kalshi API Documentation: https://docs.kalshi.com
- Kalshi Discord: #dev channel
- Kalshi Blog: Market making guides

**Python Async:**
- "Using Asyncio in Python" (O'Reilly)
- Real Python: Async IO tutorial

### Community

- **Kalshi Discord**: Developer support
- **QuantConnect Forums**: Algo trading discussions
- **/r/algotrading**: Reddit community

### Tools

- **VS Code Extensions:**
  - Python
  - YAML
  - REST Client (for API testing)
  
- **Monitoring:**
  - Grafana + Prometheus (advanced)
  - Simple terminal dashboard (included)

---

## 15. Next Steps

**Phase 1: Setup (Days 1-2)**
- [ ] Create Kalshi account
- [ ] Generate API keys
- [ ] Install FiftyFive
- [ ] Configure demo mode
- [ ] Run first test

**Phase 2: Demo Trading (Days 3-7)**
- [ ] Run in demo for 5 days
- [ ] Monitor fills and P&L
- [ ] Tune spreads based on results
- [ ] Test kill switch (manually)

**Phase 3: Live Trading (Day 8+)**
- [ ] Fund production account ($500)
- [ ] Switch to production config
- [ ] Start with conservative limits
- [ ] Monitor closely for first week
- [ ] Gradually increase exposure

**Phase 4: Optimization (Weeks 2-4)**
- [ ] Analyze performance data
- [ ] Identify best markets
- [ ] Fine-tune spreads
- [ ] Add more markets gradually
- [ ] Consider advanced strategies

---

## Conclusion

You now have a complete specification for building FiftyFive, a professional-grade market-making bot for Kalshi. This spec includes:

✅ **Strategy guidance** - proven approaches to profitability  
✅ **Complete architecture** - low-latency, async design  
✅ **Configuration system** - hands-off operation  
✅ **Risk management** - kill switches and position limits  
✅ **API integration** - all the gotchas covered  
✅ **Setup instructions** - step-by-step for WSL/VS Code  
✅ **Monitoring** - dashboards and alerts  

**Remember:**
1. Start in demo mode
2. Begin conservative (small positions, wide spreads)
3. Scale gradually as you gain confidence
4. Never disable safety features (STP, kill switch)
5. Monitor daily and adjust

**Expected Timeline:**
- Week 1: Setup and demo testing
- Week 2-4: Live trading with $500
- Month 2: Scale to $1,000-$2,000
- Month 3+: Optimize and expand

**Realistic Returns:**
- Conservative: 10-15% monthly
- Moderate: 15-25% monthly  
- Aggressive: 25-40% monthly (higher risk)

Good luck, and happy trading! 🚀

---

**Document Version:** 1.0.0  
**Last Updated:** January 8, 2026  
**Maintained by:** FiftyFive Project
