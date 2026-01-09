# FiftyFive - Kalshi Market Maker Bot

**Automated market-making bot for Kalshi prediction markets**

## Overview

FiftyFive is a Python-based automated trading bot that provides liquidity on Kalshi prediction markets through market-making strategies. The bot monitors real-time order books via WebSocket, calculates optimal bid-ask spreads, and manages risk through configurable limits and a kill switch.

## Features

- **Pure Market Making**: Provide liquidity by quoting both sides of the market
- **Self-Trade Prevention**: Mandatory compliance to prevent wash trading violations
- **Risk Management**: Daily loss limits, exposure caps, and automatic kill switch
- **Real-Time Data**: WebSocket streaming with REST API snapshots
- **Rate Limiting**: Token bucket algorithm enforcing Kalshi API limits
- **Multi-Market Support**: Concurrent operation across multiple markets
- **Configuration-Driven**: YAML configuration with Pydantic validation

## Quick Start

See [quickstart.md](specs/001-kalshi-market-maker/quickstart.md) for detailed setup instructions.

### Prerequisites

- Python 3.10+
- Kalshi account with API access
- Minimum $500 deposited capital

### Installation

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure credentials
cp .env.example .env
nano .env  # Add your Kalshi API credentials
```

### Run Demo Mode

```bash
# Dry-run (no real orders)
python src/main.py --config config/demo.yaml --dry-run

# Live demo trading
python src/main.py --config config/demo.yaml
```

## Project Structure

```
fiftyfive/
├── src/
│   ├── api/          # Kalshi API client, auth, websocket
│   ├── models/       # Data models (Order, Position, Config)
│   ├── strategies/   # Trading strategies (Pure MM, Informed MM)
│   ├── execution/    # Order execution, STP engine
│   ├── risk/         # Risk monitor, position tracker
│   ├── data/         # Order book manager, market discovery
│   ├── utils/        # Rate limiter, logger, alerts
│   └── main.py       # Entry point
├── config/           # YAML configuration files
├── tests/            # Unit, integration, contract tests
├── logs/             # Application logs
└── specs/            # Design documents and specifications
```

## Configuration

Edit `config/demo.yaml` or `config/production.yaml`:

```yaml
risk:
  max_exposure_per_market: 100.00
  max_total_exposure: 500.00
  daily_loss_limit: 50.00

strategy:
  name: pure_market_making
  pricing:
    base_spread: 0.04
  order_sizing:
    base_size: 5
```

## Safety Features

- **Self-Trade Prevention (STP)**: Automatically cancels conflicting orders before submission
- **Risk Kill Switch**: Stops trading on daily loss limit, error rate threshold, or consecutive losses
- **Rate Limiting**: Prevents API bans with token bucket algorithm
- **Configuration Validation**: Pydantic schemas ensure valid settings

## Documentation

- [Feature Specification](specs/001-kalshi-market-maker/spec.md)
- [Implementation Plan](specs/001-kalshi-market-maker/plan.md)
- [Data Model](specs/001-kalshi-market-maker/data-model.md)
- [API Contracts](specs/001-kalshi-market-maker/contracts/)
- [Task List](specs/001-kalshi-market-maker/tasks.md)

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/unit/test_stp_engine.py
```

## Monitoring

Logs are written to `logs/fiftyfive_YYYY-MM-DD.log` with daily rotation.

```bash
# Tail logs
tail -f logs/fiftyfive_*.log

# Check P&L
cat logs/fiftyfive_*.log | grep "P&L"

# Check fills
cat logs/fiftyfive_*.log | grep "Fill"
```

## Support

- **Issues**: https://github.com/yourusername/fiftyfive/issues
- **Kalshi API Docs**: https://docs.kalshi.com
- **Kalshi Discord**: #dev channel

## License

MIT License - See LICENSE file for details

## Disclaimer

This software is for educational purposes only. Trading involves risk of loss. Use at your own risk.
