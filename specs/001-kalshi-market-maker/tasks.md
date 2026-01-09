# Tasks: Kalshi Market Maker Bot (FiftyFive)

**Input**: Design documents from `/specs/001-kalshi-market-maker/`
**Prerequisites**: plan.md (tech stack), spec.md (user stories), research.md, data-model.md, contracts/

**Tests**: NOT included - implementation-focused (can add tests later if desired)

**Organization**: Tasks grouped by user story for independent implementation and testing

## Format: `- [ ] [ID] [P?] [Story?] Description with file path`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: User story label (US1, US2, US3, etc.)
- Exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: Project initialization

- [ ] T001 Create project directory structure: src/, config/, tests/, logs/
- [ ] T002 Initialize Python 3.10+ virtual environment and install dependencies
- [ ] T003 [P] Create .env.example with KALSHI_API_KEY_ID, KALSHI_PRIVATE_KEY_PATH, ENVIRONMENT
- [ ] T004 [P] Create .gitignore excluding .env, logs/, venv/, __pycache__/
- [ ] T005 [P] Create README.md with project overview
- [ ] T006 [P] Create requirements.txt: aiohttp, websockets, cryptography, pyyaml, pydantic, python-dotenv, orjson, loguru, pytest, pytest-asyncio

---

## Phase 2: Foundational (CRITICAL - Blocks All User Stories)

**Purpose**: Core infrastructure required before ANY user story

- [ ] T007 [P] Create src/__init__.py
- [ ] T008 [P] Define base enums (OrderSide, OrderAction, OrderStatus, MarketStatus) in src/models/order.py
- [ ] T009 [P] Implement PriceAdapter in src/api/price_adapter.py with to_api_price(), from_api_price()
- [ ] T010 [P] Implement TokenBucket in src/utils/rate_limiter.py with async acquire()
- [ ] T011 [P] Setup logger in src/utils/logger.py with daily rotation and structured format
- [ ] T012 [P] Create config schema models in src/models/config.py (Config, RiskConfig, StrategyConfig)
- [ ] T013 Implement ConfigLoader in src/config/loader.py with YAML parsing, Pydantic validation
- [ ] T014 [P] Create config/production.example.yaml and config/demo.yaml
- [ ] T015 [P] Implement RSA-PSS auth in src/api/auth.py with sign_request()
- [ ] T016 Create REST API client in src/api/client.py with aiohttp, connection pooling, rate limiting

**Checkpoint**: Foundation ready for user stories

---

## Phase 3: US3 - Self-Trade Prevention (P1) SAFETY FIRST

**Goal**: Prevent wash trading violations - MANDATORY before any trading

**Independent Test**: Submit crossing orders, verify STP cancels conflicting first, waits 50ms, then submits

- [ ] T017 [P] [US3] Create Order model in src/models/order.py
- [ ] T018 [P] [US3] Create Fill model in src/models/order.py
- [ ] T019 [US3] Implement STP engine in src/execution/stp_engine.py with can_submit_order()
- [ ] T020 [US3] Add order cache to STP: add_order(), remove_order(), update_on_fill()
- [ ] T021 [US3] Implement complementarity check: yes_price + no_price >= 1.00
- [ ] T022 [US3] Implement submit_with_stp() canceling conflicts, waiting 50ms, submitting
- [ ] T023 [US3] Add cancel endpoint DELETE /portfolio/orders/{id} to API client
- [ ] T024 [US3] Add place order endpoint POST /portfolio/orders to API client with STP
- [ ] T025 [US3] Add logging for STP blocks and cancellations

**Checkpoint**: STP operational - safe to place orders

---

## Phase 4: US2 - Risk Management (P1) SAFETY SECOND

**Goal**: Protect capital with limits and kill switch

**Independent Test**: Configure limits, simulate losses, verify kill switch activates

