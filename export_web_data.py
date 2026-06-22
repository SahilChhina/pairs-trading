"""Bundle backtest results into a single JSON the React dashboard consumes.

Reads from data/results/ and writes web/public/data/results.json,
copying any generated figures into web/public/figures/.

Usage:
    python3 export_web_data.py
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path

import pandas as pd

RESULTS_DIR = Path("data/results")
MOMENTUM_DIR = Path("data/results_momentum")
FIG_SRC = RESULTS_DIR / "figures"
WEB_DATA_DIR = Path("web/public/data")
WEB_FIG_DIR = Path("web/public/figures")


def _load_metrics() -> dict:
    path = RESULTS_DIR / "metrics.json"
    if path.exists():
        return json.loads(path.read_text())
    return {}


def _load_equity_curve() -> list[dict]:
    path = RESULTS_DIR / "equity_curve.csv"
    if not path.exists():
        return []
    df = pd.read_csv(path, index_col=0, parse_dates=True)
    col = df.columns[0]
    series = df[col]

    peak = series.cummax()
    drawdown = (series - peak) / peak * 100

    out = []
    for date, equity in series.items():
        out.append({
            "date": pd.Timestamp(date).strftime("%Y-%m-%d"),
            "equity": round(float(equity), 2),
            "drawdown": round(float(drawdown.loc[date]), 3),
        })
    return out


def _load_pairs() -> list[dict]:
    path = RESULTS_DIR / "cointegrated_pairs.csv"
    if not path.exists():
        return []
    df = pd.read_csv(path)
    return df.to_dict(orient="records")


def _load_trades() -> list[dict]:
    path = RESULTS_DIR / "trade_log.csv"
    if not path.exists():
        return []
    df = pd.read_csv(path)
    # Normalize date columns to strings
    for col in ("entry_date", "exit_date"):
        if col in df.columns:
            df[col] = pd.to_datetime(df[col]).dt.strftime("%Y-%m-%d")
    return df.to_dict(orient="records")


def _copy_figures() -> list[dict]:
    if not FIG_SRC.exists():
        return []
    WEB_FIG_DIR.mkdir(parents=True, exist_ok=True)
    figures = []
    for png in sorted(FIG_SRC.glob("*.png")):
        shutil.copy(png, WEB_FIG_DIR / png.name)
        figures.append({"name": png.stem, "file": f"figures/{png.name}"})
    return figures


def _load_momentum_metrics() -> dict:
    path = MOMENTUM_DIR / "metrics.json"
    if path.exists():
        return json.loads(path.read_text())
    return {}


def _load_momentum_equity() -> list[dict]:
    path = MOMENTUM_DIR / "equity_curve.csv"
    if not path.exists():
        return []
    df = pd.read_csv(path, index_col=0, parse_dates=True)
    col = df.columns[0]
    series = df[col]
    peak = series.cummax()
    drawdown = (series - peak) / peak * 100
    out = []
    for date, equity in series.items():
        out.append({
            "date": pd.Timestamp(date).strftime("%Y-%m-%d"),
            "equity": round(float(equity), 2),
            "drawdown": round(float(drawdown.loc[date]), 3),
        })
    return out


def _load_momentum_trades() -> list[dict]:
    path = MOMENTUM_DIR / "trades.csv"
    if not path.exists():
        return []
    df = pd.read_csv(path)
    for col in ("entry_date", "exit_date"):
        if col in df.columns:
            df[col] = pd.to_datetime(df[col]).dt.strftime("%Y-%m-%d")
    return df.to_dict(orient="records")


def _load_monte_carlo() -> dict:
    path = MOMENTUM_DIR / "monte_carlo.json"
    if path.exists():
        return json.loads(path.read_text())
    return {}


def main() -> None:
    WEB_DATA_DIR.mkdir(parents=True, exist_ok=True)

    mom_metrics = _load_momentum_metrics()
    mom_equity = _load_momentum_equity()
    mom_trades = _load_momentum_trades()

    payload = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "project_name": "Statistical Arbitrage Pairs Trading Engine",
        "metrics": _load_metrics(),
        "equity_curve": _load_equity_curve(),
        "pairs": _load_pairs(),
        "trades": _load_trades(),
        "figures": _copy_figures(),
        "momentum": {
            "metrics": mom_metrics,
            "equity_curve": mom_equity,
            "trades": mom_trades,
            "monte_carlo": _load_monte_carlo(),
        },
    }

    out_path = WEB_DATA_DIR / "results.json"
    out_path.write_text(json.dumps(payload, indent=2))

    print(f"Wrote {out_path}")
    print(f"  metrics:           {len(payload['metrics'])} fields")
    print(f"  equity_curve:      {len(payload['equity_curve'])} points")
    print(f"  pairs:             {len(payload['pairs'])} rows")
    print(f"  trades:            {len(payload['trades'])} rows")
    print(f"  figures:           {len(payload['figures'])} images")
    print(f"  momentum.metrics:  {len(mom_metrics)} fields")
    print(f"  momentum.equity:   {len(mom_equity)} points")
    print(f"  momentum.trades:   {len(mom_trades)} rows")
    print(f"  monte_carlo:       {'present' if _load_monte_carlo() else 'missing'}")


if __name__ == "__main__":
    main()
