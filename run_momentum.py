"""Cross-Sectional Momentum Engine — main pipeline.

Reuses the project's data_loader, metrics, and utils; implements a *cross-
sectional* long/short momentum strategy (rank the universe each month, long the
winners, short the losers) — the cross-sectional counterpart to the time-series
pairs engine in main.py.

Usage:
    python run_momentum.py --config config_momentum.yaml --download-data
    python run_momentum.py --config config_momentum.yaml --backtest
    python run_momentum.py --config config_momentum.yaml --all
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.data_loader import clean_price_data, download_price_data, load_prices, save_prices
from src.metrics import calculate_all_metrics
from src.momentum.analysis import active_return_stats, factor_stats
from src.momentum.backtest import run_equal_weight_benchmark, run_momentum_backtest
from src.momentum.universe import get_momentum_universe
from src.utils import ensure_dirs, load_config, setup_logging

logger = logging.getLogger("momentum")

DATA_RAW = "data/momentum/prices_raw.csv"
DATA_CLEAN = "data/momentum/prices_clean.csv"
RESULTS_DIR = "data/results_momentum"


def step_download(cfg: dict) -> None:
    u = cfg["universe"]
    tickers = u["tickers"] or get_momentum_universe()
    ensure_dirs("data/momentum")
    prices = download_price_data(tickers, start=u["start_date"], end=u.get("end_date"))
    save_prices(prices, DATA_RAW)
    prices = clean_price_data(prices)
    save_prices(prices, DATA_CLEAN)
    logger.info("Momentum price data ready: %d rows x %d tickers", len(prices), len(prices.columns))


def step_backtest(cfg: dict) -> None:
    sig = cfg["signal"]
    bt = cfg["backtest"]
    capital = cfg["project"]["initial_capital"]

    prices = load_prices(DATA_CLEAN)
    ensure_dirs(RESULTS_DIR)

    result = run_momentum_backtest(
        prices,
        initial_capital=capital,
        lookback_days=sig["lookback_days"],
        skip_days=sig["skip_days"],
        top_quantile=sig["top_quantile"],
        long_short=sig["long_short"],
        transaction_cost_bps=bt["transaction_cost_bps"],
        slippage_bps=bt["slippage_bps"],
        start=bt["trade_start"],
        end=bt.get("trade_end"),
    )
    equity = result["equity_curve"]

    benchmark = run_equal_weight_benchmark(
        prices, initial_capital=capital, start=bt["trade_start"], end=bt.get("trade_end")
    )

    import pandas as pd

    trade_log_df = pd.DataFrame(result["trade_log"])

    metrics = calculate_all_metrics(equity, trade_log_df)
    metrics.update(factor_stats(result["rebalance_log"]))
    metrics.update(active_return_stats(equity, benchmark))

    # Persist outputs.
    equity.to_csv(f"{RESULTS_DIR}/equity_curve.csv")
    benchmark.to_csv(f"{RESULTS_DIR}/benchmark_curve.csv")
    pd.DataFrame(result["rebalance_log"]).to_csv(f"{RESULTS_DIR}/rebalance_log.csv", index=False)
    if not trade_log_df.empty:
        trade_log_df.to_csv(f"{RESULTS_DIR}/trades.csv", index=False)
    with open(f"{RESULTS_DIR}/metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)
    with open(f"{RESULTS_DIR}/weights_history.json", "w") as f:
        json.dump(result["weights_history"], f, indent=2)

    print("\n=== Cross-Sectional Momentum — Performance ===")
    for k, v in metrics.items():
        print(f"  {k:<32} {v}")
    print(f"\nResults written to {RESULTS_DIR}/")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Cross-Sectional Momentum Engine")
    p.add_argument("--config", default="config_momentum.yaml")
    p.add_argument("--download-data", action="store_true")
    p.add_argument("--backtest", action="store_true")
    p.add_argument("--all", action="store_true")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    setup_logging()
    cfg = load_config(args.config)
    run_all = args.all or not any([args.download_data, args.backtest])
    if args.download_data or run_all:
        step_download(cfg)
    if args.backtest or run_all:
        step_backtest(cfg)


if __name__ == "__main__":
    main()
