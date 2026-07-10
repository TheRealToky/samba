"""Training server entrypoint (deployment diagram: ML Training Server GPU).

Run on demand:
    docker compose --profile training run --rm training

Trains/produces all three baselines, decoupled from inference:
  - deforestation: change-point detection -> DeforestationEvent + PredictionResult
  - sdm: logistic regression -> sdm.joblib artifact (inference loads it)
  - climate: SARIMA forecast per region -> PredictionResult(type=climate_forecast)

Idempotent: clears prior ML outputs at the start so re-runs don't accumulate.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.geo.madagascar import bbox_polygon_wkt, REGIONS
from app.ml import sdm as sdm_module
from app.ml.changepoint import detect_change_point
from app.ml.forecast import sarima_forecast
from app.ml.storage import save_artifact
from app.models.ml import DeforestationEvent, MLModel, PredictionResult
from app.models.region import Region
from app.processing.alignment import align_region, ndvi_series
from geoalchemy2.elements import WKTElement


def _reset(db: Session) -> None:
    db.execute(delete(PredictionResult))
    db.execute(delete(DeforestationEvent))
    db.execute(delete(MLModel))
    db.commit()


def _register_model(db: Session, name: str, hyperparameters: dict) -> MLModel:
    model = MLModel(name=name, hyperparameters=hyperparameters)
    db.add(model)
    db.flush()
    return model


def _bbox_for(region: Region):
    for r in REGIONS:
        if r["code"] == region.code:
            return r["bbox"]
    return None


def run_deforestation(db: Session, model: MLModel) -> int:
    count = 0
    regions = list(db.execute(select(Region)).scalars().all())
    for region in regions:
        series = ndvi_series(db, region.id)
        cp = detect_change_point(series)
        if cp is None:
            continue
        bbox = _bbox_for(region)
        geom = WKTElement(bbox_polygon_wkt(tuple(bbox)), srid=4326) if bbox else None
        event = DeforestationEvent(
            location=geom,
            vegetation_loss=cp.drop,
            start_date=cp.date,
            end_date=series[-1][0],
            ml_model_id=model.id,
            region_id=region.id,
        )
        db.add(event)
        db.add(
            PredictionResult(
                type="deforestation",
                confidence=round(1.0 - cp.p_value, 4),
                date=datetime.now(timezone.utc),
                region_id=region.id,
                ml_model_id=model.id,
                payload={
                    "change_date": cp.date.isoformat(),
                    "vegetation_loss": cp.drop,
                    "relative_loss": cp.relative_loss,
                    "mean_before": cp.mean_before,
                    "mean_after": cp.mean_after,
                    "p_value": cp.p_value,
                    "region_code": region.code,
                },
            )
        )
        count += 1
        print(f"[train] deforestation @ {region.code}: loss={cp.drop} p={cp.p_value}", flush=True)
    db.commit()
    return count


def run_sdm(db: Session, model: MLModel) -> bool:
    artifact = sdm_module.train(db)
    if artifact is None:
        print("[train] SDM: not enough data to train", flush=True)
        return False
    save_artifact("sdm", {"family": "sdm", "type": "sdm", "estimator": artifact.estimator, "meta": artifact.meta})
    model.hyperparameters = artifact.meta
    db.commit()
    print(f"[train] SDM trained: {artifact.meta}", flush=True)
    return True


def run_climate(db: Session, model: MLModel) -> int:
    count = 0
    regions = list(db.execute(select(Region)).scalars().all())
    for region in regions:
        rows = align_region(db, region.id)
        series = [(r.period, r.temperature) for r in rows if r.temperature is not None]
        fc = sarima_forecast(series, steps=12, metric="temperature")
        if fc is None:
            continue
        db.add(
            PredictionResult(
                type="climate_forecast",
                confidence=0.7,
                date=datetime.now(timezone.utc),
                region_id=region.id,
                ml_model_id=model.id,
                payload={
                    "metric": fc.metric,
                    "horizon_months": fc.horizon_months,
                    "model_order": fc.model_order,
                    "points": fc.points,
                    "region_code": region.code,
                },
            )
        )
        count += 1
        print(f"[train] climate forecast @ {region.code}: {len(fc.points)} months", flush=True)
    db.commit()
    return count


def main() -> None:
    with SessionLocal() as db:
        print("[train] resetting prior ML outputs...", flush=True)
        _reset(db)
        m_defor = _register_model(db, "deforestation-cpd", {"method": "pettitt", "alpha": 0.05, "min_relative_loss": 0.08})
        m_sdm = _register_model(db, "sdm-logreg", {"algorithm": "logistic_regression"})
        m_clim = _register_model(db, "climate-sarima", {"order": "(1,1,1)", "seasonal": "(1,1,0,12)"})
        db.commit()

        n_defor = run_deforestation(db, m_defor)
        ok_sdm = run_sdm(db, m_sdm)
        n_clim = run_climate(db, m_clim)

        # FR-7: generate + deliver alerts from the fresh ML outputs.
        from app.services.alert_service import AlertService

        alert_svc = AlertService(db)
        alerts = alert_svc.generate(clear_existing=True)
        notified = alert_svc.notify_pending()

    print(
        f"[train] done. deforestation_events={n_defor} sdm_trained={ok_sdm} "
        f"climate_forecasts={n_clim} alerts={alerts} notified={notified}",
        flush=True,
    )


if __name__ == "__main__":
    main()
