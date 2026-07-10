"""Climate trend forecasting (FR-3, "Climate trend forecasting").

SARIMA baseline (statsmodels) over a region's monthly temperature series.
Fitting is cheap on ~36 points, so the training server pre-computes forecasts
and stores them as PredictionResults for the API to serve.
"""
from __future__ import annotations

import warnings
from dataclasses import dataclass
from datetime import datetime

import numpy as np


@dataclass
class Forecast:
    metric: str
    horizon_months: int
    points: list[dict]   # [{"period": iso, "value": float, "lower": float, "upper": float}]
    model_order: str


def sarima_forecast(
    series: list[tuple[datetime, float]],
    steps: int = 12,
    metric: str = "temperature",
) -> Forecast | None:
    values = [v for _, v in series if v is not None]
    dates = [d for d, v in series if v is not None]
    if len(values) < 24:  # need >= 2 seasonal cycles
        return None

    from statsmodels.tsa.statespace.sarimax import SARIMAX

    y = np.array(values, dtype=float)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            model = SARIMAX(y, order=(1, 1, 1), seasonal_order=(1, 1, 0, 12),
                            enforce_stationarity=False, enforce_invertibility=False)
            fit = model.fit(disp=False)
            pred = fit.get_forecast(steps=steps)
            mean = pred.predicted_mean
            ci = pred.conf_int(alpha=0.2)
        except Exception:
            return None

    last = dates[-1]
    points = []
    for i in range(steps):
        month = last.month + i + 1
        year = last.year + (month - 1) // 12
        month = (month - 1) % 12 + 1
        period = datetime(year, month, 15, tzinfo=last.tzinfo)
        points.append(
            {
                "period": period.isoformat(),
                "value": round(float(mean[i]), 3),
                "lower": round(float(ci[i][0]), 3),
                "upper": round(float(ci[i][1]), 3),
            }
        )
    return Forecast(metric=metric, horizon_months=steps, points=points, model_order="SARIMA(1,1,1)(1,1,0,12)")
