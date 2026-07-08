"""Deforestation detection via statistical change-point detection (FR-3.1).

Classical baseline using Pettitt's test — a non-parametric single change-point
test on the NDVI time series. If a significant downward shift is found, it's a
candidate deforestation event. An LSTM/CNN on raw imagery could later replace
this without changing the DeforestationEvent contract.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime

import numpy as np


@dataclass
class ChangePoint:
    index: int
    date: datetime
    p_value: float
    mean_before: float
    mean_after: float
    drop: float            # NDVI drop (mean_before - mean_after), positive = loss
    relative_loss: float   # drop / mean_before


def pettitt_test(values: np.ndarray) -> tuple[int, float]:
    """Return (change_index, p_value) for the most likely single change-point."""
    n = len(values)
    # U_t = sum_{i<=t} sum_{j>t} sgn(x_i - x_j); computed via rank differences.
    diff_sign = np.sign(values[:, None] - values[None, :])  # n x n
    # cumulative version: U_t = sum over i<=t, j>t of sign(x_i - x_j)
    csum = diff_sign.cumsum(axis=0)          # partial over i
    # For each t, sum_{i<=t} sum_{j>t}: use column cumulative from the right on j
    U = np.array([diff_sign[: t + 1, t + 1 :].sum() for t in range(n - 1)])
    if U.size == 0:
        return 0, 1.0
    k = int(np.argmax(np.abs(U)))
    K = float(np.abs(U[k]))
    p = 2.0 * math.exp((-6.0 * K * K) / (n**3 + n**2))
    return k, min(1.0, p)


def detect_change_point(
    series: list[tuple[datetime, float]],
    alpha: float = 0.05,
    min_relative_loss: float = 0.08,
) -> ChangePoint | None:
    if len(series) < 12:
        return None
    dates = [d for d, _ in series]
    values = np.array([v for _, v in series], dtype=float)
    idx, p = pettitt_test(values)
    mean_before = float(values[: idx + 1].mean())
    mean_after = float(values[idx + 1 :].mean())
    drop = mean_before - mean_after
    relative_loss = drop / mean_before if mean_before > 0 else 0.0
    if p <= alpha and relative_loss >= min_relative_loss:
        return ChangePoint(
            index=idx,
            date=dates[idx],
            p_value=round(p, 5),
            mean_before=round(mean_before, 4),
            mean_after=round(mean_after, 4),
            drop=round(drop, 4),
            relative_loss=round(relative_loss, 4),
        )
    return None
