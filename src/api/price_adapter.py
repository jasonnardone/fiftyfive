"""Price conversion utilities for Kalshi API

Kalshi API uses cents (1-99) for prices
Internal representation uses dollars (0.01-0.99)
"""


class PriceAdapter:
    """Converts between API cents and internal dollar prices"""

    @staticmethod
    def to_api_price(price: float) -> int:
        """Convert dollar price to API cents

        Args:
            price: Price in dollars [0.01-0.99]

        Returns:
            Price in cents [1-99]

        Raises:
            ValueError: If price is out of valid range
        """
        if not 0.01 <= price <= 0.99:
            raise ValueError(f"Price must be 0.01-0.99, got {price}")

        cents = round(price * 100)

        # Ensure within valid range
        if not 1 <= cents <= 99:
            raise ValueError(f"Converted price {cents} cents is out of range [1-99]")

        return cents

    @staticmethod
    def from_api_price(cents: int) -> float:
        """Convert API cents to dollar price

        Args:
            cents: Price in cents [1-99]

        Returns:
            Price in dollars [0.01-0.99]

        Raises:
            ValueError: If cents is out of valid range
        """
        if not 1 <= cents <= 99:
            raise ValueError(f"Cents must be 1-99, got {cents}")

        price = cents / 100.0

        # Ensure within valid range
        if not 0.01 <= price <= 0.99:
            raise ValueError(f"Converted price {price} is out of range [0.01-0.99]")

        return price

    @staticmethod
    def validate_complementarity(yes_price: float, no_price: float, tolerance: float = 0.001) -> bool:
        """Validate that YES + NO prices sum to at least 1.00

        This is a key invariant in prediction markets:
        yes_price + no_price >= 1.00

        Args:
            yes_price: YES price in dollars
            no_price: NO price in dollars
            tolerance: Floating point tolerance

        Returns:
            True if complementarity holds
        """
        return (yes_price + no_price) >= (1.0 - tolerance)
