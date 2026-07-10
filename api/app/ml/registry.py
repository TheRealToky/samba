"""Model registry used by the inference server.

Loads artifacts published by the training server (Phase 3) from the shared model
directory (a volume locally; the cloud analogue is pulling from object storage).
Any model family without a loaded artifact falls back to a deterministic stub so
the API always has a stable contract.

Artifact format (joblib): a dict
    {"family": str, "type": str, "estimator": <sklearn estimator or params>,
     "meta": {...}}
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from app.config import settings

_FAMILIES = ("deforestation", "sdm", "climate")


class ModelRegistry:
    def __init__(self, model_dir: str | None = None):
        self.model_dir = Path(model_dir or settings.model_dir)
        self._models: dict[str, dict[str, Any]] = {}

    def load_all(self) -> None:
        self._models.clear()
        if not self.model_dir.exists():
            return
        try:
            import joblib
        except Exception:  # pragma: no cover
            return
        for path in sorted(self.model_dir.glob("*.joblib")):
            try:
                artifact = joblib.load(path)
                family = artifact.get("family", path.stem)
                self._models[family] = artifact
            except Exception as exc:  # pragma: no cover
                print(f"[registry] failed to load {path}: {exc}", flush=True)

    def loaded_names(self) -> list[str]:
        return sorted(self._models.keys()) or ["stub"]

    def describe(self) -> list[dict]:
        out = []
        for family in _FAMILIES:
            loaded = family in self._models
            entry = {"name": family, "ready": True, "backend": "stub"}
            if loaded:
                art = self._models[family]
                entry["backend"] = art.get("meta", {}).get("backend", "sklearn")
                entry["meta"] = art.get("meta", {})
            out.append(entry)
        return out

    # --- prediction -----------------------------------------------------------
    def predict(self, family: str, features: dict) -> dict:
        if family in self._models:
            return self._predict_real(family, features)
        return self._predict_stub(family, features)

    def _predict_stub(self, family: str, features: dict) -> dict:
        return {
            "type": family,
            "confidence": 0.5,
            "prediction": {"note": "stub inference (no trained artifact loaded)", "echo": features},
            "served_by": "stub",
        }

    def _predict_real(self, family: str, features: dict) -> dict:
        art = self._models[family]
        estimator = art.get("estimator")
        meta = art.get("meta", {})
        try:
            import numpy as np

            feat_names = meta.get("features", [])
            x = np.array([[float(features.get(name, 0.0)) for name in feat_names]])
            if hasattr(estimator, "predict_proba"):
                proba = estimator.predict_proba(x)[0]
                confidence = float(proba.max())
                label = int(estimator.classes_[int(proba.argmax())])
                prediction = {"label": label, "proba": proba.tolist()}
            else:
                value = float(estimator.predict(x)[0])
                confidence = float(meta.get("confidence", 0.7))
                prediction = {"value": value}
        except Exception as exc:  # pragma: no cover
            return {
                "type": family,
                "confidence": 0.0,
                "prediction": {"error": f"inference failed: {exc}"},
                "served_by": meta.get("backend", "sklearn"),
            }
        return {
            "type": art.get("type", family),
            "confidence": confidence,
            "prediction": prediction,
            "served_by": meta.get("backend", "sklearn"),
        }
