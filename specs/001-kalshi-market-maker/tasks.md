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

- [x] T001 Create project directory structure: src/, config/, tests/, logs/
- [x] T002 Initialize Python 3.10+ virtual environment and install dependencies
- [x] T003 [P] Create .env.example with KALSHI_API_KEY_ID, KALSHI_PRIVATE_KEY_PATH, ENVIRONMENT
- [x] T004 [P] Create .gitignore excluding .env, logs/, venv/, __pycache__/
- [x] T005 [P] Create README.md with project overview
- [x] T006 [P] Create requirements.txt: aiohttp, websockets, cryptography, pyyaml, pydantic, python-dotenv, orjson, loguru, pytest, pytest-asyncio

---

## Phase 2: Foundational (CRITICAL - Blocks All User Stories)

**Purpose**: Core infrastructure required before ANY user story

- [x] T007 [P] Create src/__init__.py
- [x] T008 [P] Define base enums (OrderSide, OrderAction, OrderStatus, MarketStatus) in src/models/order.py
- [x] T009 [P] Implement PriceAdapter in src/api/price_adapter.py with to_api_price(), from_api_price()
- [x] T010 [P] Implement TokenBucket in src/utils/rate_limiter.py with async acquire()
- [x] T011 [P] Setup logger in src/utils/logger.py with daily rotation and structured format
- [x] T012 [P] Create config schema models in src/models/config.py (Config, RiskConfig, StrategyConfig)
- [x] T013 Implement ConfigLoader in src/config/loader.py with YAML parsing, Pydantic validation
- [x] T014 [P] Create config/production.example.yaml and config/demo.yaml
- [x] T015 [P] Implement RSA-PSS auth in src/api/auth.py with sign_request()
- [x] T016 Create REST API client in src/api/client.py with aiohttp, connection pooling, rate limiting

**Checkpoint**: Foundation ready for user stories

---

## Phase 3: US3 - Self-Trade Prevention (P1) SAFETY FIRST

**Goal**: Prevent wash trading violations - MANDATORY before any trading

**Independent Test**: Submit crossing orders, verify STP cancels conflicting first, waits 50ms, then submits

- [x] T017 [P] [US3] Create Order model in src/models/order.py
- [x] T018 [P] [US3] Create Fill model in src/models/order.py
- [x] T019 [US3] Implement STP engine in src/execution/stp_engine.py with can_submit_order()
- [x] T020 [US3] Add order cache to STP: add_order(), remove_order(), update_on_fill()
- [x] T021 [US3] Implement complementarity check: yes_price + no_price >= 1.00
- [x] T022 [US3] Implement submit_with_stp() canceling conflicts, waiting 50ms, submitting
- [x] T023 [US3] Add cancel endpoint DELETE /portfolio/orders/{id} to API client
- [x] T024 [US3] Add place order endpoint POST /portfolio/orders to API client with STP
- [x] T025 [US3] Add logging for STP blocks and cancellations

**Checkpoint**: STP operational - safe to place orders

---

## Phase 4: US2 - Risk Management (P1) SAFETY SECOND

**Goal**: Protect capital with limits and kill switch

**Independent Test**: Configure limits, simulate losses, verify kill switch activates

- [x] T026 [P] [US2] Create Position model in src/models/position.py
- [x] T027 [P] [US2] Create Market model in src/models/market.py
- [x] T028 [US2] Implement PositionTracker in src/risk/position_tracker.py
- [x] T029 [US2] Add GET /portfolio/balance to API client (use 'balance' not 'balance_total')
- [x] T030 [US2] Add GET /portfolio/positions to API client
- [x] T031 [US2] Implement RiskMonitor in src/risk/monitor.py with check_order_risk()
- [x] T032 [US2] Add daily P&L tracking to RiskMonitor
- [x] T033 [US2] Implement kill switch: cancel all, close WebSocket, log, exit
- [x] T034 [US2] Add limit checks: exposure, inventory, loss
- [x] T035 [US2] Add error rate monitoring
- [x] T036 [US2] Add consecutive loss tracking
- [x] T037 [US2] Integrate RiskMonitor into order submission

**Checkpoint**: Risk management operational

---

## Phase 5: US4 - Real-Time Order Book (P2)

**Goal**: Accurate market data via WebSocket + REST snapshots

**Independent Test**: Subscribe to market, verify delta updates, confirm snapshot syncs