- [ ] T026 [P] [US2] Create Position model in src/models/position.py
- [ ] T027 [P] [US2] Create Market model in src/models/market.py
- [ ] T028 [US2] Implement PositionTracker in src/risk/position_tracker.py
- [ ] T029 [US2] Add GET /portfolio/balance to API client (use 'balance' not 'balance_total')
- [ ] T030 [US2] Add GET /portfolio/positions to API client
- [ ] T031 [US2] Implement RiskMonitor in src/risk/monitor.py with check_order_risk()
- [ ] T032 [US2] Add daily P&L tracking to RiskMonitor
- [ ] T033 [US2] Implement kill switch: cancel all, close WebSocket, log, exit
- [ ] T034 [US2] Add limit checks: exposure, inventory, loss
- [ ] T035 [US2] Add error rate monitoring
- [ ] T036 [US2] Add consecutive loss tracking
- [ ] T037 [US2] Integrate RiskMonitor into order submission

**Checkpoint**: Risk management operational

---

## Phase 5: US4 - Real-Time Order Book (P2)

**Goal**: Accurate market data via WebSocket + REST snapshots

**Independent Test**: Subscribe to market, verify delta updates, confirm snapshot syncs

- [ ] T038 [P] [US4] Create OrderBook model in src/models/order.py
- [ ] T039 [P] [US4] Create PriceLevel dataclass in src/models/order.py
- [ ] T040 [US4] Implement apply_delta() in OrderBook
- [ ] T041 [US4] Add sequence validation with gap detection
- [ ] T042 [US4] Implement WebSocketManager in src/api/websocket.py
- [ ] T043 [US4] Add WebSocket authentication
- [ ] T044 [US4] Implement orderbook_delta subscription
- [ ] T045 [US4] Add WebSocket message processing loop
- [ ] T046 [US4] Implement auto-reconnect with exponential backoff
- [ ] T047 [US4] Add heartbeat monitoring every 30s
- [ ] T048 [US4] Add GET /markets/{ticker}/orderbook to API client
- [ ] T049 [US4] Implement OrderBookManager in src/data/orderbook_manager.py
- [ ] T050 [US4] Add periodic snapshot sync every 30s
- [ ] T051 [US4] Add staleness detection (60s threshold)
- [ ] T052 [US4] Implement get_mid_price()

**Checkpoint**: OrderBook operational

---

## Phase 6: US5 - Rate Limiting (P2)

**Goal**: Prevent IP bans with token bucket

**Independent Test**: Submit burst requests, verify queuing without limit violations

- [ ] T053 [US5] Create read/write buckets (write 10/s cap 15, read 20/s cap 30)
- [ ] T054 [US5] Integrate write limiter into POST/DELETE
- [ ] T055 [US5] Integrate read limiter into GET
- [ ] T056 [US5] Add limiter metrics tracking
- [ ] T057 [US5] Add timeout handling

**Checkpoint**: Rate limiting operational

---

## Phase 7: US1 - Pure Market Making (P1) CORE VALUE

**Goal**: Provide liquidity, capture spreads

**Independent Test**: Configure bot, verify balanced orders, check spread capture

- [ ] T058 [P] [US1] Create Strategy interface in src/strategies/base.py
- [ ] T059 [US1] Implement PureMarketMakingStrategy in src/strategies/pure_mm.py
- [ ] T060 [US1] Add spread calculation (base/min/max)
- [ ] T061 [US1] Implement inventory skew adjustment
- [ ] T062 [US1] Add calculate_bid_ask()
- [ ] T063 [US1] Implement OrderManager in src/execution/order_manager.py
- [ ] T064 [US1] Add place_order() with STP and risk checks
- [ ] T065 [US1] Add cancel_all_orders()
- [ ] T066 [US1] Implement quote refresh (10s interval)
- [ ] T067 [US1] Add fill monitoring GET /portfolio/fills
- [ ] T068 [US1] Implement process_fill() updating P&L
- [ ] T069 [US1] Add fee calculation (-0.5% maker, +0.7% taker)
- [ ] T070 [US1] Add round-trip detection
- [ ] T071 [US1] Implement order refresh logic
- [ ] T072 [US1] Add quote_both_sides

