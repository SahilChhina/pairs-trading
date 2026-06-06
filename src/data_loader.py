from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)


def download_price_data(
    tickers: list[str],
    start: str,
    end: str | None = None,
) -> pd.DataFrame:
    """Download adjusted close prices for all tickers via yfinance.

    Returns a DataFrame indexed by date with tickers as columns.
    """
    logger.info("Downloading price data for %d tickers from %s", len(tickers), start)
    raw = yf.download(
        tickers,
        start=start,
        end=end,
        auto_adjust=True,
        progress=False,
        threads=True,
    )

    # yfinance returns multi-level columns when >1 ticker
    if isinstance(raw.columns, pd.MultiIndex):
        prices = raw["Close"]
    else:
        # Single ticker
        prices = raw[["Close"]]
        prices.columns = [tickers[0]]

    prices.index = pd.to_datetime(prices.index)
    prices.index.name = "date"
    logger.info("Downloaded %d rows x %d tickers", len(prices), len(prices.columns))
    return prices


def clean_price_data(
    prices: pd.DataFrame,
    max_missing_pct: float = 0.05,
) -> pd.DataFrame:
    """Remove tickers with excessive missing data, align dates, and forward-fill small gaps."""
    # Drop tickers exceeding missing threshold
    missing_pct = prices.isna().mean()
    bad_tickers = missing_pct[missing_pct > max_missing_pct].index.tolist()
    if bad_tickers:
        logger.warning("Dropping tickers with >%.0f%% missing data: %s", max_missing_pct * 100, bad_tickers)
        prices = prices.drop(columns=bad_tickers)

    # Forward-fill gaps up to 3 days (handles weekends / minor halts)
    prices = prices.ffill(limit=3)

    # Drop any remaining rows where all values are NaN
    prices = prices.dropna(how="all")

    # Drop duplicate dates
    prices = prices[~prices.index.duplicated(keep="first")]
    prices = prices.sort_index()

    logger.info("Cleaned price data: %d rows x %d tickers", len(prices), len(prices.columns))
    return prices


def save_prices(prices: pd.DataFrame, path: str) -> None:
    """Save cleaned price data as CSV."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    prices.to_csv(path)
    logger.info("Saved prices to %s", path)


def load_prices(path: str) -> pd.DataFrame:
    """Load saved price data from CSV."""
    prices = pd.read_csv(path, index_col=0, parse_dates=True)
    prices.index.name = "date"
    logger.info("Loaded prices from %s: %d rows x %d tickers", path, len(prices), len(prices.columns))
    return prices
