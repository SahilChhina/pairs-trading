from __future__ import annotations

"""Signal generation from spread z-scores.

Position encoding:
    1  = long spread  (long A, short B)
   -1  = short spread (short A, long B)
    0  = no position

Signals are shifted by one day before backtesting to avoid look-ahead bias.
"""

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def generate_pair_signals(
    zscore: pd.Series,
    entry_threshold: float = 2.0,
    exit_threshold: float = 0.25,
    stop_loss_threshold: float = 3.5,
    max_holding_days: int = 20,
) -> pd.DataFrame:
    """Convert z-scores into long/short/flat position signals.

    Returns a DataFrame with position and diagnostic columns.
    The returned 'position' column is already shifted one day forward
    (signal on day t executes at day t+1 close).
    """
    dates = zscore.index
    n = len(dates)

    position = np.zeros(n, dtype=int)
    entry_signal = np.zeros(n, dtype=bool)
    exit_signal = np.zeros(n, dtype=bool)
    stop_loss_signal = np.zeros(n, dtype=bool)
    holding_days_arr = np.zeros(n, dtype=int)
    trade_id_arr = np.full(n, -1, dtype=int)
    exit_reason_arr = np.empty(n, dtype=object)
    exit_reason_arr[:] = ""

    current_position = 0
    holding_days = 0
    trade_counter = 0
    current_trade_id = -1

    z = zscore.values

    for t in range(n):
        if np.isnan(z[t]):
            position[t] = 0
            continue

        if current_position == 0:
            # Check for entry
            if z[t] > entry_threshold:
                current_position = -1   # short spread
                holding_days = 1
                trade_counter += 1
                current_trade_id = trade_counter
                entry_signal[t] = True
            elif z[t] < -entry_threshold:
                current_position = 1    # long spread
                holding_days = 1
                trade_counter += 1
                current_trade_id = trade_counter
                entry_signal[t] = True
        else:
            holding_days += 1
            # Check exit conditions (in priority order)
            if abs(z[t]) > stop_loss_threshold:
                stop_loss_signal[t] = True
                exit_signal[t] = True
                exit_reason_arr[t] = "stop_loss"
                current_position = 0
                holding_days = 0
                current_trade_id = -1
            elif abs(z[t]) < exit_threshold:
                exit_signal[t] = True
                exit_reason_arr[t] = "mean_reversion"
                current_position = 0
                holding_days = 0
                current_trade_id = -1
            elif holding_days >= max_holding_days:
                exit_signal[t] = True
                exit_reason_arr[t] = "max_holding"
                current_position = 0
                holding_days = 0
                current_trade_id = -1

        position[t] = current_position
        holding_days_arr[t] = holding_days if current_position != 0 else 0
        trade_id_arr[t] = current_trade_id

    result = pd.DataFrame(
        {
            "zscore": z,
            "position_raw": position,        # same-day signal
            "position": np.roll(position, 1), # shifted: execute next day
            "entry_signal": entry_signal,
            "exit_signal": exit_signal,
            "stop_loss_signal": stop_loss_signal,
            "holding_days": holding_days_arr,
            "trade_id": trade_id_arr,
            "exit_reason": exit_reason_arr,
        },
        index=dates,
    )
    # Day 0 position after shift is meaningless
    result.loc[result.index[0], "position"] = 0

    n_trades = result["entry_signal"].sum()
    logger.debug("Signal generation complete. %d trades entered.", n_trades)
    return result
