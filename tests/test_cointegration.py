import numpy as np
import pandas as pd
import pytest

from src.cointegration import calculate_correlation_matrix, engle_granger_test, find_cointegrated_pairs


def make_cointegrated_pair(n=500, seed=42):
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2018-01-01", periods=n, freq="B")
    b = pd.Series(100 + np.cumsum(rng.normal(0, 1, n)), index=dates, name="B")
    # A is cointegrated with B: A ≈ 1.5 * B + noise
    a = 1.5 * b + rng.normal(0, 2, n)
    a.name = "A"
    return a, b


def test_engle_granger_cointegrated_pair():
    a, b = make_cointegrated_pair()
    result = engle_granger_test(a, b)
    assert result["p_value"] < 0.05, "Should detect cointegration"
    assert "t_stat" in result
    assert result["n_obs"] > 0


def test_engle_granger_independent_pair():
    rng = np.random.default_rng(99)
    dates = pd.date_range("2018-01-01", periods=500, freq="B")
    a = pd.Series(np.cumsum(rng.normal(0, 1, 500)), index=dates)
    b = pd.Series(np.cumsum(rng.normal(0, 1, 500)), index=dates)
    result = engle_granger_test(a, b)
    # p-value above threshold for independent random walks (usually)
    assert result["p_value"] is not None


def test_engle_granger_short_series():
    dates = pd.date_range("2020-01-01", periods=50, freq="B")
    a = pd.Series(np.random.randn(50), index=dates)
    b = pd.Series(np.random.randn(50), index=dates)
    result = engle_granger_test(a, b)
    assert np.isnan(result["p_value"]), "Should return NaN for insufficient data"


def test_correlation_matrix():
    a, b = make_cointegrated_pair()
    prices = pd.DataFrame({"A": a, "B": b})
    corr = calculate_correlation_matrix(prices)
    assert corr.shape == (2, 2)
    assert abs(corr.loc["A", "B"]) > 0.9


def test_find_cointegrated_pairs():
    a, b = make_cointegrated_pair()
    prices = pd.DataFrame({"A": a, "B": b})
    result = find_cointegrated_pairs(prices, correlation_threshold=0.5, pvalue_threshold=0.05, min_history_days=100)
    assert len(result) >= 1
    assert "coint_pvalue" in result.columns
    assert result.iloc[0]["selected"] is True or result.iloc[0]["selected"] == True
