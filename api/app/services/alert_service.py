"""Environmental alert generation + notification (FR-7).

Alerts are derived from ML outputs:
  - FR-7.1 Deforestation alerts: one per DeforestationEvent, severity by NDVI loss.
  - FR-7.2 Biodiversity risk alerts: endangered (CR/EN) species observed in a
    region that also has a detected deforestation event.

EnvironmentalAlert.notify() marks alerts as delivered (email is stubbed — SMTP
isn't configured in dev; the dashboard alert feed is the primary channel).
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.alert import EnvironmentalAlert
from app.models.ml import DeforestationEvent, PredictionResult
from app.models.region import Region
from app.models.species import Species, SpeciesObservation

_ENDANGERED = {"CR", "EN"}


def _severity_from_loss(loss: float) -> str:
    if loss >= 0.15:
        return "high"
    if loss >= 0.08:
        return "medium"
    return "low"


class AlertService:
    def __init__(self, db: Session):
        self.db = db

    def generate(self, clear_existing: bool = True) -> dict:
        if clear_existing:
            self.db.query(EnvironmentalAlert).delete()
            self.db.commit()
        n_defor = self._generate_deforestation()
        n_bio = self._generate_biodiversity()
        self.db.commit()
        return {"deforestation_alerts": n_defor, "biodiversity_alerts": n_bio}

    def _generate_deforestation(self) -> int:
        count = 0
        regions = {r.id: r for r in self.db.execute(select(Region)).scalars().all()}
        events = self.db.execute(select(DeforestationEvent)).scalars().all()
        for ev in events:
            region = regions.get(ev.region_id)
            region_name = region.name if region else "unknown region"
            pred = self.db.execute(
                select(PredictionResult)
                .where(PredictionResult.region_id == ev.region_id)
                .where(PredictionResult.type == "deforestation")
            ).scalars().first()
            severity = _severity_from_loss(ev.vegetation_loss)
            self.db.add(
                EnvironmentalAlert(
                    alert_type="deforestation",
                    severity=severity,
                    message=(
                        f"Deforestation detected in {region_name}: NDVI dropped by "
                        f"{ev.vegetation_loss:.3f} since {ev.start_date.date()}."
                    ),
                    region_id=ev.region_id,
                    prediction_id=pred.id if pred else None,
                )
            )
            count += 1
        return count

    def _generate_biodiversity(self) -> int:
        # regions with a deforestation event
        at_risk_regions = set(
            self.db.execute(select(DeforestationEvent.region_id)).scalars().all()
        )
        count = 0
        for region_id in at_risk_regions:
            if region_id is None:
                continue
            region = self.db.get(Region, region_id)
            endangered = self.db.execute(
                select(Species.scientific_name, Species.conservation_status)
                .join(SpeciesObservation, SpeciesObservation.species_id == Species.id)
                .where(SpeciesObservation.region_id == region_id)
                .where(Species.conservation_status.in_(_ENDANGERED))
                .distinct()
            ).all()
            if not endangered:
                continue
            names = ", ".join(sorted({n for n, _ in endangered}))
            self.db.add(
                EnvironmentalAlert(
                    alert_type="biodiversity",
                    severity="high",
                    message=(
                        f"Biodiversity risk in {region.name if region else region_id}: "
                        f"{len(endangered)} endangered species in a deforestation zone ({names})."
                    ),
                    region_id=region_id,
                )
            )
            count += 1
        return count

    # EnvironmentalAlert.notify()
    def notify_pending(self) -> int:
        pending = self.db.execute(
            select(EnvironmentalAlert).where(EnvironmentalAlert.notified.is_(False))
        ).scalars().all()
        for alert in pending:
            self._notify_one(alert)
            alert.notified = True
        self.db.commit()
        return len(pending)

    def _notify_one(self, alert: EnvironmentalAlert) -> None:
        # Dashboard feed is the delivery channel; email would go here (stubbed).
        print(f"[alert:{alert.severity}] {alert.message}", flush=True)
