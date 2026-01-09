"""Test individual components"""

import asyncio
import sys
sys.path.insert(0, '.')

from src.models.order import Order, OrderSide, OrderAction, OrderStatus, OrderBook, PriceLevel
from src.api.price_adapter import PriceAdapter
from src.utils.rate_limiter import TokenBucket
from src.execution.stp_engine import STPEngine
from src.risk.position_tracker import PositionTracker
from src.models.config import RiskConfig


def test_price_adapter():
    """Test price adapter"""
    print("\n=== Testing PriceAdapter ===")

    # Test conversion
    cents = PriceAdapter.to_api_price(0.50)
    assert cents == 50, f"Expected 50, got {cents}"
    print(f"[OK] 0.50 -> {cents} cents")

    dollars = PriceAdapter.from_api_price(75)
    assert dollars == 0.75, f"Expected 0.75, got {dollars}"
    print(f"[OK] 75 cents -> {dollars}")

    # Test complementarity
    valid = PriceAdapter.validate_complementarity(0.55, 0.50)
    assert valid, "0.55 + 0.50 should be >= 1.00"
    print(f"[OK] Complementarity: 0.55 + 0.50 = {0.55 + 0.50:.2f} (valid)")

    print("[OK] PriceAdapter tests passed!")


async def test_token_bucket():
    """Test token bucket rate limiter"""
    print("\n=== Testing TokenBucket ===")

    bucket = TokenBucket(rate=10.0, capacity=15)

    # Acquire tokens
    acquired = await bucket.acquire(tokens=5, timeout=1.0)
    assert acquired, "Should acquire tokens"
    print(f"[OK] Acquired 5 tokens, available: {bucket.available_tokens:.1f}")

    # Try to acquire more than capacity
    try:
        await bucket.acquire(tokens=20, timeout=0.1)
        assert False, "Should not acquire more than capacity"
    except ValueError:
        print("[OK] Correctly rejected tokens > capacity")

    print("[OK] TokenBucket tests passed!")


async def test_stp_engine():
    """Test self-trade prevention"""
    print("\n=== Testing STPEngine ===")

    stp = STPEngine(cancel_delay=0.01)

    # Create test order
    order1 = Order(
        order_id="order1",
        market_ticker="TEST",
        side=OrderSide.YES,
        action=OrderAction.BUY,
        price=0.50,
        quantity=10,
        status=OrderStatus.OPEN
    )

    await stp.add_order(order1)
    print(f"[OK] Added order to STP cache")

    # Check for conflict (same side, same action = no conflict)
    order2 = Order(
        order_id="order2",
        market_ticker="TEST",
        side=OrderSide.YES,
        action=OrderAction.BUY,
        price=0.51,
        quantity=10
    )

    can_submit, conflicts = await stp.can_submit_order(order2)
    assert can_submit, "Same side/action should not conflict"
    print(f"[OK] No conflict detected for same side/action")

    # Check for conflict (opposite action = conflict if prices cross)
    order3 = Order(
        order_id="order3",
        market_ticker="TEST",
        side=OrderSide.YES,
        action=OrderAction.SELL,
        price=0.48,  # Sell at 0.48, existing buy at 0.50 = would cross
        quantity=10
    )

    can_submit, conflicts = await stp.can_submit_order(order3)
    print(f"DEBUG: can_submit={can_submit}, conflicts={len(conflicts)}")
    if conflicts:
        for c in conflicts:
            print(f"  Conflict: {c.action.value} @ {c.price}")
    assert not can_submit, f"Crossing orders should conflict (got can_submit={can_submit})"
    assert len(conflicts) == 1, f"Should detect 1 conflict (got {len(conflicts)})"
    print(f"[OK] Conflict detected for crossing orders")

    print("[OK] STPEngine tests passed!")


def test_order_book():
    """Test order book"""
    print("\n=== Testing OrderBook ===")

    orderbook = OrderBook(
        market_ticker="TEST",
        yes_bids=[],
        no_bids=[],
        yes_asks=[],
        no_asks=[]
    )

    # Apply delta
    deltas = [[50, 100], [51, 50]]  # price_cents, quantity
    orderbook.apply_delta(OrderSide.YES, 'bid', deltas)

    assert len(orderbook.yes_bids) == 2, "Should have 2 bid levels"
    assert orderbook.yes_bids[0].price == 51, "Best bid should be 51"
    print(f"[OK] Applied delta, best bid: {orderbook.yes_bids[0].price} cents")

    # Get best bid
    best_bid = orderbook.get_best_bid(OrderSide.YES)
    assert best_bid.price == 51, "Best bid should be 51"
    print(f"[OK] Best bid: {best_bid.price} cents x {best_bid.quantity}")

    print("[OK] OrderBook tests passed!")


def test_position_tracker():
    """Test position tracking"""
    print("\n=== Testing PositionTracker ===")

    from src.models.order import Fill
    from datetime import datetime

    tracker = PositionTracker()

    # Create fill
    fill = Fill(
        fill_id="fill1",
        order_id="order1",
        market_ticker="TEST",
        side=OrderSide.YES,
        action=OrderAction.BUY,
        price=0.50,
        quantity=10,
        maker_fee=-0.025,  # -0.5% rebate
        taker_fee=0.0
    )

    tracker.update_from_fill(fill)

    # Check position
    position = tracker.get_position("TEST", OrderSide.YES)
    assert position.quantity == 10, "Position should be 10"
    assert position.average_price == 0.50, "Average price should be 0.50"
    print(f"[OK] Position: {position.quantity} @ ${position.average_price:.2f}")
    print(f"[OK] Realized P&L: ${position.realized_pnl:.2f}")

    # Check exposure
    exposure = tracker.get_market_exposure("TEST")
    print(f"[OK] Market exposure: ${exposure:.2f}")

    print("[OK] PositionTracker tests passed!")


async def main():
    """Run all tests"""
    print("=" * 60)
    print("FiftyFive Component Tests")
    print("=" * 60)

    try:
        # Sync tests
        test_price_adapter()
        test_order_book()
        test_position_tracker()

        # Async tests
        await test_token_bucket()
        await test_stp_engine()

        print("\n" + "=" * 60)
        print("[OK] ALL TESTS PASSED!")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n[FAIL] TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[FAIL] ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
