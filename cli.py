#!/usr/bin/env python3
"""
cli.py — Command-line entry point for the Binance Futures Testnet Trading Bot.

Usage examples
--------------
# Market BUY
python cli.py place --symbol BTCUSDT --side BUY --type MARKET --qty 0.001

# Limit SELL
python cli.py place --symbol BTCUSDT --side SELL --type LIMIT --qty 0.001 --price 100000

# Stop-Limit BUY (bonus order type)
python cli.py place --symbol BTCUSDT --side BUY --type STOP_LIMIT --qty 0.001 \
    --price 95000 --stop-price 94000

# Show open orders
python cli.py orders --symbol BTCUSDT

# Show account balances
python cli.py account
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys

import requests

# Ensure the project root is on sys.path regardless of where the script is invoked
sys.path.insert(0, os.path.dirname(__file__))

from bot.client import BinanceClient, BinanceAPIError
from bot.logging_config import setup_logging
from bot.orders import place_order
from bot.validators import validate_order_params


# ---------------------------------------------------------------------------
# CLI argument parsing
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trading_bot",
        description=(
            "Binance Futures Testnet Trading Bot\n"
            "Places MARKET, LIMIT, and STOP-LIMIT orders via the Testnet REST API."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--api-key",
        default=os.getenv("BINANCE_API_KEY", ""),
        help="Binance Testnet API key (or set BINANCE_API_KEY env var).",
    )
    parser.add_argument(
        "--api-secret",
        default=os.getenv("BINANCE_API_SECRET", ""),
        help="Binance Testnet API secret (or set BINANCE_API_SECRET env var).",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity (default: INFO).",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # ── place ────────────────────────────────────────────────────────────
    place_p = sub.add_parser("place", help="Place a new futures order.")
    place_p.add_argument(
        "--symbol", "-s", required=True,
        help="Trading pair, e.g. BTCUSDT.",
    )
    place_p.add_argument(
        "--side", required=True,
        choices=["BUY", "SELL"],
        help="Order side.",
    )
    place_p.add_argument(
        "--type", "-t", dest="order_type", required=True,
        choices=["MARKET", "LIMIT", "STOP_LIMIT"],
        help="Order type.",
    )
    place_p.add_argument(
        "--qty", "-q", required=True,
        help="Order quantity (base asset).",
    )
    place_p.add_argument(
        "--price", "-p", default=None,
        help="Limit price (required for LIMIT and STOP_LIMIT).",
    )
    place_p.add_argument(
        "--stop-price", default=None,
        help="Stop trigger price (required for STOP_LIMIT).",
    )

    # ── orders ───────────────────────────────────────────────────────────
    orders_p = sub.add_parser("orders", help="List open orders.")
    orders_p.add_argument("--symbol", "-s", default=None,
                          help="Filter by symbol (optional).")

    # ── account ──────────────────────────────────────────────────────────
    sub.add_parser("account", help="Show account information and balances.")

    # ── cancel ───────────────────────────────────────────────────────────
    cancel_p = sub.add_parser("cancel", help="Cancel an open order.")
    cancel_p.add_argument("--symbol", "-s", required=True)
    cancel_p.add_argument("--order-id", type=int, required=True)

    return parser


# ---------------------------------------------------------------------------
# Sub-command handlers
# ---------------------------------------------------------------------------

def cmd_place(client: BinanceClient, args: argparse.Namespace, logger: logging.Logger) -> int:
    """Validate inputs then place the order. Returns exit code."""
    try:
        params = validate_order_params(
            symbol=args.symbol,
            side=args.side,
            order_type=args.order_type,
            quantity=args.qty,
            price=args.price,
            stop_price=args.stop_price,
        )
    except ValueError as exc:
        print(f"\n  ✗  Validation error: {exc}\n")
        logger.error("Validation error: %s", exc)
        return 1

    try:
        place_order(
            client=client,
            symbol=params["symbol"],
            side=params["side"],
            order_type=params["order_type"],
            quantity=params["quantity"],
            price=params["price"],
            stop_price=params["stop_price"],
        )
        return 0
    except BinanceAPIError:
        return 1
    except requests.RequestException as exc:
        print(f"\n  ✗  Network error: {exc}\n")
        logger.error("Network error: %s", exc)
        return 1


def cmd_orders(client: BinanceClient, args: argparse.Namespace, logger: logging.Logger) -> int:
    """Print open orders."""
    try:
        orders = client.get_open_orders(symbol=args.symbol)
    except (BinanceAPIError, requests.RequestException) as exc:
        print(f"\n  ✗  Failed to fetch orders: {exc}\n")
        logger.error("Failed to fetch orders: %s", exc)
        return 1

    if not orders:
        print("\n  No open orders.\n")
        return 0

    print(f"\n  Open orders ({len(orders)}):\n")
    for o in orders:
        print(
            f"  [{o.get('orderId')}]  {o.get('symbol')}  {o.get('side')}  "
            f"{o.get('type')}  qty={o.get('origQty')}  price={o.get('price')}  "
            f"status={o.get('status')}"
        )
    print()
    return 0


def cmd_account(client: BinanceClient, args: argparse.Namespace, logger: logging.Logger) -> int:
    """Print account balances."""
    try:
        account = client.get_account()
    except (BinanceAPIError, requests.RequestException) as exc:
        print(f"\n  ✗  Failed to fetch account: {exc}\n")
        logger.error("Failed to fetch account: %s", exc)
        return 1

    assets = [a for a in account.get("assets", []) if float(a.get("walletBalance", 0)) > 0]
    print(f"\n  Account — total wallet balance: {account.get('totalWalletBalance')} USDT")
    print(f"  Unrealised PnL: {account.get('totalUnrealizedProfit')} USDT\n")
    if assets:
        print("  Non-zero balances:")
        for a in assets:
            print(
                f"    {a['asset']:<10}  wallet={a['walletBalance']:<16}  "
                f"available={a.get('availableBalance', 'N/A')}"
            )
    print()
    return 0


def cmd_cancel(client: BinanceClient, args: argparse.Namespace, logger: logging.Logger) -> int:
    """Cancel an open order."""
    try:
        resp = client.cancel_order(symbol=args.symbol, order_id=args.order_id)
        print(f"\n  ✔  Order {resp.get('orderId')} cancelled. Status: {resp.get('status')}\n")
        logger.info("Order cancelled: %s", resp)
        return 0
    except (BinanceAPIError, requests.RequestException) as exc:
        print(f"\n  ✗  Failed to cancel order: {exc}\n")
        logger.error("Failed to cancel order: %s", exc)
        return 1


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

COMMAND_HANDLERS = {
    "place":   cmd_place,
    "orders":  cmd_orders,
    "account": cmd_account,
    "cancel":  cmd_cancel,
}


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    logger = setup_logging(args.log_level)
    logger.info("Command: %s | Args: %s", args.command, vars(args))

    # Credential check
    if not args.api_key or not args.api_secret:
        print(
            "\n  ✗  API credentials missing.\n"
            "  Set --api-key / --api-secret flags, or\n"
            "  export BINANCE_API_KEY and BINANCE_API_SECRET environment variables.\n"
        )
        sys.exit(1)

    client = BinanceClient(api_key=args.api_key, api_secret=args.api_secret)

    handler = COMMAND_HANDLERS.get(args.command)
    if handler is None:
        print(f"Unknown command: {args.command}")
        sys.exit(1)

    exit_code = handler(client, args, logger)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
