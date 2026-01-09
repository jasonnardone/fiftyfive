<!--
SYNC IMPACT REPORT
==================
Version Change: Initial creation → 1.0.0
Modified Principles: N/A (initial version)
Added Sections:
  - Core Principles (7 principles)
  - Security & Compliance Requirements
  - Development & Operations Workflow
  - Governance
Removed Sections: N/A
Templates Status:
  ✅ .specify/templates/plan-template.md - reviewed, constitution check section aligns
  ✅ .specify/templates/spec-template.md - reviewed, requirements align with safety-first principle
  ✅ .specify/templates/tasks-template.md - reviewed, task categorization supports observability & testing
Follow-up TODOs: None
-->

# FiftyFive Constitution

## Core Principles

### I. Safety-First Architecture (NON-NEGOTIABLE)

Self-trade prevention (STP) MUST be enforced before every order submission. Wash trading will result in account termination by Kalshi. The bot MUST maintain a local cache of open orders and validate that new orders will not cross with existing positions. When conflicts are detected, conflicting orders MUST be cancelled with a minimum 50ms delay before submitting new orders. The STP engine MUST never be bypassed or disabled.

**Rationale**: Regulatory compliance is the foundation of operational viability. A single self-trade violation can result in permanent account ban, making this the highest-priority architectural constraint.

### II. Risk Management Controls (NON-NEGOTIABLE)

The bot MUST implement hard limits on positions, exposure, and losses with automated kill switches. Position limits MUST be enforced per-market and system-wide. A kill switch MUST trigger on: (a) daily loss limit breach, (b) error rate exceeding 10%, or (c) consecutive loss threshold. When triggered, the kill switch MUST immediately stop accepting orders, cancel all open orders, close WebSocket connections, log final state, and exit the process. Risk checks MUST be performed before every order submission.

**Rationale**: Automated trading systems can amplify losses exponentially. Circuit breakers are essential to prevent catastrophic capital loss and protect against system malfunctions.

### III. Rate Limiting & API Compliance (NON-NEGOTIABLE)

All API requests MUST be rate-limited using token bucket algorithm matching Kalshi tier limits (Basic: 10 writes/sec, 20 reads/sec). The bot MUST queue requests when bucket is empty rather than dropping them. IP bans resulting from rate limit violations are unacceptable. Rate limiters MUST be enforced for both REST API and order submission paths.

**Rationale**: Exchange rate limits are hard boundaries that trigger IP-level bans. Rate limiting must be proactive and defensive to ensure continuous operation.

### IV. Configuration-Driven Operation

All trading behavior MUST be controlled via YAML configuration files without code changes. Strategies, spreads, position limits, risk thresholds, and market filters MUST be externalized. The bot MUST support multiple environment configurations (demo, production) loaded via environment variables. Hot-reload capability is encouraged for non-critical parameters. Sensitive credentials MUST be stored in environment variables, never committed to version control.

**Rationale**: Traders need rapid iteration on strategy parameters without redeployment risk. Configuration externalization enables A/B testing, gradual rollouts, and emergency parameter adjustments.

### V. Observability & Monitoring (NON-NEGOTIABLE)

All critical operations MUST be logged with structured data (timestamp, level, component, action, outcome). The bot MUST track and expose metrics for: P&L (realized/unrealized), order placement rate, fill rate, maker/taker ratio, API error rate, WebSocket uptime, and order latency. Kill switch activations, STP blocks, and risk limit breaches MUST be logged at CRITICAL level. Daily P&L reports MUST be generated automatically.

**Rationale**: Algorithmic trading requires real-time operational visibility to detect anomalies, debug failures, and measure performance. Silent failures can compound into catastrophic losses.

### VI. Async Architecture & Low Latency

The bot MUST use asynchronous I/O (asyncio) to handle multiple markets concurrently without blocking. WebSocket connections for market data MUST run in parallel with REST API order submission and position monitoring. Target latency from signal to order placement is <50ms. Connection pooling, batch API calls, and optimistic order tracking MUST be employed. Synchronous blocking operations (file I/O, subprocess calls) are prohibited in the hot path.

**Rationale**: Market-making profitability depends on speed-to-quote and ability to react to market movements. Blocking operations create arbitrage opportunities for competitors and missed fills.

### VII. Data Integrity & Resilience

WebSocket order book state MUST be validated with periodic REST snapshots (max 30-second staleness). Sequence gaps in WebSocket deltas MUST trigger immediate resynchronization. Order fill monitoring MUST poll at minimum 1-second intervals. Position and balance state MUST be reconciled with exchange data before daily trading begins. Auto-reconnect logic MUST handle WebSocket disconnections with exponential backoff (max 10 attempts).

**Rationale**: Stale or incorrect market data leads to mispriced quotes and adverse selection. Data consistency is required for accurate position tracking and P&L calculation.

## Security & Compliance Requirements

**Authentication**: RSA-PSS signature-based authentication MUST be used per Kalshi API v2 specification. Private keys MUST be stored with 600 file permissions. API key IDs MUST be loaded from environment variables.

**Price Normalization**: Internal calculations MUST use float representation (0.00-1.00). API communication MUST convert to integer cents (1-99). A dedicated PriceAdapter class MUST handle all conversions.

**Secrets Management**: The `.env` file containing credentials MUST be gitignored. Private key paths MUST be absolute and validated at startup. Production credentials MUST never be used in demo/testing environments.

**Market Compliance**: The bot MUST respect market open/close status. After-hours trading attempts MUST be gracefully handled. Position clearing delays MUST be accounted for (use `balance` field, not `balance_total`).

## Development & Operations Workflow

**Testing Requirements**: Demo mode testing MUST run for minimum 24 hours before production deployment. Dry-run mode MUST be supported to validate logic without placing real orders. Kill switch MUST be manually tested before production use.

**Deployment**: The bot MUST run as a systemd service with automatic restart on failure (max 10-second restart delay). Logs MUST rotate daily with 30-day retention. Health check endpoint MUST be exposed on port 8080.

**Configuration Progression**: Start with conservative limits ($100/market, $500 total, 5 contracts/order, 4-cent spreads). Only increase exposure after 7+ days of profitable demo trading. Production configuration MUST require explicit environment variable override.

**Monitoring Checklist**: Daily reviews MUST verify: overnight error logs, WebSocket connectivity, P&L vs. expectations, fill rates (>50% target), spread competitiveness, and stuck orders (>10min unfilled).

**Incident Response**: On kill switch activation: preserve logs, document trigger conditions, analyze P&L impact, identify root cause, adjust configuration, test in demo before restarting production.

## Governance

**Amendment Process**: Constitution changes MUST be documented with version number increment, rationale, and affected templates sync report. MAJOR version for principle removals/redefinitions, MINOR for new principles/sections, PATCH for clarifications.

**Compliance Enforcement**: All code reviews MUST verify adherence to safety-first (STP), risk management (kill switches), rate limiting, and observability principles. Violations MUST be justified in plan.md Complexity Tracking table with documented alternatives considered.

**Priority Hierarchy**: In case of conflicts, principles are ranked: Safety-First > Risk Management > Rate Limiting > Data Integrity > Observability > Configuration-Driven > Async Architecture.

**Version**: 1.0.0 | **Ratified**: 2026-01-08 | **Last Amended**: 2026-01-08
