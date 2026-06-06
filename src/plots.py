from __future__ import annotations

import logging
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

STYLE = {
    "figure.facecolor": "white",
    "axes.facecolor": "#f8f9fa",
    "axes.grid": True,
    "grid.alpha": 0.4,
    "axes.spines.top": False,
    "axes.spines.right": False,
}


def _save(fig: plt.Figure, path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Saved plot: %s", path)


def plot_pair_prices(
    series_a: pd.Series,
    series_b: pd.Series,
    ticker_a: str,
    ticker_b: str,
    save_path: str,
) -> None:
    with plt.rc_context(STYLE):
        fig, ax1 = plt.subplots(figsize=(12, 4))
        ax2 = ax1.twinx()

        ax1.plot(series_a.index, series_a.values, color="#1f77b4", label=ticker_a)
        ax2.plot(series_b.index, series_b.values, color="#ff7f0e", label=ticker_b, alpha=0.8)

        ax1.set_ylabel(ticker_a, color="#1f77b4")
        ax2.set_ylabel(ticker_b, color="#ff7f0e")
        ax1.set_xlabel("Date")
        fig.suptitle(f"Price Series: {ticker_a} vs {ticker_b}", fontsize=13, fontweight="bold")
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left")
        _save(fig, save_path)


def plot_dynamic_beta(beta: pd.Series, ticker_a: str, ticker_b: str, save_path: str) -> None:
    with plt.rc_context(STYLE):
        fig, ax = plt.subplots(figsize=(12, 4))
        ax.plot(beta.index, beta.values, color="#2ca02c", linewidth=1.2)
        ax.axhline(beta.mean(), color="grey", linestyle="--", linewidth=0.8, label=f"Mean β = {beta.mean():.3f}")
        ax.set_title(f"Dynamic Hedge Ratio (Kalman Filter): {ticker_a} / {ticker_b}", fontsize=13, fontweight="bold")
        ax.set_ylabel("β (hedge ratio)")
        ax.set_xlabel("Date")
        ax.legend()
        _save(fig, save_path)


def plot_spread_zscore(
    zscore: pd.Series,
    signals: pd.DataFrame,
    ticker_a: str,
    ticker_b: str,
    entry_threshold: float = 2.0,
    exit_threshold: float = 0.25,
    stop_loss_threshold: float = 3.5,
    save_path: str = "",
) -> None:
    with plt.rc_context(STYLE):
        fig, ax = plt.subplots(figsize=(14, 5))
        ax.plot(zscore.index, zscore.values, color="#1f77b4", linewidth=0.9, label="Z-score")

        ax.axhline(entry_threshold, color="#d62728", linestyle="--", linewidth=0.9, label=f"Entry ±{entry_threshold}")
        ax.axhline(-entry_threshold, color="#d62728", linestyle="--", linewidth=0.9)
        ax.axhline(exit_threshold, color="#2ca02c", linestyle=":", linewidth=0.8, label=f"Exit ±{exit_threshold}")
        ax.axhline(-exit_threshold, color="#2ca02c", linestyle=":", linewidth=0.8)
        ax.axhline(stop_loss_threshold, color="#8c564b", linestyle="-.", linewidth=0.8, label=f"Stop ±{stop_loss_threshold}")
        ax.axhline(-stop_loss_threshold, color="#8c564b", linestyle="-.", linewidth=0.8)
        ax.axhline(0, color="black", linewidth=0.6)

        # Mark entry/exit signals
        entries = signals[signals["entry_signal"]]
        exits = signals[signals["exit_signal"]]
        ax.scatter(entries.index, zscore.reindex(entries.index), marker="^", color="green", zorder=5, s=50, label="Entry")
        ax.scatter(exits.index, zscore.reindex(exits.index), marker="v", color="red", zorder=5, s=50, label="Exit")

        ax.set_title(f"Spread Z-Score with Signals: {ticker_a} / {ticker_b}", fontsize=13, fontweight="bold")
        ax.set_ylabel("Z-score")
        ax.set_xlabel("Date")
        ax.legend(loc="upper right", fontsize=8)
        _save(fig, save_path)


def plot_equity_curve(equity_curve: pd.Series, title: str, save_path: str) -> None:
    with plt.rc_context(STYLE):
        fig, ax = plt.subplots(figsize=(12, 4))
        ax.plot(equity_curve.index, equity_curve.values, color="#1f77b4", linewidth=1.5)
        ax.axhline(equity_curve.iloc[0], color="grey", linestyle="--", linewidth=0.8, label="Initial capital")
        ax.fill_between(
            equity_curve.index,
            equity_curve.iloc[0],
            equity_curve.values,
            where=equity_curve.values >= equity_curve.iloc[0],
            alpha=0.2,
            color="green",
        )
        ax.fill_between(
            equity_curve.index,
            equity_curve.iloc[0],
            equity_curve.values,
            where=equity_curve.values < equity_curve.iloc[0],
            alpha=0.2,
            color="red",
        )
        ax.set_title(title, fontsize=13, fontweight="bold")
        ax.set_ylabel("Portfolio Value ($)")
        ax.set_xlabel("Date")
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"${x:,.0f}"))
        ax.legend()
        _save(fig, save_path)


def plot_drawdown(equity_curve: pd.Series, title: str, save_path: str) -> None:
    with plt.rc_context(STYLE):
        peak = equity_curve.cummax()
        drawdown = (equity_curve - peak) / peak * 100

        fig, ax = plt.subplots(figsize=(12, 3))
        ax.fill_between(drawdown.index, drawdown.values, 0, alpha=0.6, color="#d62728")
        ax.plot(drawdown.index, drawdown.values, color="#d62728", linewidth=0.8)
        ax.set_title(title, fontsize=13, fontweight="bold")
        ax.set_ylabel("Drawdown (%)")
        ax.set_xlabel("Date")
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:.1f}%"))
        _save(fig, save_path)


def plot_monthly_returns_heatmap(equity_curve: pd.Series, save_path: str) -> None:
    try:
        import seaborn as sns
    except ImportError:
        logger.warning("seaborn not installed — skipping monthly returns heatmap")
        return

    returns = equity_curve.pct_change().dropna()
    monthly = returns.resample("ME").apply(lambda r: (1 + r).prod() - 1) * 100

    pivot = monthly.to_frame("return")
    pivot["year"] = pivot.index.year
    pivot["month"] = pivot.index.month
    heatmap_data = pivot.pivot(index="year", columns="month", values="return")
    heatmap_data.columns = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                             "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][: len(heatmap_data.columns)]

    with plt.rc_context({"figure.facecolor": "white"}):
        fig, ax = plt.subplots(figsize=(14, max(3, len(heatmap_data) * 0.6)))
        sns.heatmap(
            heatmap_data,
            annot=True,
            fmt=".1f",
            cmap="RdYlGn",
            center=0,
            linewidths=0.5,
            ax=ax,
            cbar_kws={"label": "Return (%)"},
        )
        ax.set_title("Monthly Returns Heatmap (%)", fontsize=13, fontweight="bold")
        _save(fig, save_path)
