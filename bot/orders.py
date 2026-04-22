"""
Order placement and presentation logic.

This layer sits between the CLI and the raw Binance client.
It is responsible for:
- Calling the client with validated parameters
- Formatting human-readable summaries of requests and responses
- Centralising the print / logging calls so the CLI stays thin
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Optional

from .client import BinanceClient, BinanceAPIError

logger = logging.getLogger("trading_bot.orders")


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def _fmt_request_summary(
    symbol: str,
    side: str,
    order_type: str,
    quantity: Decimal,
    price: Optional[Decimal],
    stop_price: Optional[Decimal],
) -> str:
    lines = [
        "",
        "┌─────────────────────────────────────────┐",
        "│           ORDER REQUEST SUMMARY          │",
        "├─────────────────────────────────────────┤",
        f"│  Symbol     : {symbol:<26}│",
        f"│  Side       : {side:<26}│",
        f"│  Type       : {order_type:<26}│",
        f"│  Quantity   : {str(quantity):<26}│",
    ]
    if price is not None:
        lines.append(f"│  Price      : {str(price):<26}│")
    if stop_price is not None:
        lines.append(f"│  Stop Price : {str(stop_price):<26}│")
    lines.append("└─────────────────────────────────────────┘")
    return "\n".join(lines)


def _fmt_response_summary(resp: dict) -> str:
    order_id    = resp.get("orderId", "N/A")
    status      = resp.get("status", "N/A")
    exec_qty    = resp.get("executedQty", "N/A")
    avg_price   = resp.get("avgPrice", resp.get("price", "N/A"))
    client_id   = resp.get("clientOrderId", "N/A")
    symbol      = resp.get("symbol", "N/A")
    side        = resp.get("side", "N/A")
    o_type      = resp.get("type", "N/A")

    lines = [
        "",
        "┌─────────────────────────────────────────┐",
        "│          ORDER RESPONSE DETAILS          │",
        "├─────────────────────────────────────────┤",
        f"│  Order ID   : {str(order_id):<26}│",
        f"│  Client ID  : {str(client_id):<26}│",
        f"│  Symbol     : {str(symbol):<26}│",
        f"│  Side       : {str(side):<26}│",
        f"│  Type       : {str(o_type):<26}│",
        f"│  Status     : {str(status):<26}│",
        f"│  Exec Qty   : {str(exec_qty):<26}│",
        f"│  Avg Price  : {str(avg_price):<26}│",
        "└─────────────────────────────────────────┘",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Core order function
# ---------------------------------------------------------------------------

def place_order(
    client: BinanceClient,
    symbol: str,
    side: str,
    order_type: str,
    quantity: Decimal,
    price: Optional[Decimal] = None,
    stop_price: Optional[Decimal] = None,
) -> dict:
    """
    Place an order via the client, print summaries, and return the response.

    Handles BinanceAPIError and re-raises after printing a friendly message.
    Network exceptions bubble up to the CLI layer.

    Returns:
        Raw response dict from Binance on success.
    Raises:
        BinanceAPIError: On Binance-level errors (invalid params, etc.)
        requests.RequestException: On transport-level errors.
    """
    # 1. Print request summary
    print(_fmt_request_summary(symbol, side, order_type, quantity, price, stop_price))
    logger.info(
        "Placing order: symbol=%s side=%s type=%s qty=%s price=%s stop=%s",
        symbol, side, order_type, quantity, price, stop_price,
    )

    # 2. Call the exchange
    try:
        response = client.place_order(
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            stop_price=stop_price,
        )
    except BinanceAPIError as exc:
        logger.error("Order placement failed: %s", exc)
        print(f"\n  ✗  ORDER FAILED — Binance error {exc.code}: {exc.message}\n")
        raise
    except Exception as exc:
        logger.error("Unexpected error during order placement: %s", exc)
        print(f"\n  ✗  ORDER FAILED — {exc}\n")
        raise

    # 3. Print response summary
    print(_fmt_response_summary(response))

    status = response.get("status", "")
    if status in ("FILLED", "NEW", "PARTIALLY_FILLED"):
        print(f"\n  ✔  Order placed successfully! Status: {status}\n")
        logger.info("Order placed successfully: orderId=%s status=%s", response.get("orderId"), status)
    else:
        print(f"\n  ⚠  Order created with status: {status}\n")
        logger.warning("Order has unexpected status: %s | full response: %s", status, response)

    return response
