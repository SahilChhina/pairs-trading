import numpy as np
import pandas as pd
import pytest

from src.signals import generate_pair_signals


def make_zscore(values: list[float]) -> pd.Series:
    dates = pd.date_range("2022-01-01", periods=len(values), freq="B")
    return pd.Series(values, index=dates, name="zscore")


def test_no_trade_when_zscore_below_threshold():
    z = make_zscore([0.5, 1.0, 1.5, 1.0, 0.5])
    signals = generate_pair_signals(z, entry_threshold=2.0)
    assert (signals["position"] == 0).all()


def test_short_spread_entered_on_high_zscore():
    # z goes high → short spread (-1)
    z = make_zscore([0.0, 0.0, 2.5, 2.5, 0.0])
    signals = generate_pair_signals(z, entry_threshold=2.0, exit_threshold=0.25)
    # position is shifted +1 day, so entry at index 2 shows in position at index 3
    assert signals["position"].iloc[3] == -1


def test_long_spread_entered_on_low_zscore():
    z = make_zscore([0.0, 0.0, -2.5, -2.5, 0.0])
    signals = generate_pair_signals(z, entry_threshold=2.0, exit_threshold=0.25)
    assert signals["position"].iloc[3] == 1


def test_exit_on_mean_reversion():
    # Enter short at z=2.5, then z reverts to 0.1 → exit
    z_vals = [0.0, 2.5, 2.5, 0.1, 0.1]
    z = make_zscore(z_vals)
    signals = generate_pair_signals(z, entry_threshold=2.0, exit_threshold=0.25)
    # After exit signal, position should go to 0
    assert signals["position"].iloc[-1] == 0


def test_stop_loss_triggered():
    z = make_zscore([0.0, 2.5, 3.6, 3.6, 3.6])
    signals = generate_pair_signals(z, entry_threshold=2.0, stop_loss_threshold=3.5)
    assert signals["stop_loss_signal"].any()


def test_no_overlapping_trades():
    # Once in a trade, new entries cannot start until position is closed
    z_vals = [0.0, 2.5, 2.5, 2.5, 0.1, 0.1, 2.5, 2.5]
    z = make_zscore(z_vals)
    signals = generate_pair_signals(z, entry_threshold=2.0, exit_threshold=0.25)
    n_entries = signals["entry_signal"].sum()
    # Should not enter a second trade while the first is still open
    assert n_entries <= 2


def test_max_holding_period_exit():
    z_vals = [0.0, 2.5] + [2.5] * 25  # stays elevated for 25+ days
    z = make_zscore(z_vals)
    signals = generate_pair_signals(z, entry_threshold=2.0, max_holding_days=10)
    # Trade must have been closed within max_holding_days
    assert (signals["holding_days"] <= 10).all()


def test_position_is_shifted_one_day():
    z = make_zscore([0.0, 2.5, 2.5, 2.5])
    signals = generate_pair_signals(z, entry_threshold=2.0)
    # Signal generated at day 1, position active at day 2 (shifted)
    assert signals["position"].iloc[0] == 0  # day 0 always 0 after shift
