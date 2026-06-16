"""Factor-strategy-specific analytics that complement the shared src/metrics.py.

src/metrics.py gives us the portfolio-level risk metrics (Sharpe, Sortino,
drawdown, CAGR, Calmar). Those are computed on the equity curve and reused
verbatim. The helpers here add the things that are specific to a periodically
rebalanced factor book: turnover, monthly hit rate, and the active return vs a
benchmark (alpha / information ratio).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

TRADING_DAYS = 252


def factor_stats(rebalance_log: list[dict]) -> dict:
    """Summarise the rebalance log: turnover and monthly hit rate."""
    if not rebalance_log:
        return {}
    df = pd.DataFrame(rebalance_log)
    period_ret = df["period_return_pct"].iloc[1:]  # first period has no prior point
    return {
        "n_rebalances": int(len(df)),
        "avg_turnover_pct": round(float(df["turnover"].mean()) * 100, 1),
        "total_cost_drag_pct": round(float(df["cost"].sum()) * 100, 3),
        "monthly_hit_rate_pct": round(float((period_ret > 0).mean()) * 100, 1)
        if len(period_ret)
        else 0.0,
        "best_month_pct": round(float(period_ret.max()), 2) if len(period_ret) else 0.0,
        "worst_month_pct": round(float(period_ret.min()), 2) if len(period_ret) else 0.0,
    }


def active_return_stats(
    strategy_equity: pd.Series, benchmark_equity: pd.Series
) -> dict:
    """Information ratio and annualised alpha vs the benchmark.

    Both curves are aligned on their common dates; the active return is the daily
    difference in returns. The information ratio is the active-return analogue of
    the Sharpe ratio — the standard 'did the strategy add value over the
    benchmark' measure.
    """
    s = strategy_equity.pct_change()
    b = benchmark_equity.pct_change()
    df = pd.concat([s, b], axis=1, keys=["s", "b"]).dropna()
    if df.empty:
        return {}
    active = df["s"] - df["b"]
    ann_active = float(active.mean()) * TRADING_DAYS
    ann_te = float(active.std()) * np.sqrt(TRADING_DAYS)  # tracking error
    info_ratio = ann_active / ann_te if ann_te > 0 else 0.0
    bench_total = float(benchmark_equity.iloc[-1] / benchmark_equity.iloc[0] - 1.0)
    return {
        "benchmark_total_return_pct": round(bench_total * 100, 2),
        "annualized_alpha_pct": round(ann_active * 100, 2),
        "tracking_error_pct": round(ann_te * 100, 2),
        "information_ratio": round(info_ratio, 3),
    }
