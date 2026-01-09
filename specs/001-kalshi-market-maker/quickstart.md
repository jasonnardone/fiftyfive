# FiftyFive Quickstart Guide

**Get your Kalshi market maker bot running in 15 minutes**

---

## Prerequisites

Before starting, ensure you have:
- **Kalshi Account**: Verified account with API access enabled
- **Capital**: Minimum $500 deposited and settled
- **API Keys**: Generated RSA key pair and registered with Kalshi
- **Environment**: Windows with WSL2 Ubuntu 22.04 OR native Linux
- **Python**: Version 3.10 or higher
- **Git**: For cloning repository

---

## Step 1: Kalshi Account Setup (5 minutes)

### 1.1 Create Account
1. Go to https://kalshi.com
2. Sign up with email/password
3. Complete KYC verification (upload ID)
4. Wait for approval (usually <24 hours)

### 1.2 Generate API Keys
1. Log in to Kalshi dashboard
2. Navigate to Settings → API Keys
3. Click "Generate New Key"
4. Download the JSON file containing `api_key_id` and `private_key`
5. **IMPORTANT**: Store this file securely - you cannot retrieve it again

### 1.3 Fund Account
1. Link bank account or debit card
2. Deposit at least $500 (recommended starting capital)
3. Wait for funds to settle (1-3 business days)

---

## Step 2: Environment Setup (5 minutes)

### 2.1 Install WSL2 (Windows only)
```bash
# PowerShell as Administrator
wsl --install -d Ubuntu-22.04

# Update packages
sudo apt update && sudo apt upgrade -y
```

### 2.2 Install Python 3.10+
```bash
# Check version
python3 --version

# If < 3.10, install:
sudo apt install python3.10 python3.10-venv python3-pip -y
```

### 2.3 Clone Repository
```bash
mkdir ~/fiftyfive
cd ~/fiftyfive
git clone https://github.com/yourusername/fiftyfive.git .
```

---

## Step 3: Configure Bot (5 minutes)

### 3.1 Install Dependencies
```bash
# Create virtual environment
python3 -m venv venv

# Activate
source venv/bin/activate

# Install packages
pip install -r requirements.txt
```

### 3.2 Save API Credentials
```bash
# Create credentials directory
mkdir -p ~/.kalshi

# Save private key (paste content from Kalshi JSON download)
nano ~/.kalshi/private_key.pem
# Ctrl+X, Y, Enter to save

# Secure the file
chmod 600 ~/.kalshi/private_key.pem
```

### 3.3 Create Environment File
```bash
# Copy example
cp .env.example .env

# Edit with your credentials
nano .env
```

Add your credentials:
```bash
# Kalshi API Credentials
KALSHI_API_KEY_ID="your-api-key-uuid-here"
KALSHI_PRIVATE_KEY_PATH="/home/yourusername/.kalshi/private_key.pem"

# Environment (start with demo!)
ENVIRONMENT="demo"
```

### 3.4 Configure Risk Limits
```bash
# Edit demo config
nano config/demo.yaml
```

**Conservative starting settings:**
```yaml
risk:
  max_exposure_per_market: 100.00   # $100 per market
  max_total_exposure: 500.00        # $500 total
  daily_loss_limit: 50.00           # Stop after $50 loss
  max_contracts_per_side: 10        # Max 10 contracts

strategy:
  name: pure_market_making
  
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

## Step 4: First Run (Demo Mode)

### 4.1 Activate Virtual Environment
```bash
cd ~/fiftyfive
source venv/bin/activate
```

### 4.2 Run in Dry-Run Mode (Test Without Trading)
```bash
python src/main.py --config config/demo.yaml --dry-run
```

**Expected output:**
```
[INFO] FiftyFive v1.0.0 starting...
[INFO] Environment: demo
[INFO] Dry-run mode: ON (no real orders)
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
[DRY-RUN] Would place order: KXHARRIS24 buy 5@0.53
[DRY-RUN] Would place order: KXHARRIS24 sell 5@0.57
```

### 4.3 Monitor for 10 Minutes
Let the bot run and observe:
- Orders being simulated (dry-run)
- Order book updates
- Market discovery
- No errors in logs

### 4.4 Check Logs
```bash
tail -f logs/fiftyfive_*.log
```

---

## Step 5: Enable Live Demo Trading

### 5.1 Remove Dry-Run Flag
```bash
# Edit .env to use demo environment
nano .env
```

Set:
```bash
ENVIRONMENT="demo"
```

### 5.2 Run With Real Demo Orders
```bash
python src/main.py --config config/demo.yaml
```

**You should see:**
```
[INFO] Dry-run mode: OFF
[OK] Order placed: KXHARRIS24 buy 5@0.53 (order_id: abc123)
[OK] Order placed: KXHARRIS24 sell 5@0.57 (order_id: def456)
```

### 5.3 Monitor for 1 Hour
Check for:
- Orders getting filled
- P&L updates
- Spread capture
- No kill switch triggers

### 5.4 Verify Demo Results
```bash
# Check fills
cat logs/fiftyfive_*.log | grep "Fill"

