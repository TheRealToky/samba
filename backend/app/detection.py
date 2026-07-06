"""Rule-based deforestation detector.

MVP stand-in for the future ML pipeline described in the SRS. This module is a
*pure* function over NDVI time-series (no DB, no framework) so it can be unit
tested in isolation.

Rule: for each region, an NDVI reading is a "loss point" if it has dropped by at
least `drop_threshold_pct` relative to the peak NDVI within the trailing
`window_days`. Consecutive/overlapping loss points are merged into a single
DeforestationEvent spanning the drop, with `vegetation_loss` = the largest
percentage drop observed.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Iterable


@dataclass(frozen=True)
class NDVIPoint:
    date: date
    ndvi: float


@dataclass(frozen=True)
class DetectedEvent:
    polygon_location: str
    start_date: date
    end_date: date
    vegetation_loss: float  # percent, e.g. 42.5


def severity_for_loss(loss_pct: float) -> str:
    """Map a vegetation-loss percentage to an alert severity band."""
    if loss_pct >= 65:
        return "critical"
    if loss_pct >= 45:
        return "high"
    return "moderate"


def detect_region_events(
    polygon_location: str,
    points: Iterable[NDVIPoint],
    drop_threshold_pct: float,
    window_days: int,
) -> list[DetectedEvent]:
    """Return the deforestation events detected in one region's NDVI series."""
    pts = sorted(points, key=lambda p: p.date)
    window = timedelta(days=window_days)

    # 1. Flag individual loss points against the trailing-window peak.
    loss_spans: list[tuple[date, date, float]] = []  # (baseline_date, current_date, loss_pct)
    for i, cur in enumerate(pts):
        baseline: NDVIPoint | None = None
        for prev in pts[: i + 1]:
            if cur.date - prev.date <= window:
                if baseline is None or prev.ndvi > baseline.ndvi:
                    baseline = prev
        if baseline is None or baseline.ndvi <= 0:
            continue
        loss = (baseline.ndvi - cur.ndvi) / baseline.ndvi * 100
        if loss >= drop_threshold_pct:
            loss_spans.append((baseline.date, cur.date, loss))

    # 2. Merge overlapping/adjacent spans into distinct events.
    events: list[tuple[date, date, float]] = []
    for start, end, loss in loss_spans:
        if events and start <= events[-1][1]:
            s0, e0, l0 = events[-1]
            events[-1] = (min(s0, start), max(e0, end), max(l0, loss))
        else:
            events.append((start, end, loss))

    return [
        DetectedEvent(polygon_location, s, e, round(l, 2))
        for s, e, l in events
    ]
