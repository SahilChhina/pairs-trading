"""Cross-sectional momentum signal generation.

The signal is the classic Jegadeesh & Titman (1993) "12-1" momentum:
trailing 12-month return, skipping the most recent month to avoid short-term
reversal contamination.

Everything here is computed *cross-sectionally* — at a single point in time we
rank every stock against every other stock. That is the conceptual opposite of
the pairs engine, which looks at one spread *through time*.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Trading-day approximations. ~21 trading days per month, ~252 per year.
DAYS_PER_MONTH = 21
DAYS_PER_YEAR = 252


def momentum_score(
    prices: pd.DataFrame,
    asof: pd.Timestamp,
    lookback_days: int = DAYS_PER_YEAR,
    skip_days: int = DAYS_PER_MONTH,
) -> pd.Series:
    """Compute the 12-1 momentum score for every ticker as of ``asof``.

    score_i = P_i(asof - skip) / P_i(asof - lookback) - 1

    Using prices strictly on or before ``asof`` means there is no look-ahead:
    the score could have been computed in real time on that date.

    Returns a Series indexed by ticker (NaN for names without enough history).
    """
    window = prices.loc[:asof]
    if len(window) < lookback_days + 1:
        # Not enough history yet for any name.
        return pd.Series(dtype=float)

    end_px = window.iloc[-1 - skip_days]      # price one month ago (skip recent month)
    start_px = window.iloc[-1 - lookback_days]  # price twelve months ago

    score = end_px / start_px - 1.0
    # Require both endpoints to be valid prices.
    valid = end_px.notna() & start_px.notna()
    return score.where(valid).dropna()


def rank_to_weights(
    score: pd.Series,
    top_quantile: float = 0.2,
    long_short: bool = True,
) -> pd.Series:
    """Convert a cross-sectional score into portfolio weights.

    - Long the top ``top_quantile`` fraction (highest momentum), equal-weighted.
    - If ``long_short``, short the bottom ``top_quantile`` fraction, equal-weighted.

    The result is dollar-neutral when long_short=True (sum of weights ~ 0, gross
    exposure ~ 2.0: 1.0 long + 1.0 short). When long_short=False it is a
    long-only book with weights summing to 1.0.

    Returns a Series of weights indexed by ticker (only non-zero names included).
    """
    score = score.dropna()
    n = len(score)
    if n == 0:
        return pd.Series(dtype=float)

    k = max(1, int(round(n * top_quantile)))
    ranked = score.sort_values(ascending=False)

    longs = ranked.index[:k]
    weights = pd.Series(0.0, index=score.index)
    weights.loc[longs] = 1.0 / k

    if long_short:
        shorts = ranked.index[-k:]
        weights.loc[shorts] = -1.0 / k

    return weights[weights != 0.0]


def month_end_rebalance_dates(index: pd.DatetimeIndex) -> list[pd.Timestamp]:
    """Return the last trading day of each month present in ``index``."""
    s = pd.Series(index=index, data=index)
    # Group by year-month, take the max (last) trading day in each.
    last_days = s.groupby([index.year, index.month]).max()
    return sorted(last_days.tolist())
