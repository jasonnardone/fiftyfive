"""Test configuration loading"""

import sys
sys.path.insert(0, '.')

import os
from src.config.loader import load_config

def test_config_load():
    """Test that demo.yaml loads correctly"""
    print("\n=== Testing Configuration Loading ===\n")

    try:
        # Load config using the built-in loader
        config = load_config("config/demo.yaml")

        print("[OK] Configuration loaded successfully!")
        print(f"\n  Environment: {config.environment}")
        print(f"  API Base URL: {config.exchange.api_base_url}")
        print(f"  WebSocket URL: {config.exchange.ws_url}")
        print(f"  API Key ID: {config.exchange.api_key_id[:20]}...")
        print(f"  Private Key Path: {config.exchange.private_key_path}")
        print(f"\n  Dry Run Mode: {config.advanced.dry_run}")
        print(f"  Max Exposure/Market: ${config.risk.max_exposure_per_market:.2f}")
        print(f"  Max Total Exposure: ${config.risk.max_total_exposure:.2f}")
        print(f"  Daily Loss Limit: ${config.risk.daily_loss_limit:.2f}")
        print(f"\n  Strategy: {config.strategy.name}")
        print(f"  Base Spread: {config.strategy.pricing.base_spread}")
        print(f"  Order Size: {config.strategy.order_sizing.base_size}")
        print(f"  STP Enabled: {config.execution.stp_enabled}")

        # Check private key file exists
        import os
        if os.path.exists(config.exchange.private_key_path):
            print(f"\n[OK] Private key file found")
        else:
            print(f"\n[ERROR] Private key file not found: {config.exchange.private_key_path}")
            return False

        print("\n[OK] All configuration checks passed!")
        return True

    except Exception as e:
        print(f"\n[ERROR] Configuration loading failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_config_load()
    sys.exit(0 if success else 1)
