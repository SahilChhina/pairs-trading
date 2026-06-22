"""Monte Carlo robustness tests for the momentum backtest.

A single backtest is one path through history — it can't tell you whether the
result reflects a real edge or a lucky sequence of events. These bootstraps
resample the realised results thousands of times to build a *distribution* of
outcomes, so the headline numbers come with honest confidence bands.

Two complementary tests:

* **Trade-level bootstrap.** Resample the individual position trades (with
  replacement) and recompute the per-trade edge each time. Answers: "is the
  ~0.4% average trade / 1.10 profit factor distinguishable from zero, or is it
  noise?" The fraction of simulations with a positive mean is an empirical
  significance check.

* **Monthly-return bootstrap.** Resample the monthly portfolio returns (each
  month kept intact, so within-month position correlation is preserved) and
  compound them into synthetic equity curves. Answers: "given the same monthly
  behaviour in a different order, what range of total returns and — crucially —
  drawdowns could we have seen?" The realised −52% drawdown is just one draw
  from this distribution.

Note on method: we resample at the *monthly* (already-aggregated) level, which
removes most of the daily-autocorrelation concern that makes naive return
bootstraps misleading for trend strategies. Each month's joint position outcome
stays bundled together.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

TRADING_DAYS = 252
MONTHS_PER_YEAR = 12


def _percentiles(arr: np.ndarray, ps=(5, 25, 50, 75, 95)) -> dict:
    return {f"p{p}": round(float(np.percentile(arr, p)), 4) for p in ps}


def trade_bootstrap(
    trade_returns_pct: np.ndarray,
    trade_pnl: np.ndarray,
    *,
    n_sims: int = 10_000,
    seed: int = 42,
) -> dict:
    """Bootstrap individual trades to test whether the per-trade edge is real."""
    rng = np.random.default_rng(seed)
    n = len(trade_returns_pct)

    mean_returns = np.empty(n_sims)
    win_rates = np.empty(n_sims)
    profit_factors = np.empty(n_sims)

    for i in range(n_sims):
        idx = rng.integers(0, n, size=n)
        r = trade_returns_pct[idx]
        p = trade_pnl[idx]
        mean_returns[i] = r.mean()
        win_rates[i] = (p > 0).mean() * 100.0
        gross_profit = p[p > 0].sum()
        gross_loss = -p[p < 0].sum()
        profit_factors[i] = gross_profit / gross_loss if gross_loss > 0 else np.inf

    pf_finite = profit_factors[np.isfinite(profit_factors)]

    return {
        "n_trades": int(n),
        "n_sims": int(n_sims),
        "actual_mean_return_pct": round(float(trade_returns_pct.mean()), 4),
        "actual_win_rate_pct": round(float((trade_pnl > 0).mean() * 100.0), 2),
        "mean_return_pct": _percentiles(mean_returns),
        "win_rate_pct": _percentiles(win_rates),
        "profit_factor": _percentiles(pf_finite),
        # Empirical significance: how often the resampled edge stays positive.
        "pct_sims_mean_positive": round(float((mean_returns > 0).mean() * 100.0), 2),
        "pct_sims_pf_above_1": round(float((profit_factors > 1).mean() * 100.0), 2),
    }


def monthly_return_bootstrap(
    monthly_returns: np.ndarray,
    *,
    initial_capital: float = 100_000.0,
    benchmark_total_return_pct: float | None = None,
    n_sims: int = 10_000,
    seed: int = 42,
) -> dict:
    """Bootstrap monthly portfolio returns into synthetic equity curves.

    ``monthly_returns`` are decimal returns (e.g. 0.02 for +2%).
    """
    rng = np.random.default_rng(seed)
    n_months = len(monthly_returns)
    years = n_months / MONTHS_PER_YEAR

    total_returns = np.empty(n_sims)
    cagrs = np.empty(n_sims)
    max_drawdowns = np.empty(n_sims)
    sharpes = np.empty(n_sims)

    for i in range(n_sims):
        idx = rng.integers(0, n_months, size=n_months)
        sample = monthly_returns[idx]

        curve = initial_capital * np.cumprod(1.0 + sample)
        total_ret = curve[-1] / initial_capital - 1.0
        total_returns[i] = total_ret * 100.0
        cagrs[i] = ((curve[-1] / initial_capital) ** (1.0 / years) - 1.0) * 100.0

        peak = np.maximum.accumulate(curve)
        dd = (curve - peak) / peak
        max_drawdowns[i] = dd.min() * 100.0

        mu, sigma = sample.mean(), sample.std()
        sharpes[i] = (mu / sigma * np.sqrt(MONTHS_PER_YEAR)) if sigma > 0 else 0.0

    actual_total = (np.prod(1.0 + monthly_returns) - 1.0) * 100.0

    result = {
        "n_months": int(n_months),
        "n_sims": int(n_sims),
        "actual_total_return_pct": round(float(actual_total), 2),
        "total_return_pct": _percentiles(total_returns),
        "cagr_pct": _percentiles(cagrs),
        "max_drawdown_pct": _percentiles(max_drawdowns),
        "sharpe_ratio": _percentiles(sharpes),
        "pct_sims_positive": round(float((total_returns > 0).mean() * 100.0), 2),
    }
    if benchmark_total_return_pct is not None:
        result["benchmark_total_return_pct"] = round(float(benchmark_total_return_pct), 2)
        result["pct_sims_beat_benchmark"] = round(
            float((total_returns > benchmark_total_return_pct).mean() * 100.0), 2
        )
    return result


def run_monte_carlo(
    trades: pd.DataFrame,
    rebalance_log: pd.DataFrame,
    *,
    initial_capital: float = 100_000.0,
    benchmark_total_return_pct: float | None = None,
    n_sims: int = 10_000,
    seed: int = 42,
) -> dict:
    """Run both bootstraps and return a combined report dict."""
    trade_ret = trades["return_pct"].to_numpy(dtype=float)
    trade_pnl = trades["net_pnl"].to_numpy(dtype=float)

    # First rebalance period has no prior point — drop it.
    monthly_pct = rebalance_log["period_return_pct"].to_numpy(dtype=float)[1:]
    monthly_returns = monthly_pct / 100.0

    logger.info(
        "Monte Carlo: %d trades, %d monthly returns, %d sims",
        len(trade_ret), len(monthly_returns), n_sims,
    )

    return {
        "n_sims": int(n_sims),
        "seed": int(seed),
        "trade_bootstrap": trade_bootstrap(
            trade_ret, trade_pnl, n_sims=n_sims, seed=seed
        ),
        "monthly_bootstrap": monthly_return_bootstrap(
            monthly_returns,
            initial_capital=initial_capital,
            benchmark_total_return_pct=benchmark_total_return_pct,
            n_sims=n_sims,
            seed=seed,
        ),
    }
