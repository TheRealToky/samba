"""Species distribution / biodiversity-suitability model (FR-3.2).

v1 baseline: logistic regression over environmental covariates (NDVI,
temperature, rainfall, humidity) predicting whether a region-month is
biodiversity-rich (species_richness above the dataset median). This is a
habitat-suitability proxy; per-species Maxent/RF SDMs are a later extension.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.region import Region
from app.processing.alignment import align_region

FEATURES = ["ndvi", "temperature", "rainfall", "humidity"]


@dataclass
class SDMArtifact:
    estimator: object
    meta: dict


def build_dataset(db: Session) -> tuple[np.ndarray, np.ndarray]:
    region_ids = list(db.execute(select(Region.id)).scalars().all())
    rows: list[list[float]] = []
    richness: list[int] = []
    for rid in region_ids:
        for r in align_region(db, rid):
            if None in (r.ndvi, r.temperature, r.rainfall, r.humidity):
                continue
            rows.append([r.ndvi, r.temperature, r.rainfall, r.humidity])
            richness.append(r.species_richness)
    X = np.array(rows, dtype=float)
    rich = np.array(richness, dtype=float)
    return X, rich


def train(db: Session) -> SDMArtifact | None:
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import cross_val_score
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    X, rich = build_dataset(db)
    if len(X) < 20 or rich.max() == 0:
        return None
    threshold = float(np.median(rich[rich > 0])) if (rich > 0).any() else 1.0
    y = (rich >= threshold).astype(int)
    if len(np.unique(y)) < 2:
        return None

    model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000))
    try:
        cv = cross_val_score(model, X, y, cv=min(5, int(y.sum()), int((1 - y).sum()) or 2))
        cv_acc = float(cv.mean())
    except Exception:
        cv_acc = float("nan")
    model.fit(X, y)
    meta = {
        "backend": "sklearn",
        "algorithm": "logistic_regression",
        "features": FEATURES,
        "target": f"species_richness >= {threshold}",
        "n_samples": int(len(X)),
        "positive_rate": round(float(y.mean()), 3),
        "cv_accuracy": round(cv_acc, 3) if cv_acc == cv_acc else None,
    }
    return SDMArtifact(estimator=model, meta=meta)
