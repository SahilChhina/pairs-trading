from __future__ import annotations

import itertools
import logging
from pathlib import Path

import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import coint

logger = logging.getLogger(__name__)


def calculate_correlation_matrix(prices: pd.DataFrame) -> pd.DataFrame:
    """Calculate pairwise Pearson correlation of log prices."""
    log_prices = np.log(prices.dropna())
    return log_prices.corr()


def engle_granger_test(series_a: pd.Series, series_b: pd.Series) -> dict:
    """Run Engle-Granger cointegration test on two price series.

    Null hypothesis: no cointegration. A low p-value rejects that null.
    """
    # Align on common dates and drop any NaNs
    aligned = pd.concat([series_a, series_b], axis=1).dropna()
    if len(aligned) < 100:
        return {
            "t_stat": np.nan,
            "p_value": np.nan,
            "critical_1pct": np.nan,
            "critical_5pct": np.nan,
            "critical_10pct": np.nan,
            "n_obs": len(aligned),
        }

    a = aligned.iloc[:, 0].values
    b = aligned.iloc[:, 1].values

    t_stat, p_value, crit_values = coint(a, b)

    return {
        "t_stat": float(t_stat),
        "p_value": float(p_value),
        "critical_1pct": float(crit_values[0]),
        "critical_5pct": float(crit_values[1]),
        "critical_10pct": float(crit_values[2]),
        "n_obs": len(aligned),
    }


def find_cointegrated_pairs(
    prices: pd.DataFrame,
    correlation_threshold: float = 0.70,
    pvalue_threshold: float = 0.05,
    min_history_days: int = 250,
    save_path: str | None = None,
) -> pd.DataFrame:
    """Test all eligible pairs for cointegration and return ranked candidates.

    IMPORTANT: Only call this on training-period data to avoid look-ahead bias.
    """
    tickers = prices.columns.tolist()
    corr_matrix = calculate_correlation_matrix(prices)

    results: list[dict] = []

    for ticker_a, ticker_b in itertools.combinations(tickers, 2):
        series_a = prices[ticker_a].dropna()
        series_b = prices[ticker_b].dropna()

        # Align and check sufficient history
        aligned = pd.concat([series_a, series_b], axis=1).dropna()
        if len(aligned) < min_history_days:
            logger.debug("Skipping %s/%s — insufficient history (%d days)", ticker_a, ticker_b, len(aligned))
            continue

        # Correlation filter first (cheap)
        corr = corr_matrix.loc[ticker_a, ticker_b]
        if abs(corr) < correlation_threshold:
            continue

        # Engle-Granger test
        eg = engle_granger_test(series_a, series_b)
        if np.isnan(eg["p_value"]):
            continue

        results.append({
            "stock_a": ticker_a,
            "stock_b": ticker_b,
            "correlation": round(corr, 4),
            "coint_t_stat": round(eg["t_stat"], 4),
            "coint_pvalue": round(eg["p_value"], 6),
            "critical_value_1pct": round(eg["critical_1pct"], 4),
            "critical_value_5pct": round(eg["critical_5pct"], 4),
            "critical_value_10pct": round(eg["critical_10pct"], 4),
            "n_obs": eg["n_obs"],
            "selected": eg["p_value"] < pvalue_threshold,
        })

    if not results:
        logger.warning("No candidate pairs found. Try loosening thresholds.")
        return pd.DataFrame()

    df = pd.DataFrame(results).sort_values("coint_pvalue").reset_index(drop=True)

    logger.info(
        "Tested %d pairs. %d passed correlation filter. %d cointegrated at p<%.2f.",
        len(list(itertools.combinations(tickers, 2))),
        len(df),
        df["selected"].sum(),
        pvalue_threshold,
    )

    if save_path:
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(save_path, index=False)
        logger.info("Saved cointegration results to %s", save_path)

    return df
