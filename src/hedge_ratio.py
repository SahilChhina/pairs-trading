from __future__ import annotations

import logging

import numpy as np
import pandas as pd
from statsmodels.regression.linear_model import OLS
from statsmodels.tools import add_constant

logger = logging.getLogger(__name__)


def estimate_static_hedge_ratio(
    series_a: pd.Series,
    series_b: pd.Series,
) -> dict:
    """Estimate static hedge ratio via OLS: A = alpha + beta * B + error.

    Returns beta (hedge ratio), alpha (intercept), residuals, and R-squared.
    Uses only the data passed in — caller is responsible for train/test split.
    """
    aligned = pd.concat([series_a, series_b], axis=1).dropna()
    y = aligned.iloc[:, 0].values
    x = add_constant(aligned.iloc[:, 1].values)

    model = OLS(y, x).fit()
    alpha = float(model.params[0])
    beta = float(model.params[1])

    residuals = pd.Series(model.resid, index=aligned.index, name="residuals")

    logger.debug("Static hedge ratio: alpha=%.4f, beta=%.4f, R2=%.4f", alpha, beta, model.rsquared)

    return {
        "alpha": alpha,
        "beta": beta,
        "residuals": residuals,
        "r_squared": float(model.rsquared),
    }
