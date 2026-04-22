# Binance Futures Testnet Trading Bot

A clean, production-structured Python CLI for placing orders on the **Binance Futures Testnet (USDT-M)**. Supports Market, Limit, and Stop-Limit order types with full logging and input validation.

---

## Project Structure

```
trading_bot/
├── bot/
│   ├── __init__.py
│   ├── client.py          # Binance REST client wrapper (signing, HTTP, error handling)
│   ├── orders.py          # Order placement logic + formatted output
│   ├── validators.py      # CLI input validation
│   └── logging_config.py  # Structured file + console logging setup
├── cli.py                 # CLI entry point (argparse)
├── logs/                  # Auto-created; log files written here
│   ├── market_order_example.log
│   └── limit_order_example.log
├── requirements.txt
└── README.md
```

---

## Setup

### 1. Register on Binance Futures Testnet

1. Visit [https://testnet.binancefuture.com](https://testnet.binancefuture.com)
2. Sign in (GitHub OAuth is supported)
3. Navigate to **API Management** → generate a new key pair
4. Copy your **API Key** and **Secret Key**

### 2. Clone / unzip the project

```bash
cd trading_bot
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

The only runtime dependency is `requests`. No third-party Binance SDK is used.

### 4. Set credentials

**Option A — environment variables (recommended):**

```bash
export BINANCE_API_KEY="your_api_key_here"
export BINANCE_API_SECRET="your_api_secret_here"
```

**Option B — inline flags on every command:**

```bash
python cli.py --api-key YOUR_KEY --api-secret YOUR_SECRET place ...
```

---

## How to Run

### Place a Market Order

```bash
# BUY 0.001 BTC at market price
python cli.py place --symbol BTCUSDT --side BUY --type MARKET --qty 0.001

# SELL 0.001 BTC at market price
python cli.py place --symbol BTCUSDT --side SELL --type MARKET --qty 0.001
```

### Place a Limit Order

```bash
# SELL limit at $100,000
python cli.py place --symbol BTCUSDT --side SELL --type LIMIT --qty 0.001 --price 100000

# BUY limit at $85,000
python cli.py place --symbol BTCUSDT --side BUY --type LIMIT --qty 0.001 --price 85000
```

### Place a Stop-Limit Order *(bonus)*

```bash
# BUY stop-limit: triggers at $94,000, places limit at $95,000
python cli.py place \
  --symbol BTCUSDT \
  --side BUY \
  --type STOP_LIMIT \
  --qty 0.001 \
  --price 95000 \
  --stop-price 94000
```

### View Open Orders

```bash
# All open orders
python cli.py orders

# Filtered by symbol
python cli.py orders --symbol BTCUSDT
```

### View Account Balances

```bash
python cli.py account
```

### Cancel an Order

```bash
python cli.py cancel --symbol BTCUSDT --order-id 4661093
```

### Verbose / Debug Logging

```bash
python cli.py --log-level DEBUG place --symbol BTCUSDT --side BUY --type MARKET --qty 0.001
```

---

## Sample Output

```
┌─────────────────────────────────────────┐
│           ORDER REQUEST SUMMARY          │
├─────────────────────────────────────────┤
│  Symbol     : BTCUSDT                   │
│  Side       : BUY                       │
│  Type       : MARKET                    │
│  Quantity   : 0.001                     │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│          ORDER RESPONSE DETAILS          │
├─────────────────────────────────────────┤
│  Order ID   : 4661093                   │
│  Client ID  : myOrder123                │
│  Symbol     : BTCUSDT                   │
│  Side       : BUY                       │
│  Type       : MARKET                    │
│  Status     : FILLED                    │
│  Exec Qty   : 0.001                     │
│  Avg Price  : 93450.10                  │
└─────────────────────────────────────────┘

  ✔  Order placed successfully! Status: FILLED
```

---

## Logging

Every run creates a timestamped log file in `logs/`:

```
logs/trading_bot_20250421_101501.log
```

Log format:

```
2025-04-21 10:15:01 | INFO     | trading_bot.client | REQUEST  method=POST ...
2025-04-21 10:15:01 | INFO     | trading_bot.client | RESPONSE status=200 body=...
```

- **File handler**: captures DEBUG/INFO/WARNING/ERROR
- **Console handler**: WARNING and above only (keeps stdout clean)

Sample log files are included in `logs/` for reference.

---

## Validation & Error Handling

| Scenario | Behaviour |
|---|---|
| Missing `--price` for LIMIT | Validation error before any API call |
| Missing `--stop-price` for STOP_LIMIT | Validation error before any API call |
| Invalid symbol characters | Clear error message |
| Non-positive quantity or price | Clear error message |
| Binance API error (e.g. `-1121 Invalid symbol`) | Prints error code + message, exits with code 1 |
| Network timeout / connection failure | Prints network error, exits with code 1 |
| Missing API credentials | Prints instructions, exits with code 1 |

---

## Assumptions

1. **Testnet only** — the base URL is hardcoded to `https://testnet.binancefuture.com`. Change `TESTNET_BASE_URL` in `bot/client.py` to target mainnet (add appropriate risk warnings).
2. **USDT-M futures** — all endpoints use `/fapi/v1`. For COIN-M futures (`/dapi/v1`) a different client instance would be required.
3. **Stop-Limit** maps to Binance's `type=STOP` on the futures API (which combines stop trigger + limit price).
4. **Quantity precision** — the bot sends the quantity exactly as provided. Binance will reject quantities that don't match the symbol's `LOT_SIZE` filter. Check the testnet's `GET /fapi/v1/exchangeInfo` for per-symbol precision rules.
5. **Time-in-force** defaults to `GTC` (Good Till Cancelled) for all non-market orders.
6. **Clock skew** — `recvWindow=5000ms` is used. If your system clock is significantly off, requests may be rejected; sync your system clock if you see `-1021` errors.

---

## Dependencies

```
requests>=2.31.0
```

Python 3.8+ required (uses `from __future__ import annotations`).
