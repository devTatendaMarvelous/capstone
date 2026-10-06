"""Regression metrics. These are not classification accuracy."""

from __future__ import annotations

import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


def regression_metrics(y_true, y_pred) -> dict[str, float]:
    """MAE, RMSE, and R² for a yield prediction.

    R² is the coefficient of determination. A project target of 80% is
    interpreted as R² >= 0.80 on the held-out later seasons. It is not
    the share of rows within an error band, and it is not accuracy.
    """
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    return {
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "r2": float(r2_score(y_true, y_pred)),
    }
