import numpy as np
import pandas as pd
import pytest

from src.metrics import (
    calculate_cagr,
    calculate_max_drawdown,
    calculate_profit_factor,
    calculate_sharpe_ratio,
    calculate_sortino_ratio,
    calculate_win_rate,
    calculate_all_metrics,
)


def flat_equity(n=252, start=100_000):
    dates = pd.date_range("2022-01-01", periods=n, freq="B")
    return pd.Series([start] * n, index=dates)


def growing_equity(n=252, start=100_000, end=110_000):
    dates = pd.date_range("2022-01-01", periods=n, freq="B")
    values = np.linspace(start, end, n)
    return pd.Series(values, index=dates)


def trade_log(pnls: list[float]) -> pd.DataFrame:
    return pd.DataFrame({
        "net_pnl": pnls,
        "return_pct": [p / 10_000 for p in pnls],
        "holding_days": [5] * len(pnls),
    })


def test_sharpe_zero_vol():
    eq = flat_equity()
    returns = eq.pct_change().dropna()
    assert calculate_sharpe_ratio(returns) == 0.0


def test_sharpe_positive_drift():
    eq = growing_equity()
    returns = eq.pct_change().dropna()
    assert calculate_sharpe_ratio(returns) > 0


def test_max_drawdown_no_drawdown():
    eq = growing_equity()
    assert calculate_max_drawdown(eq) >= -0.01  # nearly 0


def test_max_drawdown_severe():
    dates = pd.date_range("2022-01-01", periods=4, freq="B")
    eq = pd.Series([100_000, 110_000, 60_000, 70_000], index=dates)
    dd = calculate_max_drawdown(eq)
    assert dd < -0.40  # ~45% drawdown


def test_cagr_positive():
    eq = growing_equity(n=252, start=100_000, end=110_000)
    assert calculate_cagr(eq) > 0


def test_win_rate():
    tl = trade_log([100, -50, 200, -30, 80])
    wr = calculate_win_rate(tl)
    assert abs(wr - 0.6) < 1e-9


def test_profit_factor():
    tl = trade_log([100, -50, 200, -30])
    pf = calculate_profit_factor(tl)
    assert abs(pf - (300 / 80)) < 1e-6


def test_profit_factor_no_losses():
    tl = trade_log([100, 200])
    assert calculate_profit_factor(tl) == float("inf")


def test_all_metrics_empty():
    eq = pd.Series(dtype=float)
    tl = pd.DataFrame()
    metrics = calculate_all_metrics(eq, tl)
    assert metrics == {}


def test_all_metrics_keys():
    eq = growing_equity()
    tl = trade_log([100, -50, 200])
    metrics = calculate_all_metrics(eq, tl)
    expected_keys = {"sharpe_ratio", "max_drawdown_pct", "cagr_pct", "win_rate_pct", "n_trades"}
    assert expected_keys.issubset(set(metrics.keys()))
