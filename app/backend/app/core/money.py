from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")


def to_money(value) -> Decimal:
    """Convert to Decimal (never via float) and round to 2 places."""
    if isinstance(value, float):
        raise TypeError("floats are not allowed for money")
    return Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)
