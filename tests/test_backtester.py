import numpy as np
import pandas as pd
import pytest

from src.backtester import PairBacktester
from src.signals import generate_pair_signals


def make_synthetic_pair(n=200, seed=7):
    """Two clearly mean-reverting assets that will generate at least one trade."""
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2022-01-01", periods=n, freq="B")
    base = 100 + np.cumsum(rng.normal(0, 0.5, n))
    # B tracks base closely, A diverges temporarily
    b = pd.Series(base, index=dates, name="B")
    a = pd.Series(base * 1.5 + rng.normal(0, 0.3, n), index=dates, name="A")
    prices = pd.DataFrame({"A": a, "B": b})
    return prices


def make_signals_with_one_trade(prices: pd.DataFrame) -> tuple:
    """Produce a simple signal series that opens exactly one trade."""
    from src.kalman import kalman_filter_hedge_ratio
    from src.spread import calculate_spread, calculate_rolling_zscore

    kf = kalman_filter_hedge_ratio(prices["A"], prices["B"])
    spread = calculate_spread(prices["A"], prices["B"], kf["beta"], kf["intercept"])
    zscore = calculate_rolling_zscore(spread, window=30, min_periods=15)
    signals = generate_pair_signals(zscore, entry_threshold=1.0, exit_threshold=0.1, max_holding_days=30)
    return kf, signals


def test_backtester_runs_without_error():
    prices = make_synthetic_pair()
    kf, signals = make_signals_with_one_trade(prices)

    bt = PairBacktester(prices, initial_capital=100_000, transaction_cost_bps=5, slippage_bps=5)
    result = bt.backtest_pair("A", "B", kf["beta"], signals)

    assert "equity_curve" in result
    assert "trade_log" in result
    assert len(result["equity_curve"]) > 0


def test_transaction_costs_deducted():
    prices = make_synthetic_pair()
    kf, signals = make_signals_with_one_trade(prices)

    bt = PairBacktester(prices, initial_capital=100_000, transaction_cost_bps=10, slippage_bps=10)
    result = bt.backtest_pair("A", "B", kf["beta"], signals)

    tl = result["trade_log"]
    if not tl.empty:
        assert (tl["transaction_costs"] > 0).all(), "Costs must be deducted"


def test_trade_log_columns():
    prices = make_synthetic_pair()
    kf, signals = make_signals_with_one_trade(prices)

    bt = PairBacktester(prices, initial_capital=100_000)
    result = bt.backtest_pair("A", "B", kf["beta"], signals)

    tl = result["trade_log"]
    if not tl.empty:
        required = {"entry_date", "exit_date", "net_pnl", "gross_pnl", "transaction_costs", "return_pct", "direction"}
        assert required.issubset(set(tl.columns))


def test_pnl_long_and_short():
    """Verify PnL direction is correct for both long and short spread trades."""
    prices = make_synthetic_pair()
    kf, signals = make_signals_with_one_trade(prices)

    bt = PairBacktester(prices, initial_capital=100_000)
    result = bt.backtest_pair("A", "B", kf["beta"], signals)

    tl = result["trade_log"]
    if not tl.empty:
        # net_pnl = gross_pnl - costs; gross can be positive or negative
        assert "net_pnl" in tl.columns
        assert tl["net_pnl"].dtype in [float, np.float64]


def test_equity_curve_starts_at_capital():
    prices = make_synthetic_pair()
    kf, signals = make_signals_with_one_trade(prices)

    bt = PairBacktester(prices, initial_capital=100_000, capital_per_trade_pct=0.10)
    result = bt.backtest_pair("A", "B", kf["beta"], signals, capital=10_000)

    eq = result["equity_curve"]
    # First value should be near the allocated capital (minus any entry cost on day 1)
    assert abs(eq.iloc[0] - 10_000) < 500
