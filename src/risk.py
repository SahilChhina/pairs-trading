from __future__ import annotations

import logging

import pandas as pd

logger = logging.getLogger(__name__)


def apply_position_limits(open_positions: list, max_open_positions: int) -> bool:
    """Return True if a new position can be opened (under the limit)."""
    return len(open_positions) < max_open_positions


def check_drawdown_stop(equity_curve: pd.Series, max_drawdown_stop: float) -> bool:
    """Return True if portfolio drawdown exceeds the stop threshold."""
    if len(equity_curve) < 2:
        return False
    peak = equity_curve.cummax()
    drawdown = (equity_curve - peak) / peak
    current_dd = drawdown.iloc[-1]
    return current_dd < -abs(max_drawdown_stop)


def calculate_pair_exposure(position: dict) -> dict:
    """Calculate gross and net dollar exposure for one open position."""
    long_value = position.get("long_value", 0.0)
    short_value = position.get("short_value", 0.0)
    gross = long_value + abs(short_value)
    net = long_value - abs(short_value)
    return {"gross_exposure": gross, "net_exposure": net}
