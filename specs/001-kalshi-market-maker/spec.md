# Feature Specification: Kalshi Market Maker Bot

**Feature Branch**: `001-kalshi-market-maker`
**Created**: 2026-01-08
**Status**: Draft
**Input**: User description: "FiftyFive: Automated market-making bot for Kalshi prediction markets that provides liquidity by continuously posting buy and sell orders, profiting from bid-ask spreads"

# SYSTEM CONSTRAINTS (WINDOWS)
**CRITICAL:** This project is running on Windows with Git Bash.
1.  **NO BASH WRITES:** Do NOT use `cat`, `echo`, or bash redirection (`>`) to write files. It causes `Exit code 2` and CRLF errors.
2.  **USE NATIVE TOOLS:** Always use the native `Write` tool.
3.  **HANDLE LOCKS:** If `Write` fails due to "unexpected modification," do NOT switch to Bash. Ask the user to close the file instead.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Pure Market Making with Automated Liquidity (Priority: P1)

A trader wants to earn passive income by providing liquidity to prediction markets without taking directional bets. They configure the bot with conservative risk limits, select liquid sports markets, and let it run autonomously to capture bid-ask spreads.

**Why this priority**: This is the core value proposition and lowest-risk strategy. It's the foundation that all other features build upon and delivers immediate value with minimal market knowledge required.

**Independent Test**: Can be fully tested by configuring the bot with demo credentials, setting risk limits ($100 max per market), and verifying it places balanced buy/sell orders that capture spreads without accumulating inventory.

**Acceptance Scenarios**:

1. **Given** the bot is configured with pure market making strategy and $500 capital, **When** liquid markets are available, **Then** the bot places balanced bid/ask orders within configured spread (2-4 cents)
2. **Given** the bot has open orders on both sides, **When** an order fills, **Then** the bot immediately refreshes quotes to maintain balanced exposure
3. **Given** the bot accumulates inventory (>10 contracts), **When** quotes are refreshed, **Then** spreads widen on the heavy side to encourage unwinding
4. **Given** the bot is running, **When** it completes a round-trip trade (buy then sell), **Then** realized P&L reflects the captured spread minus fees

---

### User Story 2 - Risk Management and Position Limits (Priority: P1)

A trader wants to protect their capital by enforcing strict position limits and automatic shutdown triggers. They configure maximum exposure per market, daily loss limits, and error thresholds that automatically halt trading when breached.

**Why this priority**: Risk management is critical for capital preservation and is required before any real money trading. Without this, users could face unlimited losses.

**Independent Test**: Can be fully tested by configuring risk limits ($50 daily loss, $100 per market), then simulating adverse scenarios (rapid price movements, consecutive losses) and verifying the bot stops trading when thresholds are hit.

**Acceptance Scenarios**:

1. **Given** daily loss limit is set to $50, **When** cumulative losses reach $50, **Then** the bot cancels all orders, closes WebSocket connections, and exits with critical alert
2. **Given** maximum exposure per market is $100, **When** a new order would exceed this limit, **Then** the order is rejected and logged
3. **Given** inventory limit is 20 contracts, **When** position reaches 20 contracts, **Then** no new orders are placed on that side until inventory is reduced
4. **Given** error rate threshold is 10%, **When** API errors exceed 10% of requests, **Then** kill switch activates and trading halts
5. **Given** the bot detects 5 consecutive losing trades, **When** the fifth loss occurs, **Then** trading pauses and an alert is sent

---

### User Story 3 - Self-Trade Prevention (Priority: P1)

A trader needs to avoid wash trading violations that would result in account suspension. The bot checks every order before submission to ensure it won't cross with existing orders, canceling conflicting orders first if necessary.

**Why this priority**: Self-trade prevention is mandatory for compliance with Kalshi rules. Account bans are permanent, making this a critical safety feature that must work before any trading occurs.

**Independent Test**: Can be fully tested by submitting orders that would cross (e.g., buy yes at $0.58 when sell yes exists at $0.57), verifying the bot cancels the conflicting order first, waits for cancellation confirmation, then places the new order.

**Acceptance Scenarios**:

