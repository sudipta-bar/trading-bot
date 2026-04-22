"""
Input validation for CLI arguments passed to the trading bot.

All validation raises ValueError with human-readable messages so the
CLI layer can catch them and display a friendly error to the user.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Optional


VALID_ORDER_TYPES = {"MARKET", "LIMIT", "STOP_LIMIT"}
VALID_SIDES = {"BUY", "SELL"}

# Binance symbol format is straightforward: all uppercase letters/digits
# We do a light check rather than maintaining an exhaustive list.
_MIN_SYMBOL_LEN = 3
_MAX_SYMBOL_LEN = 20


def validate_symbol(symbol: str) -> str:
    """Return normalised symbol or raise ValueError."""
    symbol = symbol.strip().upper()
    if not symbol.isalnum():
        raise ValueError(
            f"Symbol '{symbol}' contains invalid characters. "
            "Use alphanumeric only, e.g. BTCUSDT."
        )
    if not (_MIN_SYMBOL_LEN <= len(symbol) <= _MAX_SYMBOL_LEN):
        raise ValueError(
            f"Symbol '{symbol}' length ({len(symbol)}) is out of range "
            f"[{_MIN_SYMBOL_LEN}, {_MAX_SYMBOL_LEN}]."
        )
    return symbol


def validate_side(side: str) -> str:
    """Return normalised side or raise ValueError."""
    side = side.strip().upper()
    if side not in VALID_SIDES:
        raise ValueError(
            f"Side '{side}' is invalid. Choose from: {', '.join(sorted(VALID_SIDES))}."
        )
    return side


def validate_order_type(order_type: str) -> str:
    """Return normalised order type or raise ValueError."""
    order_type = order_type.strip().upper()
    if order_type not in VALID_ORDER_TYPES:
        raise ValueError(
            f"Order type '{order_type}' is invalid. "
            f"Choose from: {', '.join(sorted(VALID_ORDER_TYPES))}."
        )
    return order_type


def validate_quantity(quantity: str | float) -> Decimal:
    """Parse and validate quantity; must be a positive number."""
    try:
        qty = Decimal(str(quantity))
    except InvalidOperation:
        raise ValueError(f"Quantity '{quantity}' is not a valid number.")
    if qty <= 0:
        raise ValueError(f"Quantity must be greater than zero, got {qty}.")
    return qty


def validate_price(price: Optional[str | float]) -> Optional[Decimal]:
    """Parse and validate price; must be positive when provided."""
    if price is None:
        return None
    try:
        p = Decimal(str(price))
    except InvalidOperation:
        raise ValueError(f"Price '{price}' is not a valid number.")
    if p <= 0:
        raise ValueError(f"Price must be greater than zero, got {p}.")
    return p


def validate_stop_price(stop_price: Optional[str | float]) -> Optional[Decimal]:
    """Parse and validate stop price for stop-limit orders."""
    return validate_price(stop_price)  # same rules apply


def validate_order_params(
    symbol: str,
    side: str,
    order_type: str,
    quantity: str | float,
    price: Optional[str | float] = None,
    stop_price: Optional[str | float] = None,
) -> dict:
    """
    Validate all order parameters together and return a clean dict.

    Cross-field rules:
    - LIMIT orders require price.
    - STOP_LIMIT orders require both price and stop_price.
    - MARKET orders must NOT supply a price (ignored with a warning).

    Returns:
        dict with keys: symbol, side, order_type, quantity,
        price (Decimal | None), stop_price (Decimal | None).
    """
    symbol = validate_symbol(symbol)
    side = validate_side(side)
    order_type = validate_order_type(order_type)
    qty = validate_quantity(quantity)
    p = validate_price(price)
    sp = validate_stop_price(stop_price)

    if order_type == "LIMIT" and p is None:
        raise ValueError("LIMIT orders require a --price argument.")

    if order_type == "STOP_LIMIT":
        if p is None:
            raise ValueError("STOP_LIMIT orders require a --price argument (limit price).")
        if sp is None:
            raise ValueError("STOP_LIMIT orders require a --stop-price argument.")

    return {
        "symbol": symbol,
        "side": side,
        "order_type": order_type,
        "quantity": qty,
        "price": p,
        "stop_price": sp,
    }
