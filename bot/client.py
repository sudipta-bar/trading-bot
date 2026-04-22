"""
Low-level Binance Futures Testnet REST client.

Handles:
- Request signing (HMAC-SHA256)
- Timestamp synchronisation
- HTTP communication via `requests`
- Structured logging of every request / response / error
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import time
from decimal import Decimal
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import requests

logger = logging.getLogger("trading_bot.client")

TESTNET_BASE_URL = "https://testnet.binancefuture.com"
RECV_WINDOW = 5000  # ms


class BinanceAPIError(Exception):
    """Raised when the Binance API returns an error payload."""

    def __init__(self, code: int, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"Binance API error {code}: {message}")


class BinanceClient:
    """
    Thin wrapper around Binance Futures Testnet REST endpoints.

    Parameters
    ----------
    api_key:    Testnet API key.
    api_secret: Testnet API secret.
    base_url:   Override for the base URL (useful for mocking in tests).
    timeout:    HTTP request timeout in seconds.
    """

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        base_url: str = TESTNET_BASE_URL,
        timeout: int = 10,
    ) -> None:
        if not api_key or not api_secret:
            raise ValueError("api_key and api_secret must not be empty.")
        self._api_key = api_key
        self._api_secret = api_secret
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._session = requests.Session()
        self._session.headers.update(
            {
                "X-MBX-APIKEY": self._api_key,
                "Content-Type": "application/x-www-form-urlencoded",
            }
        )
        logger.info("BinanceClient initialised (base_url=%s)", self._base_url)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _timestamp(self) -> int:
        """Current UTC timestamp in milliseconds."""
        return int(time.time() * 1000)

    def _sign(self, params: dict) -> str:
        """Return HMAC-SHA256 hex signature for the given params dict."""
        query_string = urlencode(params)
        signature = hmac.new(
            self._api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return signature

    def _request(
        self,
        method: str,
        path: str,
        params: Optional[dict] = None,
        signed: bool = True,
    ) -> Dict[str, Any]:
        """
        Execute an HTTP request and return the parsed JSON response.

        Raises:
            BinanceAPIError: If the API returns a JSON error payload.
            requests.RequestException: On network / HTTP failures.
        """
        params = params or {}

        if signed:
            params["timestamp"] = self._timestamp()
            params["recvWindow"] = RECV_WINDOW
            params["signature"] = self._sign(params)

        url = f"{self._base_url}{path}"
        logger.info(
            "REQUEST  method=%s url=%s params=%s",
            method,
            url,
            {k: v for k, v in params.items() if k != "signature"},
        )

        try:
            if method.upper() == "GET":
                response = self._session.get(
                    url, params=params, timeout=self._timeout
                )
            else:  # POST / DELETE
                response = self._session.request(
                    method.upper(), url, data=params, timeout=self._timeout
                )

            logger.info(
                "RESPONSE status=%s body=%s",
                response.status_code,
                response.text[:500],  # cap to avoid giant log lines
            )

            data = response.json()

        except requests.exceptions.Timeout as exc:
            logger.error("REQUEST TIMEOUT url=%s error=%s", url, exc)
            raise
        except requests.exceptions.ConnectionError as exc:
            logger.error("CONNECTION ERROR url=%s error=%s", url, exc)
            raise
        except ValueError as exc:
            logger.error("JSON DECODE ERROR body=%s error=%s", response.text, exc)
            raise

        # Binance returns error payloads as JSON with a 'code' (negative int)
        if isinstance(data, dict) and data.get("code", 0) < 0:
            logger.error(
                "API ERROR code=%s msg=%s", data.get("code"), data.get("msg")
            )
            raise BinanceAPIError(data["code"], data.get("msg", "Unknown error"))

        return data

    # ------------------------------------------------------------------
    # Public API methods
    # ------------------------------------------------------------------

    def get_server_time(self) -> int:
        """Return Binance server time in ms (used for clock-skew checks)."""
        data = self._request("GET", "/fapi/v1/time", signed=False)
        return data["serverTime"]

    def get_exchange_info(self, symbol: Optional[str] = None) -> dict:
        """Fetch exchange info (optionally filtered to a single symbol)."""
        params = {}
        if symbol:
            params["symbol"] = symbol
        return self._request("GET", "/fapi/v1/exchangeInfo", params=params, signed=False)

    def get_account(self) -> dict:
        """Fetch account information (balances, positions, etc.)."""
        return self._request("GET", "/fapi/v2/account")

    def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: Decimal,
        price: Optional[Decimal] = None,
        stop_price: Optional[Decimal] = None,
        time_in_force: str = "GTC",
    ) -> dict:
        """
        Place a new futures order.

        Parameters
        ----------
        symbol:        Trading pair, e.g. 'BTCUSDT'.
        side:          'BUY' or 'SELL'.
        order_type:    'MARKET', 'LIMIT', or 'STOP'.
        quantity:      Order quantity.
        price:         Limit price (required for LIMIT / STOP_LIMIT).
        stop_price:    Stop trigger price (required for STOP_LIMIT).
        time_in_force: 'GTC', 'IOC', 'FOK' (ignored for MARKET).

        Returns:
            Parsed order response dict from Binance.
        """
        params: Dict[str, Any] = {
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "quantity": str(quantity),
        }

        if order_type == "LIMIT":
            params["price"] = str(price)
            params["timeInForce"] = time_in_force

        elif order_type == "STOP_LIMIT" or order_type == "STOP":
            # Binance futures uses type=STOP for stop-limit orders
            params["type"] = "STOP"
            params["price"] = str(price)
            params["stopPrice"] = str(stop_price)
            params["timeInForce"] = time_in_force

        logger.info(
            "PLACE ORDER symbol=%s side=%s type=%s qty=%s price=%s stopPrice=%s",
            symbol,
            side,
            order_type,
            quantity,
            price,
            stop_price,
        )

        return self._request("POST", "/fapi/v1/order", params=params)

    def cancel_order(self, symbol: str, order_id: int) -> dict:
        """Cancel an open order by orderId."""
        params = {"symbol": symbol, "orderId": order_id}
        logger.info("CANCEL ORDER symbol=%s orderId=%s", symbol, order_id)
        return self._request("DELETE", "/fapi/v1/order", params=params)

    def get_open_orders(self, symbol: Optional[str] = None) -> list:
        """Return all open orders, optionally filtered by symbol."""
        params = {}
        if symbol:
            params["symbol"] = symbol
        return self._request("GET", "/fapi/v1/openOrders", params=params)

    def get_order(self, symbol: str, order_id: int) -> dict:
        """Return details of a specific order."""
        params = {"symbol": symbol, "orderId": order_id}
        return self._request("GET", "/fapi/v1/order", params=params)