1. **Given** the bot has an open sell order at $0.57, **When** it attempts to place a buy order at $0.58, **Then** the conflicting sell order is cancelled first, a 50ms delay occurs, then the buy order is submitted
2. **Given** the bot tracks all open orders locally, **When** an order fills or is cancelled, **Then** the local cache is immediately updated
3. **Given** a new order would cross existing orders, **When** self-trade check runs, **Then** the crossing condition is detected before API submission
4. **Given** complementary yes/no orders exist, **When** checking for crosses, **Then** the bot correctly evaluates yes_price + no_price >= $1.00 condition

---

### User Story 4 - Real-Time Order Book Management (Priority: P2)

A trader needs accurate, real-time market data to price orders competitively. The bot maintains a local order book via WebSocket updates, syncing periodically with REST snapshots to ensure data accuracy.

**Why this priority**: Accurate pricing depends on current order book state. Without this, the bot would place non-competitive orders that never fill or would lose money on stale data.

**Independent Test**: Can be fully tested by subscribing to a market's order book, verifying delta updates are applied correctly, and confirming periodic snapshot syncs detect and correct any drift from the exchange state.

**Acceptance Scenarios**:

1. **Given** the bot subscribes to a market, **When** order book updates arrive via WebSocket, **Then** local order book reflects changes within 100ms
2. **Given** WebSocket connection drops, **When** reconnection occurs, **Then** the bot fetches a fresh snapshot and resumes delta updates
3. **Given** sequence numbers in deltas, **When** a gap is detected, **Then** the bot forces a snapshot resync
4. **Given** 30 seconds have elapsed, **When** periodic sync runs, **Then** local order book is refreshed from REST API snapshot
5. **Given** order book data is available, **When** calculating fair value, **Then** mid-price is computed from best bid and best ask

---

### User Story 5 - Rate Limiting and API Compliance (Priority: P2)

A trader wants to avoid IP bans from exceeding Kalshi's rate limits. The bot uses a token bucket algorithm to queue requests and ensure write operations stay under 10/second and reads under 20/second.

**Why this priority**: Rate limit violations result in IP bans, which would completely halt trading. This protection must be in place before high-frequency operation.

**Independent Test**: Can be fully tested by configuring rate limits (10 writes/sec, 20 reads/sec), submitting bursts of requests, and verifying the bot queues them appropriately without exceeding limits.

**Acceptance Scenarios**:

1. **Given** write rate limit is 10/second, **When** 15 orders are submitted simultaneously, **Then** the first 10 execute immediately and the remaining 5 are queued for the next second
2. **Given** token bucket allows bursts, **When** short burst of 15 requests occurs after idle period, **Then** burst is allowed (up to capacity limit)
3. **Given** tokens are depleted, **When** a new request arrives, **Then** it waits until tokens replenish before executing
4. **Given** separate read and write limiters, **When** both types of requests occur, **Then** they are tracked independently

---

### User Story 6 - Dynamic Spread Adjustment (Priority: P3)

A trader wants the bot to adapt spreads based on market conditions and inventory. The bot widens spreads during high volatility or when holding inventory, and tightens them in stable, balanced conditions.

**Why this priority**: Dynamic spreads optimize profitability by reducing risk during uncertainty and increasing competitiveness in favorable conditions. This is an enhancement to the core market making function.

**Independent Test**: Can be fully tested by configuring spread adjustment factors (inventory multiplier 1.5x, volatility multiplier 2x), then verifying spreads change appropriately when inventory accumulates or price volatility increases.

**Acceptance Scenarios**:

1. **Given** base spread is 4 cents and inventory is neutral, **When** quotes are generated, **Then** bid and ask are each 2 cents from fair value
2. **Given** inventory reaches 15 contracts long, **When** quotes refresh, **Then** ask spread tightens (0.5x) and bid spread widens (1.5x)
3. **Given** price volatility over 5 minutes exceeds threshold, **When** spreads are calculated, **Then** both bid and ask spreads are multiplied by volatility factor (2x)
4. **Given** spreads are adjusted dynamically, **When** inventory returns to neutral and volatility normalizes, **Then** spreads return to base configuration

---

### User Story 7 - Market Selection and Filtering (Priority: P3)

A trader wants to focus on profitable markets by filtering based on liquidity, category, and spread width. The bot automatically discovers and subscribes to markets matching configured criteria (e.g., sports markets with >$10k daily volume).

**Why this priority**: Market selection affects profitability but is not required for basic operation. Traders can manually specify markets initially, making this an optimization feature.

