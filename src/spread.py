from __future__ import annotations

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def calculate_spread(
    series_a: pd.Series,
    series_b: pd.Series,
    beta: pd.Series | float,
    intercept: pd.Series | float = 0.0,
) -> pd.Series:
    """Calculate spread = A - beta * B - intercept.

    beta and intercept can be scalar (static OLS) or a time-aligned Series (Kalman).
    """
    aligned = pd.concat([series_a, series_b], axis=1).dropna()
    a = aligned.iloc[:, 0]
    b = aligned.iloc[:, 1]

    if isinstance(beta, pd.Series):
        beta = beta.reindex(aligned.index).ffill()
    if isinstance(intercept, pd.Series):
        intercept = intercept.reindex(aligned.index).ffill()

    spread = a - beta * b - intercept
    spread.name = "spread"
    return spread


def calculate_rolling_zscore(spread: pd.Series, window: int = 60, min_periods: int = 30) -> pd.Series:
    """Calculate rolling z-score of the spread using only past observations."""
    rolling_mean = spread.rolling(window=window, min_periods=min_periods).mean()
    rolling_std = spread.rolling(window=window, min_periods=min_periods).std()

    # Avoid division by zero — return NaN when std is ~0
    zscore = (spread - rolling_mean) / rolling_std.replace(0, np.nan)
    zscore.name = "zscore"
    return zscore
