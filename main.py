"""Statistical Arbitrage Pairs Trading Engine — main pipeline.

Usage:
    python main.py --config config.yaml
    python main.py --config config.yaml --download-data
    python main.py --config config.yaml --find-pairs
    python main.py --config config.yaml --backtest
    python main.py --config config.yaml --plot-results
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

# Ensure src is importable when running from the project root
sys.path.insert(0, str(Path(__file__).parent))

from src.backtester import PairBacktester
from src.cointegration import find_cointegrated_pairs
from src.data_loader import clean_price_data, download_price_data, load_prices, save_prices
from src.kalman import kalman_filter_hedge_ratio
from src.metrics import calculate_all_metrics
from src.plots import (
    plot_drawdown,
    plot_dynamic_beta,
    plot_equity_curve,
    plot_monthly_returns_heatmap,
    plot_pair_prices,
    plot_spread_zscore,
)
from src.signals import generate_pair_signals
from src.spread import calculate_rolling_zscore, calculate_spread
from src.utils import ensure_dirs, load_config, setup_logging

logger = logging.getLogger("pairs_trading")


# ---------------------------------------------------------------------------
# Step helpers
# ---------------------------------------------------------------------------

def step_download(cfg: dict) -> None:
    """Download and clean price data, save to disk."""
    universe_cfg = cfg["universe"]
    tickers = universe_cfg["tickers"]
    start = universe_cfg["start_date"]
    end = universe_cfg.get("end_date")

    ensure_dirs("data/raw", "data/processed")
    prices = download_price_data(tickers, start=start, end=end)
    save_prices(prices, "data/raw/prices_raw.csv")

    prices = clean_price_data(prices)
    save_prices(prices, "data/processed/prices_clean.csv")
    logger.info("Price data ready: %d rows x %d tickers", len(prices), len(prices.columns))


def step_find_pairs(cfg: dict) -> None:
    """Run cointegration tests on training data and save results."""
    bt_cfg = cfg["backtest"]
    ps_cfg = cfg["pair_selection"]

    prices = load_prices("data/processed/prices_clean.csv")
    train = prices.loc[bt_cfg["train_start"]: bt_cfg["train_end"]]

    logger.info("Finding cointegrated pairs on training data: %s → %s", bt_cfg["train_start"], bt_cfg["train_end"])

    pairs_df = find_cointegrated_pairs(
        train,
        correlation_threshold=ps_cfg["correlation_threshold"],
        pvalue_threshold=ps_cfg["cointegration_pvalue_threshold"],
        min_history_days=ps_cfg["min_history_days"],
        save_path="data/results/cointegrated_pairs.csv",
    )

    selected = pairs_df[pairs_df["selected"]].head(ps_cfg["max_pairs"])
    print("\n=== Top Cointegrated Pairs ===")
    print(selected[["stock_a", "stock_b", "correlation", "coint_pvalue"]].to_string(index=False))


def step_backtest(cfg: dict) -> None:
    """Run full pipeline: Kalman filter → signals → backtest → metrics."""
    bt_cfg = cfg["backtest"]
    ps_cfg = cfg["pair_selection"]
    model_cfg = cfg["model"]
    sig_cfg = cfg["signals"]
    risk_cfg = cfg["risk"]

    prices = load_prices("data/processed/prices_clean.csv")
    train = prices.loc[bt_cfg["train_start"]: bt_cfg["train_end"]]
    test_end = bt_cfg.get("test_end")
    test = prices.loc[bt_cfg["test_start"]: test_end] if test_end else prices.loc[bt_cfg["test_start"]:]

    # Load or recompute pairs
    pairs_path = "data/results/cointegrated_pairs.csv"
    if not Path(pairs_path).exists():
        logger.info("Pair results not found — running cointegration tests first.")
        step_find_pairs(cfg)

    import pandas as pd
    pairs_df = pd.read_csv(pairs_path)
    selected = pairs_df[pairs_df["selected"]].head(ps_cfg["max_pairs"])

    if selected.empty:
        logger.error("No cointegrated pairs selected. Aborting backtest.")
        return

    logger.info("Backtesting %d pairs on test period: %s → %s", len(selected), bt_cfg["test_start"], test_end or "latest")

    kalman_results: dict = {}
    signals_results: dict = {}

    for _, row in selected.iterrows():
        a, b = row["stock_a"], row["stock_b"]
        pair_key = f"{a}/{b}"

        if a not in test.columns or b not in test.columns:
            logger.warning("Tickers %s or %s not in price data, skipping.", a, b)
            continue

        # Fit Kalman filter on full test period (dynamic — no future leakage within filter)
        kf_df = kalman_filter_hedge_ratio(test[a], test[b])
        kalman_results[pair_key] = kf_df

        # Compute spread and z-score
        spread = calculate_spread(test[a], test[b], kf_df["beta"], kf_df["intercept"])
        zscore = calculate_rolling_zscore(
            spread,
            window=model_cfg["rolling_z_window"],
            min_periods=model_cfg["min_z_window"],
        )

        # Generate signals (already shifted +1 day inside the function)
        sig_df = generate_pair_signals(
            zscore,
            entry_threshold=sig_cfg["entry_threshold"],
            exit_threshold=sig_cfg["exit_threshold"],
            stop_loss_threshold=sig_cfg["stop_loss_threshold"],
            max_holding_days=sig_cfg["max_holding_days"],
        )
        signals_results[pair_key] = sig_df
        logger.info("Pair %s: %d trade signals generated.", pair_key, sig_df["entry_signal"].sum())

    backtester = PairBacktester(
        prices=test,
        initial_capital=cfg["project"]["initial_capital"],
        transaction_cost_bps=bt_cfg["transaction_cost_bps"],
        slippage_bps=bt_cfg["slippage_bps"],
        capital_per_trade_pct=bt_cfg["capital_per_trade_pct"],
        max_open_positions=risk_cfg["max_open_positions"],
        max_portfolio_drawdown_stop=risk_cfg["max_portfolio_drawdown_stop"],
    )

    portfolio = backtester.backtest_portfolio(
        selected_pairs=selected,
        kalman_results=kalman_results,
        signals_results=signals_results,
        save_dir="data/results",
    )

    eq = portfolio["equity_curve"]
    tl = portfolio["trade_log"]
    m = calculate_all_metrics(eq, tl)

    # Save metrics
    import json
    with open("data/results/metrics.json", "w") as f:
        json.dump(m, f, indent=2)

    print("\n=== Portfolio Performance ===")
    for k, v in m.items():
        print(f"  {k:<35} {v}")


def step_plot(cfg: dict) -> None:
    """Generate all plots from saved results."""
    import pandas as pd

    bt_cfg = cfg["backtest"]
    ps_cfg = cfg["pair_selection"]
    model_cfg = cfg["model"]
    sig_cfg = cfg["signals"]

    prices = load_prices("data/processed/prices_clean.csv")
    test_end = bt_cfg.get("test_end")
    test = prices.loc[bt_cfg["test_start"]: test_end] if test_end else prices.loc[bt_cfg["test_start"]:]

    pairs_path = "data/results/cointegrated_pairs.csv"
    if not Path(pairs_path).exists():
        logger.error("Run --find-pairs first.")
        return

    pairs_df = pd.read_csv(pairs_path)
    selected = pairs_df[pairs_df["selected"]].head(ps_cfg["max_pairs"])
    fig_dir = "data/results/figures"

    for _, row in selected.iterrows():
        a, b = row["stock_a"], row["stock_b"]
        if a not in test.columns or b not in test.columns:
            continue

        slug = f"{a}_{b}"
        plot_pair_prices(test[a], test[b], a, b, f"{fig_dir}/{slug}_prices.png")

        kf_df = kalman_filter_hedge_ratio(test[a], test[b])
        plot_dynamic_beta(kf_df["beta"], a, b, f"{fig_dir}/{slug}_beta.png")

        from src.spread import calculate_spread, calculate_rolling_zscore
        spread = calculate_spread(test[a], test[b], kf_df["beta"], kf_df["intercept"])
        zscore = calculate_rolling_zscore(spread, window=model_cfg["rolling_z_window"])
        sig_df = generate_pair_signals(
            zscore,
            entry_threshold=sig_cfg["entry_threshold"],
            exit_threshold=sig_cfg["exit_threshold"],
            stop_loss_threshold=sig_cfg["stop_loss_threshold"],
            max_holding_days=sig_cfg["max_holding_days"],
        )
        plot_spread_zscore(
            zscore, sig_df, a, b,
            entry_threshold=sig_cfg["entry_threshold"],
            exit_threshold=sig_cfg["exit_threshold"],
            stop_loss_threshold=sig_cfg["stop_loss_threshold"],
            save_path=f"{fig_dir}/{slug}_zscore.png",
        )

    eq_path = "data/results/equity_curve.csv"
    if Path(eq_path).exists():
        eq = pd.read_csv(eq_path, index_col=0, parse_dates=True).squeeze()
        plot_equity_curve(eq, "Portfolio Equity Curve", f"{fig_dir}/portfolio_equity.png")
        plot_drawdown(eq, "Portfolio Drawdown", f"{fig_dir}/portfolio_drawdown.png")
        plot_monthly_returns_heatmap(eq, f"{fig_dir}/monthly_returns_heatmap.png")

    logger.info("All plots saved to %s", fig_dir)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Statistical Arbitrage Pairs Trading Engine")
    parser.add_argument("--config", default="config.yaml", help="Path to config file")
    parser.add_argument("--download-data", action="store_true", help="Download price data")
    parser.add_argument("--find-pairs", action="store_true", help="Run cointegration tests")
    parser.add_argument("--backtest", action="store_true", help="Run backtest")
    parser.add_argument("--plot-results", action="store_true", help="Generate plots")
    parser.add_argument("--all", action="store_true", help="Run full pipeline (download → pairs → backtest → plot)")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    setup_logging()
    cfg = load_config(args.config)

    run_all = args.all or not any([args.download_data, args.find_pairs, args.backtest, args.plot_results])

    if args.download_data or run_all:
        step_download(cfg)

    if args.find_pairs or run_all:
        step_find_pairs(cfg)

    if args.backtest or run_all:
        step_backtest(cfg)

    if args.plot_results or run_all:
        step_plot(cfg)


if __name__ == "__main__":
    main()
