from __future__ import annotations

"""Kalman filter for dynamic hedge ratio estimation.

State-space model:
    Observation:  A_t = beta_t * B_t + intercept_t + error_t
    State:        [beta_t, intercept_t] = [beta_{t-1}, intercept_{t-1}] + noise_t

The filter updates the hidden state [beta, intercept] as each new price arrives,
producing a time-varying hedge ratio without peeking at future data.
"""

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def kalman_filter_hedge_ratio(
    series_a: pd.Series,
    series_b: pd.Series,
    delta: float = 1e-4,
    observation_noise: float = 1e-3,
) -> pd.DataFrame:
    """Estimate dynamic beta and intercept using a Kalman filter.

    Args:
        series_a: Price series for stock A (dependent variable).
        series_b: Price series for stock B (independent variable).
        delta: Process noise scaling factor. Higher = faster adaptation.
        observation_noise: Variance of the observation noise.

    Returns:
        DataFrame with columns [beta, intercept, spread] indexed by date.
    """
    aligned = pd.concat([series_a, series_b], axis=1).dropna()
    dates = aligned.index
    a = aligned.iloc[:, 0].values
    b = aligned.iloc[:, 1].values
    n = len(a)

    # State transition: identity (random walk on [beta, intercept])
    F = np.eye(2)

    # Process noise covariance — drives how fast beta can drift
    Q = delta / (1 - delta) * np.eye(2)

    # Observation noise variance
    R = observation_noise

    # Initial state estimate and covariance
    state = np.zeros(2)          # [beta, intercept]
    P = np.ones((2, 2))          # initial uncertainty

    betas = np.empty(n)
    intercepts = np.empty(n)
    spreads = np.empty(n)

    for t in range(n):
        # Observation matrix: [B_t, 1]
        H = np.array([[b[t], 1.0]])

        # --- Predict ---
        state_pred = F @ state
        P_pred = F @ P @ F.T + Q

        # --- Update ---
        y_pred = H @ state_pred        # predicted A_t
        innovation = a[t] - y_pred[0]
        S = (H @ P_pred @ H.T)[0, 0] + R   # innovation covariance
        K = (P_pred @ H.T) / S              # Kalman gain (2x1)

        state = state_pred + K.flatten() * innovation
        P = (np.eye(2) - K @ H) @ P_pred

        betas[t] = state[0]
        intercepts[t] = state[1]
        spreads[t] = a[t] - state[0] * b[t] - state[1]

    result = pd.DataFrame(
        {"beta": betas, "intercept": intercepts, "spread": spreads},
        index=dates,
    )
    result.index.name = "date"
    logger.debug("Kalman filter complete. Beta range: [%.4f, %.4f]", betas.min(), betas.max())
    return result
