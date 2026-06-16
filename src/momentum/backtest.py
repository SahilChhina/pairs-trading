"""Monthly-rebalanced backtest for the cross-sectional momentum strategy.

Design choices (and why):

* **Daily equity curve.** We hold the monthly weights fixed and compound daily
  portfolio returns. This makes the output directly compatible with the existing
  ``src/metrics.py`` (which annualises assuming 252 trading days) and is more
  realistic than a coarse month-to-month curve.

* **No look-ahead.** At each month-end we score using prices up to and including
  that day (the 12-1 score already skips the most recent month), trade at that
  close, and only earn the new weights' returns from the *next* day onward.

* **Costs are charged on turnover.** Monthly rotation is the main cost driver for
  this style, so we charge ``(transaction_cost_bps + slippage_bps)`` against the
  L1 turnover of the weight vector on each rebalance — the honest, net-of-cost
  number is what we report.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from .signals import momentum_score, month_end_rebalance_dates, rank_to_weights

logger = logging.getLogger(__name__)


def run_momentum_backtest(
    prices: pd.DataFrame,
    *,
    initial_capital: float = 100_000.0,
    lookback_days: int = 252,
    skip_days: int = 21,
    top_quantile: float = 0.2,
    long_short: bool = True,
    transaction_cost_bps: float = 5.0,
    slippage_bps: float = 5.0,
    start: str | None = None,
    end: str | None = None,
) -> dict:
    """Run the rebalance loop and return equity curve, rebalance log, and weights.

    ``prices`` should be the FULL price history (including the warm-up period
    needed to compute the first momentum score). ``start``/``end`` bound the
    *trading* window — performance is only measured from ``start`` onward, but
    scores can still look back into the pre-``start`` history.
    """
    prices = prices.sort_index()
    daily_returns = prices.pct_change()

    cost_rate = (transaction_cost_bps + slippage_bps) / 10_000.0

    # Trading window (the dates we actually hold positions / measure returns).
    trade_index = prices.loc[start:end].index
    if len(trade_index) == 0:
        raise ValueError("No trading dates in the requested window.")

    rebalance_dates = set(month_end_rebalance_dates(trade_index))

    current_weights = pd.Series(0.0, index=prices.columns)
    equity = initial_capital

    equity_dates: list[pd.Timestamp] = []
    equity_values: list[float] = []
    rebalance_log: list[dict] = []
    trade_log: list[dict] = []
    weights_history: dict[str, dict] = {}

    # open_positions tracks each ticker currently held:
    # { ticker: {entry_date, entry_price, weight, entry_equity} }
    open_positions: dict[str, dict] = {}

    prev_rebalance_equity = initial_capital

    for day in trade_index:
        # 1) Return earned today from the positions we came into the day with.
        day_ret = float((current_weights * daily_returns.loc[day]).sum())

        # 2) If today is a rebalance day, re-score and rotate (cost charged today).
        if day in rebalance_dates:
            score = momentum_score(
                prices, asof=day, lookback_days=lookback_days, skip_days=skip_days
            )
            new_weights = rank_to_weights(
                score, top_quantile=top_quantile, long_short=long_short
            )
            new_weights = new_weights.reindex(prices.columns).fillna(0.0)

            turnover = float((new_weights - current_weights).abs().sum())
            cost = turnover * cost_rate
            day_ret -= cost

            equity *= 1.0 + day_ret

            # --- Close all currently open positions and record each as a trade ---
            for ticker, pos in list(open_positions.items()):
                exit_price = prices.loc[day, ticker]
                entry_price = pos["entry_price"]
                if pd.isna(exit_price) or pd.isna(entry_price) or entry_price == 0:
                    continue
                direction = 1 if pos["weight"] > 0 else -1
                raw_ret = direction * (exit_price / entry_price - 1.0)
                holding_days = (day - pos["entry_date"]).days
                allocated = abs(pos["weight"]) * pos["entry_equity"]
                net_pnl = raw_ret * allocated
                trade_log.append({
                    "ticker": ticker,
                    "entry_date": pos["entry_date"].strftime("%Y-%m-%d"),
                    "exit_date": day.strftime("%Y-%m-%d"),
                    "direction": "long" if direction == 1 else "short",
                    "weight": round(pos["weight"], 4),
                    "entry_price": round(entry_price, 4),
                    "exit_price": round(exit_price, 4),
                    "return_pct": round(raw_ret * 100, 4),
                    "net_pnl": round(net_pnl, 2),
                    "holding_days": holding_days,
                })
            open_positions.clear()

            # --- Open a new position entry for every non-zero weight ---
            for ticker, w in new_weights[new_weights != 0].items():
                entry_price = prices.loc[day, ticker]
                if pd.isna(entry_price):
                    continue
                open_positions[ticker] = {
                    "entry_date": day,
                    "entry_price": entry_price,
                    "weight": w,
                    "entry_equity": equity,
                }

            longs = new_weights[new_weights > 0].index.tolist()
            shorts = new_weights[new_weights < 0].index.tolist()
            period_return = equity / prev_rebalance_equity - 1.0

            rebalance_log.append(
                {
                    "date": day.strftime("%Y-%m-%d"),
                    "n_long": len(longs),
                    "n_short": len(shorts),
                    "longs": longs,
                    "shorts": shorts,
                    "turnover": round(turnover, 4),
                    "cost": round(cost, 6),
                    "equity": round(equity, 2),
                    "period_return_pct": round(period_return * 100, 3),
                }
            )
            weights_history[day.strftime("%Y-%m-%d")] = new_weights[
                new_weights != 0
            ].round(4).to_dict()

            current_weights = new_weights
            prev_rebalance_equity = equity
        else:
            equity *= 1.0 + day_ret

        equity_dates.append(day)
        equity_values.append(equity)

    # Close any positions still open at the end of the backtest window.
    last_day = trade_index[-1]
    for ticker, pos in open_positions.items():
        exit_price = prices.loc[last_day, ticker]
        entry_price = pos["entry_price"]
        if pd.isna(exit_price) or pd.isna(entry_price) or entry_price == 0:
            continue
        direction = 1 if pos["weight"] > 0 else -1
        raw_ret = direction * (exit_price / entry_price - 1.0)
        holding_days = (last_day - pos["entry_date"]).days
        allocated = abs(pos["weight"]) * pos["entry_equity"]
        net_pnl = raw_ret * allocated
        trade_log.append({
            "ticker": ticker,
            "entry_date": pos["entry_date"].strftime("%Y-%m-%d"),
            "exit_date": last_day.strftime("%Y-%m-%d"),
            "direction": "long" if direction == 1 else "short",
            "weight": round(pos["weight"], 4),
            "entry_price": round(entry_price, 4),
            "exit_price": round(exit_price, 4),
            "return_pct": round(raw_ret * 100, 4),
            "net_pnl": round(net_pnl, 2),
            "holding_days": holding_days,
        })

    equity_curve = pd.Series(equity_values, index=pd.DatetimeIndex(equity_dates), name="equity")

    return {
        "equity_curve": equity_curve,
        "rebalance_log": rebalance_log,
        "trade_log": trade_log,
        "weights_history": weights_history,
    }


def run_equal_weight_benchmark(
    prices: pd.DataFrame,
    *,
    initial_capital: float = 100_000.0,
    start: str | None = None,
    end: str | None = None,
) -> pd.Series:
    """A naive 'buy the whole universe, equal weight' benchmark for comparison.

    Equal-weight, monthly-rebalanced, long-only across all available names. This
    is the 'just hold the market' baseline the long/short strategy must beat on a
    risk-adjusted basis to justify its complexity.
    """
    prices = prices.sort_index()
    daily_returns = prices.pct_change()
    trade_index = prices.loc[start:end].index
    rebalance_dates = set(month_end_rebalance_dates(trade_index))

    current_weights = pd.Series(0.0, index=prices.columns)
    equity = initial_capital
    dates: list[pd.Timestamp] = []
    values: list[float] = []

    for day in trade_index:
        day_ret = float((current_weights * daily_returns.loc[day]).sum())
        if day in rebalance_dates:
            available = prices.loc[:day].iloc[-1].dropna().index
            w = pd.Series(0.0, index=prices.columns)
            if len(available) > 0:
                w.loc[available] = 1.0 / len(available)
            current_weights = w
        equity *= 1.0 + day_ret
        dates.append(day)
        values.append(equity)

    return pd.Series(values, index=pd.DatetimeIndex(dates), name="benchmark")