**Independent Test**: Can be fully tested by configuring market filters (min volume $10k, categories: sports, max spread 10 cents), then verifying only matching markets are selected from available markets.

**Acceptance Scenarios**:

1. **Given** market filters specify min volume $10k, **When** markets are discovered, **Then** only markets with daily volume >= $10k are selected
2. **Given** category filter includes sports and economics, **When** markets are evaluated, **Then** politics and weather markets are excluded
3. **Given** max spread is 10 cents, **When** a market has 12 cent spread, **Then** it is filtered out
4. **Given** markets are paginated, **When** fetching all markets, **Then** the bot iterates through all pages using cursor pagination

---

### User Story 8 - Performance Monitoring and Alerts (Priority: P3)

A trader wants visibility into bot performance through real-time metrics (P&L, fill rate, exposure) and alerts for critical events (loss limits, errors, disconnections). The bot logs all activity and sends notifications via configured channels.

**Why this priority**: Monitoring enables optimization and early problem detection but is not required for basic trading functionality. Manual log review can substitute initially.

**Independent Test**: Can be fully tested by running the bot for 1 hour, then verifying logs contain all orders/fills/errors, P&L is accurately tracked, and test alerts are sent when thresholds are simulated.

**Acceptance Scenarios**:

1. **Given** the bot is running, **When** orders are placed and filled, **Then** all events are logged with timestamps, market, price, and quantity
2. **Given** daily P&L tracking, **When** trades are executed, **Then** realized P&L reflects fills and fees accurately
3. **Given** alert rules are configured, **When** daily loss limit is hit, **Then** Slack/email alert is sent with P&L details
4. **Given** WebSocket disconnects, **When** reconnection attempt starts, **Then** warning alert is sent
5. **Given** logs are configured with daily rotation, **When** midnight occurs, **Then** a new log file is created and old logs are retained for 30 days

---

### Edge Cases

- **What happens when the bot starts with existing open orders?** The bot queries existing orders via REST API on startup, populates the self-trade prevention cache, and integrates them into its tracking before placing new orders.

- **What happens when Kalshi API is down or returns errors?** The bot implements exponential backoff retry logic (3 attempts), and if errors persist, increments the error rate counter which may trigger the kill switch if threshold is exceeded.

- **What happens when WebSocket connection is lost during active trading?** The bot detects the disconnect via heartbeat timeout, immediately stops placing new orders, attempts reconnection with exponential backoff, and resyncs order books from REST snapshots upon reconnection.

- **What happens when market closes while bot has open orders?** The bot receives market status updates via WebSocket, detects the closure, cancels all open orders for that market, and removes it from active trading until it reopens.

- **What happens when the bot has inventory at end of day?** The bot continues holding positions overnight (no forced liquidation), adjusts spreads to encourage unwinding, and logs the positions for risk monitoring. Aggressive unwind mode (market orders) can be enabled via configuration.

- **What happens when authentication signature expires?** The bot generates a new signature with fresh timestamp for every request, so signatures never expire. If authentication fails (wrong key), the bot logs a critical error and exits.

- **What happens when buy and sell orders both fill simultaneously?** Both fills are processed independently, P&L is updated for each trade, and inventory returns closer to neutral. This is the ideal outcome for market making.

- **What happens when order prices are below minimum (1 cent) or above maximum (99 cents)?** The price adapter clamps prices to valid range [1, 99] cents before API submission, preventing rejection.

