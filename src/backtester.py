from __future__ import annotations

"""Single-pair and portfolio backtester.

Execution assumptions:
  - Trades execute at next day's adjusted close after signal generation.
  - Signals are already shifted by one day in signals.py.
  - Dollar-neutral sizing: equal dollar value on each leg.
  - Transaction costs and slippage deducted from net PnL.
"""

import logging
from pathlib import Path

import numpy as np
import pandas as pd

from src.risk import apply_position_limits, check_drawdown_stop

logger = logging.getLogger(__name__)


class PairBacktester:
    def __init__(
        self,
        prices: pd.DataFrame,
        initial_capital: float = 100_000.0,
        transaction_cost_bps: float = 5.0,
        slippage_bps: float = 5.0,
        capital_per_trade_pct: float = 0.10,
        max_open_positions: int = 5,
        max_portfolio_drawdown_stop: float = 0.25,
    ) -> None:
        self.prices = prices
        self.initial_capital = initial_capital
        self.tc_bps = transaction_cost_bps
        self.slip_bps = slippage_bps
        self.trade_pct = capital_per_trade_pct
        self.max_open = max_open_positions
        self.max_dd_stop = max_portfolio_drawdown_stop

    def _cost(self, notional: float) -> float:
        return notional * (self.tc_bps + self.slip_bps) / 10_000

    def backtest_pair(
        self,
        stock_a: str,
        stock_b: str,
        beta: pd.Series,
        signals: pd.DataFrame,
        capital: float | None = None,
    ) -> dict:
        """Backtest a single pair. Returns equity_curve, trade_log, and metrics dict."""
        capital = capital if capital is not None else self.initial_capital * self.trade_pct
        price_a = self.prices[stock_a]
        price_b = self.prices[stock_b]

        # Align everything on common dates present in signals
        idx = signals.index.intersection(price_a.dropna().index).intersection(price_b.dropna().index)
        signals = signals.loc[idx]
        price_a = price_a.loc[idx]
        price_b = price_b.loc[idx]
        beta = beta.reindex(idx).ffill().bfill()

        equity = capital
        equity_curve: list[tuple] = []
        trade_log: list[dict] = []

        in_trade = False
        trade: dict = {}
        i_entry = 0

        for i, date in enumerate(idx):
            pos = signals.loc[date, "position"]
            z = signals.loc[date, "zscore"]
            pa = price_a.loc[date]
            pb = price_b.loc[date]
            bt = beta.loc[date]

            if not in_trade and pos != 0:
                # ---- ENTRY ----
                half = capital / 2
                # Dollar-neutral: equal dollar on each leg
                shares_a = (half / pa) * pos           # pos=1 → long A; pos=-1 → short A
                shares_b = (half / pb) * (-pos * bt)  # opposite direction, beta-adjusted

                notional = abs(shares_a * pa) + abs(shares_b * pb)
                entry_cost = self._cost(notional)

                trade = {
                    "trade_id": int(signals.loc[date, "trade_id"]),
                    "pair": f"{stock_a}/{stock_b}",
                    "entry_date": date,
                    "exit_date": None,
                    "direction": "long_spread" if pos == 1 else "short_spread",
                    "entry_zscore": round(z, 4),
                    "exit_zscore": None,
                    "entry_price_a": round(pa, 4),
                    "entry_price_b": round(pb, 4),
                    "exit_price_a": None,
                    "exit_price_b": None,
                    "beta_entry": round(bt, 4),
                    "beta_exit": None,
                    "shares_a": round(shares_a, 4),
                    "shares_b": round(shares_b, 4),
                    "capital_allocated": capital,
                    "entry_cost": round(entry_cost, 2),
                    "exit_cost": 0.0,
                    "gross_pnl": 0.0,
                    "transaction_costs": round(entry_cost, 2),
                    "slippage": 0.0,
                    "net_pnl": 0.0,
                    "holding_days": 0,
                    "exit_reason": "",
                    "return_pct": 0.0,
                }
                equity -= entry_cost
                in_trade = True
                i_entry = i

            elif in_trade and pos == 0:
                # ---- EXIT ----
                pnl_a = trade["shares_a"] * (pa - trade["entry_price_a"])
                pnl_b = trade["shares_b"] * (pb - trade["entry_price_b"])
                gross_pnl = pnl_a + pnl_b

                notional_exit = abs(trade["shares_a"] * pa) + abs(trade["shares_b"] * pb)
                exit_cost = self._cost(notional_exit)

                net_pnl = gross_pnl - trade["entry_cost"] - exit_cost
                equity += net_pnl

                # Positions are shifted +1, so the exit at day i was triggered by the
                # raw signal at day i-1. Read the recorded exit_reason from that bar.
                trigger_reason = signals.iloc[i - 1]["exit_reason"] if i > 0 else ""
                exit_reason = trigger_reason or "mean_reversion"
                holding_days = i - i_entry

                trade.update({
                    "exit_date": date,
                    "exit_zscore": round(z, 4),
                    "exit_price_a": round(pa, 4),
                    "exit_price_b": round(pb, 4),
                    "beta_exit": round(bt, 4),
                    "exit_cost": round(exit_cost, 2),
                    "gross_pnl": round(gross_pnl, 2),
                    "transaction_costs": round(trade["entry_cost"] + exit_cost, 2),
                    "net_pnl": round(net_pnl, 2),
                    "holding_days": int(holding_days),
                    "exit_reason": exit_reason,
                    "return_pct": round(net_pnl / capital * 100, 4),
                })
                trade_log.append(trade)
                in_trade = False
                trade = {}

            equity_curve.append((date, equity))

        # Close any open trade at end of period using last price
        if in_trade and trade:
            last_date = idx[-1]
            pa = price_a.iloc[-1]
            pb = price_b.iloc[-1]
            bt = beta.iloc[-1]
            pnl_a = trade["shares_a"] * (pa - trade["entry_price_a"])
            pnl_b = trade["shares_b"] * (pb - trade["entry_price_b"])
            gross_pnl = pnl_a + pnl_b
            notional_exit = abs(trade["shares_a"] * pa) + abs(trade["shares_b"] * pb)
            exit_cost = self._cost(notional_exit)
            net_pnl = gross_pnl - trade["entry_cost"] - exit_cost
            equity += net_pnl
            trade.update({
                "exit_date": last_date,
                "exit_price_a": round(pa, 4),
                "exit_price_b": round(pb, 4),
                "beta_exit": round(bt, 4),
                "exit_cost": round(exit_cost, 2),
                "gross_pnl": round(gross_pnl, 2),
                "transaction_costs": round(trade["entry_cost"] + exit_cost, 2),
                "net_pnl": round(net_pnl, 2),
                "holding_days": int(len(idx) - 1 - i_entry),
                "exit_reason": "end_of_period",
                "return_pct": round(net_pnl / capital * 100, 4),
            })
            trade_log.append(trade)

        eq_series = pd.Series(
            {d: v for d, v in equity_curve},
            name=f"{stock_a}/{stock_b}",
        )
        trade_df = pd.DataFrame(trade_log) if trade_log else pd.DataFrame()

        return {
            "equity_curve": eq_series,
            "trade_log": trade_df,
            "pair": f"{stock_a}/{stock_b}",
            "initial_capital": capital,
        }

    def backtest_portfolio(
        self,
        selected_pairs: pd.DataFrame,
        kalman_results: dict[str, pd.DataFrame],
        signals_results: dict[str, pd.DataFrame],
        save_dir: str | None = None,
    ) -> dict:
        """Backtest multiple pairs and aggregate into portfolio-level results."""
        portfolio_equity = pd.Series(dtype=float)
        all_trade_logs: list[pd.DataFrame] = []
        pair_metrics: list[dict] = []
        open_positions: list[str] = []

        capital_per_pair = self.initial_capital * self.trade_pct

        for _, row in selected_pairs.iterrows():
            if not row.get("selected", True):
                continue

            a, b = row["stock_a"], row["stock_b"]
            pair_key = f"{a}/{b}"

            if not apply_position_limits(open_positions, self.max_open):
                logger.warning("Max open positions reached, skipping %s", pair_key)
                continue

            if pair_key not in kalman_results or pair_key not in signals_results:
                logger.warning("Missing data for pair %s, skipping", pair_key)
                continue

            kf_df = kalman_results[pair_key]
            sig_df = signals_results[pair_key]
            beta_series = kf_df["beta"]

            result = self.backtest_pair(a, b, beta_series, sig_df, capital=capital_per_pair)
            eq = result["equity_curve"]

            if portfolio_equity.empty:
                portfolio_equity = eq - capital_per_pair  # PnL contribution
            else:
                common = portfolio_equity.index.union(eq.index)
                portfolio_equity = portfolio_equity.reindex(common).ffill().fillna(0)
                pnl = (eq - capital_per_pair).reindex(common).ffill().fillna(0)
                portfolio_equity = portfolio_equity + pnl

            if not result["trade_log"].empty:
                all_trade_logs.append(result["trade_log"])

            open_positions.append(pair_key)

        # Build total portfolio equity curve starting from initial capital
        if not portfolio_equity.empty:
            portfolio_equity = self.initial_capital + portfolio_equity
            portfolio_equity = portfolio_equity.sort_index()

        # Check drawdown stop
        if not portfolio_equity.empty and check_drawdown_stop(portfolio_equity, self.max_dd_stop):
            logger.warning("Portfolio hit max drawdown stop of %.0f%%.", self.max_dd_stop * 100)

        trade_log_df = pd.concat(all_trade_logs, ignore_index=True) if all_trade_logs else pd.DataFrame()

        if save_dir:
            Path(save_dir).mkdir(parents=True, exist_ok=True)
            portfolio_equity.to_csv(f"{save_dir}/equity_curve.csv", header=["equity"])
            if not trade_log_df.empty:
                trade_log_df.to_csv(f"{save_dir}/trade_log.csv", index=False)
            logger.info("Saved portfolio results to %s", save_dir)

        return {
            "equity_curve": portfolio_equity,
            "trade_log": trade_log_df,
            "initial_capital": self.initial_capital,
        }