- [x] T038 [P] [US4] Create OrderBook model in src/models/order.py
- [x] T039 [P] [US4] Create PriceLevel dataclass in src/models/order.py
- [x] T040 [US4] Implement apply_delta() in OrderBook
- [x] T041 [US4] Add sequence validation with gap detection
- [x] T042 [US4] Implement WebSocketManager in src/api/websocket.py
- [x] T043 [US4] Add WebSocket authentication
- [x] T044 [US4] Implement orderbook_delta subscription
- [x] T045 [US4] Add WebSocket message processing loop
- [x] T046 [US4] Implement auto-reconnect with exponential backoff
- [x] T047 [US4] Add heartbeat monitoring every 30s
- [x] T048 [US4] Add GET /markets/{ticker}/orderbook to API client
- [x] T049 [US4] Implement OrderBookManager in src/data/orderbook_manager.py
- [x] T050 [US4] Add periodic snapshot sync every 30s
- [x] T051 [US4] Add staleness detection (60s threshold)
- [x] T052 [US4] Implement get_mid_price()

**Checkpoint**: OrderBook operational

---

## Phase 6: US5 - Rate Limiting (P2)

**Goal**: Prevent IP bans with token bucket

**Independent Test**: Submit burst requests, verify queuing without limit violations

- [x] T053 [US5] Create read/write buckets (write 10/s cap 15, read 20/s cap 30)
- [x] T054 [US5] Integrate write limiter into POST/DELETE
- [x] T055 [US5] Integrate read limiter into GET
- [x] T056 [US5] Add limiter metrics tracking
- [x] T057 [US5] Add timeout handling

**Checkpoint**: Rate limiting operational

---

## Phase 7: US1 - Pure Market Making (P1) CORE VALUE

**Goal**: Provide liquidity, capture spreads

**Independent Test**: Configure bot, verify balanced orders, check spread capture

- [x] T058 [P] [US1] Create Strategy interface in src/strategies/base.py
- [x] T059 [US1] Implement PureMarketMakingStrategy in src/strategies/pure_mm.py
- [x] T060 [US1] Add spread calculation (base/min/max)
- [x] T061 [US1] Implement inventory skew adjustment
- [x] T062 [US1] Add calculate_bid_ask()
- [x] T063 [US1] Implement OrderManager in src/execution/order_manager.py
- [x] T064 [US1] Add place_order() with STP and risk checks
- [x] T065 [US1] Add cancel_all_orders()
- [x] T066 [US1] Implement quote refresh (10s interval)
- [x] T067 [US1] Add fill monitoring GET /portfolio/fills
- [x] T068 [US1] Implement process_fill() updating P&L
- [x] T069 [US1] Add fee calculation (-0.5% maker, +0.7% taker)
- [x] T070 [US1] Add round-trip detection
- [x] T071 [US1] Implement order refresh logic
- [x] T072 [US1] Add quote_both_sides

**Checkpoint**: Market making operational

---

## Phase 8: US6 - Dynamic Spreads (P3)

**Goal**: Adapt spreads to inventory/volatility

- [x] T073 [P] [US6] Add volatility tracking to OrderBookManager
- [x] T074 [P] [US6] Add get_volatility()
- [x] T075 [US6] Apply inventory_multiplier to spreads
- [x] T076 [US6] Apply volatility_multiplier
- [x] T077 [US6] Implement spread clamping
- [x] T078 [US6] Add spread logging

---

## Phase 9: US7 - Market Selection (P3)

**Goal**: Auto-discover profitable markets

- [x] T079 [P] [US7] Add GET /markets to API client
- [x] T080 [US7] Implement fetch_all_markets() with pagination
- [x] T081 [US7] Implement MarketDiscovery in src/data/market_discovery.py
- [x] T082 [US7] Add volume filter
- [x] T083 [US7] Add category filter
- [x] T084 [US7] Add spread filter
- [x] T085 [US7] Add status filter
- [x] T086 [US7] Implement subscribe_to_markets()
- [x] T087 [US7] Add periodic discovery refresh (5min)

---

## Phase 10: US8 - Monitoring (P3)

**Goal**: Visibility via logging and alerts

- [x] T088 [P] [US8] Implement AlertDispatcher in src/utils/alerts.py
- [ ] T089 [P] [US8] Add Slack integration
- [ ] T090 [P] [US8] Add email integration
- [x] T091 [P] [US8] Add terminal alerts
- [x] T092 [US8] Integrate alerts into RiskMonitor
- [x] T093 [US8] Add alert triggers
- [x] T094 [US8] Implement P&L summary logging
- [x] T095 [US8] Add fill rate tracking
- [x] T096 [US8] Add maker ratio tracking
- [x] T097 [US8] Add exposure tracking
- [ ] T098 [US8] Implement log rotation (30 days)
- [ ] T099 [US8] Add structured logging

---

## Phase 11: Main Entry Point

- [x] T100 Create src/main.py with async main()
- [x] T101 Add argument parsing: --config, --dry-run
- [x] T102 Implement initialization sequence
- [x] T103 Add startup validation
- [x] T104 Query existing orders, populate STP cache
- [x] T105 Implement main loop with asyncio.gather()
- [x] T106 Add graceful shutdown
- [x] T107 Implement dry-run mode
- [x] T108 Add periodic tasks
- [x] T109 Add startup banner

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