# Check P&L
cat logs/fiftyfive_*.log | grep "P&L"
```

---

## Step 6: Production (After 24 Hours Demo Success)

### 6.1 Switch to Production
```bash
nano .env
```

Change:
```bash
ENVIRONMENT="production"
```

### 6.2 Update Production Config
```bash
nano config/production.yaml
```

Keep conservative limits initially:
```yaml
risk:
  max_exposure_per_market: 100.00
  max_total_exposure: 500.00
  daily_loss_limit: 50.00
```

### 6.3 Run Production
```bash
python src/main.py --config config/production.yaml
```

---

## Step 7: Background Service (24/7 Operation)

### 7.1 Create Systemd Service
```bash
sudo nano /etc/systemd/system/fiftyfive.service
```

Content:
```ini
[Unit]
Description=FiftyFive Kalshi Market Maker
After=network.target

[Service]
Type=simple
User=yourusername
WorkingDirectory=/home/yourusername/fiftyfive
Environment="PATH=/home/yourusername/fiftyfive/venv/bin"
ExecStart=/home/yourusername/fiftyfive/venv/bin/python src/main.py --config config/production.yaml
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 7.2 Enable and Start
```bash
sudo systemctl enable fiftyfive
sudo systemctl start fiftyfive

# Check status
sudo systemctl status fiftyfive

# View logs
journalctl -u fiftyfive -f
```

---

## Troubleshooting

### "Authentication failed"
- Verify `KALSHI_API_KEY_ID` is correct
- Check `private_key.pem` file exists and has correct path
- Ensure private key file permissions are 600

### "Rate limit exceeded"
- Reduce `order_refresh_interval` in config
- Check `rate_limits.write_rps` and `read_rps` settings
- Wait 60 seconds and retry

### "WebSocket disconnected"
- Check internet connection
- Verify Kalshi exchange is not in maintenance
- Bot will auto-reconnect with exponential backoff

### "Orders not filling"
- Check if spreads are too wide (tighten `base_spread`)
- Verify markets have sufficient liquidity
- Compare your quotes to current order book

---

## Daily Monitoring Checklist

**Morning (before trading):**
- [ ] Check logs for overnight errors
- [ ] Verify WebSocket connection
- [ ] Review yesterday's P&L
- [ ] Confirm API rate tier hasn't changed

**During Trading:**
- [ ] Monitor P&L every hour
- [ ] Check fill rate (should be >50%)
- [ ] Watch for stuck orders (>10 min unfilled)
- [ ] Verify spreads are competitive

**Evening (after trading):**
- [ ] Review daily P&L
- [ ] Analyze best/worst markets
- [ ] Check overnight positions
- [ ] Archive logs

---

## Next Steps

Once comfortable with basic operation:
1. Gradually increase exposure limits
2. Add more markets (sports → economics → politics)
3. Experiment with spread adjustments
4. Consider informed market making strategy
5. Optimize based on performance data

---

## Support

- **Documentation**: See `specs/001-kalshi-market-maker/` for technical details
- **Issues**: https://github.com/yourusername/fiftyfive/issues
- **Kalshi API Docs**: https://docs.kalshi.com
- **Kalshi Discord**: #dev channel for developer support

**Happy Trading! 🚀**