- **What happens when available cash is insufficient for new orders?** The position tracker calculates buying power before orders, and the risk check rejects orders that would exceed available cash.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST authenticate with Kalshi API v2 using RSA-PSS signature authentication with API key ID and private key
- **FR-002**: System MUST maintain real-time order book for subscribed markets via WebSocket connection with delta updates
- **FR-003**: System MUST check every order against open orders before submission to prevent self-trade violations
- **FR-004**: System MUST enforce rate limits of 10 write requests/second and 20 read requests/second using token bucket algorithm
- **FR-005**: System MUST calculate fair value for each market based on configured pricing strategy (mid-price, external data, or mean reversion)
- **FR-006**: System MUST place limit orders on both bid and ask sides with spreads configured in strategy settings
- **FR-007**: System MUST track positions per market including contracts held, average entry price, and unrealized P&L
- **FR-008**: System MUST enforce maximum exposure limits per market and total portfolio exposure
- **FR-009**: System MUST track daily P&L and trigger kill switch when daily loss limit is exceeded
- **FR-010**: System MUST cancel conflicting orders before submitting new orders that would cross
- **FR-011**: System MUST refresh quotes periodically (configurable interval, default 10 seconds) or when inventory changes
- **FR-012**: System MUST adjust spreads based on inventory skew when inventory adjustment is enabled
- **FR-013**: System MUST handle WebSocket disconnections with automatic reconnection and order book resync
- **FR-014**: System MUST convert between internal float prices (0.00-1.00) and Kalshi API integer cents (1-99)
- **FR-015**: System MUST log all orders, fills, cancellations, errors, and P&L changes with timestamps
- **FR-016**: System MUST fetch all markets using cursor pagination when discovering trading opportunities
- **FR-017**: System MUST filter markets based on configured criteria (volume, category, spread, liquidity)
- **FR-018**: System MUST monitor error rate and trigger kill switch when threshold (default 10%) is exceeded
- **FR-019**: System MUST validate configuration on startup using schema enforcement
- **FR-020**: System MUST load credentials from environment variables, never from hardcoded values
- **FR-021**: System MUST track sequence numbers for order book deltas and force resync on gaps
- **FR-022**: System MUST sync order book snapshots via REST API periodically (default 30 seconds)
- **FR-023**: System MUST calculate buying power based on available settled balance, not total equity
- **FR-024**: System MUST support dry-run mode where orders are simulated but not submitted
- **FR-025**: System MUST support multiple pricing strategies selectable via configuration (pure market making, informed market making, volatility harvesting)
- **FR-026**: System MUST send alerts via configured channels (Slack, email, terminal) for critical events
- **FR-027**: System MUST rotate logs daily and retain for configured period (default 30 days)
- **FR-028**: System MUST operate asynchronously to handle multiple markets concurrently without blocking

### Key Entities

- **Market**: A Kalshi prediction market with ticker symbol, category, status, volume, and order book
- **Order**: A limit order with market ticker, side, action, price (0.01-0.99), quantity, and client ID
- **Position**: Holdings in a market including quantity (net position), side, total cost, and P&L (realized/unrealized)
- **OrderBook**: Real-time order book with bids/asks at multiple price levels, sequence ID, and last updated timestamp
- **Fill**: Executed trade with market ticker, side, price, quantity, timestamp, maker/taker fees, and net proceeds
- **RiskLimits**: Configured thresholds including max exposure, daily loss limit, inventory target/skew, and error rate
- **Strategy**: Pricing configuration with strategy type, spread settings, inventory adjustment factors, and order sizing parameters
- **RateLimit**: Token bucket with rate (requests/second), capacity (burst size), current token count, and last refill timestamp

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Trader can configure and start the bot in demo mode within 10 minutes of setup completion
- **SC-002**: Bot places first orders within 30 seconds of startup when markets are available
- **SC-003**: Bot maintains 24/7 operation with >99% uptime (excluding planned restarts)
- **SC-004**: Order placement latency from signal to API submission averages <50ms
- **SC-005**: Self-trade prevention successfully blocks 100% of crossing orders in testing
- **SC-006**: Kill switch activates within 1 second when any risk threshold is exceeded
- **SC-007**: Bot achieves >90% maker ratio (vs taker) on all filled orders
- **SC-008**: WebSocket reconnects automatically within 30 seconds of disconnection
- **SC-009**: Order book accuracy matches exchange snapshot on >99% of periodic syncs
- **SC-010**: Rate limiting prevents any API limit violations during normal operation
- **SC-011**: Bot captures minimum 2 cent average spread on profitable round-trip trades
- **SC-012**: Inventory remains within configured limits (±20 contracts default) >95% of trading time
- **SC-013**: Daily P&L tracking accuracy matches Kalshi portfolio balance within $0.10
- **SC-014**: All critical events (kills switch, errors, disconnections) generate alerts within 5 seconds
- **SC-015**: Configuration changes via YAML take effect within 60 seconds without restart (hot reload)
- **SC-016**: Bot processes >50 order book updates per second per market without lag
- **SC-017**: Log entries for all trades are written within 100ms of event occurrence
- **SC-018**: Market selection filters correctly identify profitable markets (>$10k volume) from full market list
- **SC-019**: Spread adjustments based on inventory occur within one quote refresh cycle (10 seconds)
- **SC-020**: Bot returns to neutral inventory (±5 contracts) within 4 hours during normal market conditions

