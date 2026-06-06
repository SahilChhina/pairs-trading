from __future__ import annotations

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

TRADING_DAYS = 252


def calculate_returns(equity_curve: pd.Series) -> pd.Series:
    return equity_curve.pct_change().dropna()


def calculate_sharpe_ratio(returns: pd.Series, periods_per_year: int = TRADING_DAYS) -> float:
    if returns.empty or returns.std() == 0:
        return 0.0
    return float((returns.mean() / returns.std()) * np.sqrt(periods_per_year))


def calculate_sortino_ratio(returns: pd.Series, periods_per_year: int = TRADING_DAYS) -> float:
    if returns.empty:
        return 0.0
    downside = returns[returns < 0]
    if downside.empty or downside.std() == 0:
        return 0.0
    return float((returns.mean() / downside.std()) * np.sqrt(periods_per_year))


def calculate_max_drawdown(equity_curve: pd.Series) -> float:
    if equity_curve.empty:
        return 0.0
    peak = equity_curve.cummax()
    dd = (equity_curve - peak) / peak
    return float(dd.min())


def calculate_cagr(equity_curve: pd.Series, periods_per_year: int = TRADING_DAYS) -> float:
    if len(equity_curve) < 2:
        return 0.0
    n_periods = len(equity_curve)
    total_return = equity_curve.iloc[-1] / equity_curve.iloc[0]
    years = n_periods / periods_per_year
    return float(total_return ** (1 / years) - 1)


def calculate_win_rate(trade_log: pd.DataFrame) -> float:
    if trade_log.empty or "net_pnl" not in trade_log.columns:
        return 0.0
    wins = (trade_log["net_pnl"] > 0).sum()
    return float(wins / len(trade_log))


def calculate_profit_factor(trade_log: pd.DataFrame) -> float:
    if trade_log.empty or "net_pnl" not in trade_log.columns:
        return 0.0
    gross_profit = trade_log.loc[trade_log["net_pnl"] > 0, "net_pnl"].sum()
    gross_loss = abs(trade_log.loc[trade_log["net_pnl"] < 0, "net_pnl"].sum())
    return float(gross_profit / gross_loss) if gross_loss > 0 else float("inf")


def calculate_all_metrics(equity_curve: pd.Series, trade_log: pd.DataFrame) -> dict:
    """Compute the full suite of risk-adjusted performance metrics."""
    if equity_curve.empty:
        return {}

    returns = calculate_returns(equity_curve)
    initial = equity_curve.iloc[0]
    final = equity_curve.iloc[-1]
    total_return = (final - initial) / initial
    ann_vol = returns.std() * np.sqrt(TRADING_DAYS) if not returns.empty else 0.0
    max_dd = calculate_max_drawdown(equity_curve)
    cagr = calculate_cagr(equity_curve)
    calmar = cagr / abs(max_dd) if max_dd != 0 else 0.0

    n_trades = len(trade_log) if not trade_log.empty else 0
    win_rate = calculate_win_rate(trade_log)
    avg_return = float(trade_log["return_pct"].mean()) if not trade_log.empty and "return_pct" in trade_log.columns else 0.0
    avg_holding = float(trade_log["holding_days"].mean()) if not trade_log.empty and "holding_days" in trade_log.columns else 0.0
    best_trade = float(trade_log["net_pnl"].max()) if not trade_log.empty and "net_pnl" in trade_log.columns else 0.0
    worst_trade = float(trade_log["net_pnl"].min()) if not trade_log.empty and "net_pnl" in trade_log.columns else 0.0

    return {
        "initial_capital": round(initial, 2),
        "final_value": round(final, 2),
        "total_return_pct": round(total_return * 100, 2),
        "cagr_pct": round(cagr * 100, 2),
        "annualized_volatility_pct": round(ann_vol * 100, 2),
        "sharpe_ratio": round(calculate_sharpe_ratio(returns), 3),
        "sortino_ratio": round(calculate_sortino_ratio(returns), 3),
        "max_drawdown_pct": round(max_dd * 100, 2),
        "calmar_ratio": round(calmar, 3),
        "n_trades": n_trades,
        "win_rate_pct": round(win_rate * 100, 2),
        "avg_trade_return_pct": round(avg_return, 4),
        "avg_holding_days": round(avg_holding, 1),
        "profit_factor": round(calculate_profit_factor(trade_log), 3),
        "best_trade": round(best_trade, 2),
        "worst_trade": round(worst_trade, 2),
    }