**Checkpoint**: Market making operational

---

## Phase 8: US6 - Dynamic Spreads (P3)

**Goal**: Adapt spreads to inventory/volatility

- [ ] T073 [P] [US6] Add volatility tracking to OrderBookManager
- [ ] T074 [P] [US6] Add get_volatility()
- [ ] T075 [US6] Apply inventory_multiplier to spreads
- [ ] T076 [US6] Apply volatility_multiplier
- [ ] T077 [US6] Implement spread clamping
- [ ] T078 [US6] Add spread logging

---

## Phase 9: US7 - Market Selection (P3)

**Goal**: Auto-discover profitable markets

- [ ] T079 [P] [US7] Add GET /markets to API client
- [ ] T080 [US7] Implement fetch_all_markets() with pagination
- [ ] T081 [US7] Implement MarketDiscovery in src/data/market_discovery.py
- [ ] T082 [US7] Add volume filter
- [ ] T083 [US7] Add category filter
- [ ] T084 [US7] Add spread filter
- [ ] T085 [US7] Add status filter
- [ ] T086 [US7] Implement subscribe_to_markets()
- [ ] T087 [US7] Add periodic discovery refresh (5min)

---

## Phase 10: US8 - Monitoring (P3)

**Goal**: Visibility via logging and alerts

- [ ] T088 [P] [US8] Implement AlertDispatcher in src/utils/alerts.py
- [ ] T089 [P] [US8] Add Slack integration
- [ ] T090 [P] [US8] Add email integration
- [ ] T091 [P] [US8] Add terminal alerts
- [ ] T092 [US8] Integrate alerts into RiskMonitor
- [ ] T093 [US8] Add alert triggers
- [ ] T094 [US8] Implement P&L summary logging
- [ ] T095 [US8] Add fill rate tracking
- [ ] T096 [US8] Add maker ratio tracking
- [ ] T097 [US8] Add exposure tracking
- [ ] T098 [US8] Implement log rotation (30 days)
- [ ] T099 [US8] Add structured logging

---

## Phase 11: Main Entry Point

- [ ] T100 Create src/main.py with async main()
- [ ] T101 Add argument parsing: --config, --dry-run
- [ ] T102 Implement initialization sequence
- [ ] T103 Add startup validation
- [ ] T104 Query existing orders, populate STP cache
- [ ] T105 Implement main loop with asyncio.gather()
- [ ] T106 Add graceful shutdown
- [ ] T107 Implement dry-run mode
- [ ] T108 Add periodic tasks
- [ ] T109 Add startup banner

**Checkpoint**: Application runnable

---

## Phase 12: Polish

- [ ] T110 [P] Create tests/conftest.py
- [ ] T111 [P] Unit tests for PriceAdapter
- [ ] T112 [P] Unit tests for TokenBucket
- [ ] T113 [P] Unit tests for STP
- [ ] T114 [P] Integration test for orderbook
- [ ] T115 [P] End-to-end test
- [ ] T116 [P] Update README.md
- [ ] T117 [P] Create systemd service template
- [ ] T118 Code review
- [ ] T119 Performance profiling
- [ ] T120 Security audit
- [ ] T121 Validate quickstart.md

---

## Summary

**Total**: 121 tasks
**MVP**: 84 tasks (Phases 1-7 + 11)
**Parallel**: 29 tasks (24%)
**User Stories**: 8 (US1-US8)

**MVP Critical Path**: Setup → Foundational → US3 (STP) → US2 (Risk) → US4 (OrderBook) → US5 (RateLimit) → US1 (MarketMaking) → Main

**Rationale for US3 First**: Self-trade prevention is MANDATORY for compliance before ANY trading. US3 must be complete before US1 (market making) can begin.

**Independent Stories**: US4, US5, US7, US8 can run in parallel after Foundational

**Format Validation**: All 121 tasks follow `- [ ] [ID] [P?] [Story?] Description with path`