## Scope & Boundaries *(mandatory)*

### In Scope

- Automated market making on Kalshi prediction markets via API v2
- Three core strategies: Pure Market Making, Informed Market Making (external data), Volatility Harvesting
- Real-time order book management via WebSocket with REST snapshot fallback
- Self-trade prevention to ensure compliance with Kalshi wash trading rules
- Position and risk management with configurable limits and kill switch
- Rate limiting to prevent API violations and IP bans
- Dynamic spread adjustment based on inventory and volatility
- Market discovery and filtering based on liquidity and category
- Authentication using RSA-PSS signatures
- Comprehensive logging of all trading activity
- Alert notifications for critical events via Slack/email/terminal
- Demo mode for testing without real money
- Configuration via YAML files with environment variable support
- Deployment on Windows WSL2/Ubuntu via systemd service

### Out of Scope

- Trading on exchanges other than Kalshi (no multi-exchange support)
- Web-based user interface or dashboard (terminal/logs only)
- Historical backtesting engine (manual analysis of logs only)
- Machine learning models for price prediction (external data integration supported but models not included)
- Portfolio optimization across multiple strategies simultaneously
- High-frequency trading features requiring <10ms latency
- Options, futures, or derivatives (Kalshi binary contracts only)
- Automated strategy parameter tuning or optimization
- Social features, user accounts, or multi-user support
- Mobile application or remote monitoring (local operation only)
- Integration with external portfolio management tools
- Tax reporting or accounting features
- Paper trading simulation with synthetic order books (uses real demo exchange)

### Assumptions

- User has a verified Kalshi account with API access enabled
- User has deposited sufficient capital ($500+ recommended) for market making
- User has generated RSA key pair and registered public key with Kalshi
- User has basic command line and YAML editing skills
- User operates on Windows with WSL2 Ubuntu environment
- User has stable internet connection for real-time trading
- Kalshi API v2 remains stable and backward compatible
- Kalshi fee structure remains -0.5% maker / +0.7% taker
- Kalshi rate limits remain 10 writes/sec, 20 reads/sec for Basic tier
- Markets maintain sufficient liquidity (>$10k daily volume) for profitable market making
- User monitors bot daily and reviews logs for issues
- User starts with conservative risk limits and increases gradually
- User tests thoroughly in demo environment before production trading
- Python 3.10+ and required dependencies are available in WSL2 environment
- User has VS Code or equivalent editor for configuration management

### Dependencies

- Kalshi API v2 availability and uptime
- Kalshi demo environment for testing
- WebSocket and REST API endpoints responding within normal latency (<500ms)
- Kalshi market data feed providing real-time updates
- User's internet connection and local machine uptime
- Kalshi maintaining current authentication method (RSA-PSS)
- Python 3.10+ runtime environment
- External libraries: aiohttp, websockets, cryptography, pyyaml, pydantic, python-dotenv, orjson, loguru
- WSL2 for Windows users or native Linux environment
- Systemd for background process management (optional but recommended)
- Optional: Slack webhook or SMTP server for alert notifications
- Optional: External data feeds (sports APIs, weather APIs) for informed market making strategy

## Open Questions

*No open questions at this time. All requirements are sufficiently specified based on the comprehensive technical specification provided.*

---

## Notes

This specification is derived from the comprehensive technical specification document (FIFTYFIVE_SPEC.md) which contains detailed implementation guidance, code examples, and architectural decisions. This user-focused specification extracts the "what" and "why" while deferring the "how" to the planning and implementation phases.

The specification prioritizes features by their criticality to safe, compliant trading:
- **P1 (Critical)**: Core market making, risk management, and compliance features required before any real money trading
- **P2 (Important)**: Data accuracy and operational reliability features needed for consistent profitability
- **P3 (Nice to Have)**: Optimization and convenience features that improve performance but aren't strictly required for operation

Each user story is independently testable, allowing incremental development and validation. The P1 stories together form a minimal viable product (MVP) capable of safe, profitable market making on Kalshi.
