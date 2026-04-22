"""
Logging configuration for the Binance Futures Trading Bot.
Sets up both file and console handlers with structured formatting.
"""

import logging
import os
from datetime import datetime


LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")


def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """
    Configure and return the root logger for the trading bot.

    Creates a 'logs/' directory if it doesn't exist, writes structured
    log entries to a timestamped file, and also emits WARNING+ messages
    to the console so the operator sees critical events immediately.

    Args:
        log_level: String log level, e.g. "DEBUG", "INFO", "WARNING".

    Returns:
        Configured logger instance named 'trading_bot'.
    """
    os.makedirs(LOG_DIR, exist_ok=True)

    log_filename = os.path.join(
        LOG_DIR,
        f"trading_bot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
    )

    logger = logging.getLogger("trading_bot")
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Avoid adding duplicate handlers if called more than once
    if logger.handlers:
        return logger

    fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # File handler — captures everything at or above the configured level
    file_handler = logging.FileHandler(log_filename, encoding="utf-8")
    file_handler.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)

    # Console handler — only WARNING and above to keep stdout clean
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(fmt)
    logger.addHandler(console_handler)

    logger.info("Logger initialised — writing to %s", log_filename)
    return logger
