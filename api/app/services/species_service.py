"""Species services.

Implements SpeciesObservation.record() (single upload — the "upload species
photo" use case) and Species.updateStatus(), plus distribution queries used by
the dashboard and SDM.
"""
from __future__ import annotations

from datetime import datetime, timezone

from geoalchemy2.elements import WKTElement
from geoalchemy2.functions import ST_AsGeoJSON, ST_Contains, ST_X, ST_Y
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.ml import DeforestationEvent
from app.models.region import Region
from app.models.species import Species, SpeciesObservation

# IUCN Red List category ordering + a 0..1 concern weight used to rank risk.
_STATUS_ORDER = ["CR", "EN", "VU", "NT", "LC", "DD", None]
_STATUS_WEIGHT = {"CR": 1.0, "EN": 0.8, "VU": 0.6, "NT": 0.4, "LC": 0.15, "DD": 0.3}


def _status_rank(status: str | None) -> int:
    try:
        return _STATUS_ORDER.index(status)
    except ValueError:
        return len(_STATUS_ORDER)


class SpeciesService:
    def __init__(self, db: Session):
        self.db = db

    # Species.updateStatus()
    def update_status(self, species_id: int, conservation_status: str) -> Species | None:
        species = self.db.get(Species, species_id)
        if species is None:
            return None
        species.conservation_status = conservation_status
        self.db.commit()
        self.db.refresh(species)
        return species

    def get_or_create(self, scientific_name: str, conservation_status: str | None = None, endemic: bool = False) -> Species:
        species = self.db.execute(
            select(Species).where(Species.scientific_name == scientific_name)
        ).scalar_one_or_none()
        if species is None:
            species = Species(
                scientific_name=scientific_name, conservation_status=conservation_status, endemic=endemic
            )
            self.db.add(species)
            self.db.commit()
            self.db.refresh(species)
        return species

    # SpeciesObservation.record()
    def record(self, scientific_name: str, lon: float, lat: float, source: str = "upload", date: datetime | None = None) -> SpeciesObservation:
        species = self.get_or_create(scientific_name)
        region_id = self._region_for_point(lon, lat)
        obs = SpeciesObservation(
            species_id=species.id,
            location=WKTElement(f"POINT({lon} {lat})", srid=4326),
            date=date or datetime.now(timezone.utc),
            source=source,
            region_id=region_id,
        )
        self.db.add(obs)
        self.db.commit()
        self.db.refresh(obs)
        return obs

    def _region_for_point(self, lon: float, lat: float) -> int | None:
        return self.db.execute(
            select(Region.id).where(ST_Contains(Region.geom, WKTElement(f"POINT({lon} {lat})", srid=4326)))
        ).scalars().first()

    # Distribution: observation counts per region for a species (FR-3.2 support).
    def distribution(self, scientific_name: str) -> list[dict]:
        rows = self.db.execute(
            select(Region.code, Region.name, func.count(SpeciesObservation.id))
            .join(SpeciesObservation, SpeciesObservation.region_id == Region.id)
            .join(Species, Species.id == SpeciesObservation.species_id)
            .where(Species.scientific_name == scientific_name)
            .group_by(Region.code, Region.name)
            .order_by(func.count(SpeciesObservation.id).desc())
        ).all()
        return [{"region_code": c, "region_name": n, "count": int(cnt)} for c, n, cnt in rows]

    def richness_by_region(self) -> list[dict]:
        rows = self.db.execute(
            select(
                Region.code, Region.name,
                func.count(func.distinct(SpeciesObservation.species_id)),
                func.count(SpeciesObservation.id),
            )
            .join(SpeciesObservation, SpeciesObservation.region_id == Region.id)
            .group_by(Region.code, Region.name)
            .order_by(Region.name)
        ).all()
        return [
            {"region_code": c, "region_name": n, "species_richness": int(rich), "observations": int(cnt)}
            for c, n, rich, cnt in rows
        ]

    def list_species(self) -> list[Species]:
        return list(self.db.execute(select(Species).order_by(Species.scientific_name)).scalars().all())

    # --- Analytics (dashboard / biodiversity page) ---------------------------

    def top_observed(self, limit: int = 10) -> list[dict]:
        """Most-observed species overall (leaderboard)."""
        rows = self.db.execute(
            select(
                Species.id,
                Species.scientific_name,
                Species.conservation_status,
                Species.endemic,
                func.count(SpeciesObservation.id).label("observations"),
                func.count(func.distinct(SpeciesObservation.region_id)).label("regions"),
                func.max(SpeciesObservation.date).label("last_seen"),
            )
            .join(SpeciesObservation, SpeciesObservation.species_id == Species.id)
            .group_by(Species.id, Species.scientific_name, Species.conservation_status, Species.endemic)
            .order_by(func.count(SpeciesObservation.id).desc())
            .limit(limit)
        ).all()
        return [
            {
                "species_id": sid,
                "scientific_name": name,
                "conservation_status": status,
                "endemic": bool(endemic),
                "observations": int(obs),
                "regions": int(regions),
                "last_seen": last,
            }
            for sid, name, status, endemic, obs, regions, last in rows
        ]

    def status_breakdown(self) -> list[dict]:
        """Species + observation counts grouped by IUCN conservation status."""
        rows = self.db.execute(
            select(
                Species.conservation_status,
                func.count(func.distinct(Species.id)),
                func.count(SpeciesObservation.id),
            )
            .outerjoin(SpeciesObservation, SpeciesObservation.species_id == Species.id)
            .group_by(Species.conservation_status)
        ).all()
        out = [
            {"status": status or "NA", "species": int(sp), "observations": int(obs)}
            for status, sp, obs in rows
        ]
        out.sort(key=lambda r: _status_rank(None if r["status"] == "NA" else r["status"]))
        return out

    def observation_trend(self) -> list[dict]:
        """Monthly observation counts, split by data source."""
        month = func.date_trunc("month", SpeciesObservation.date)
        rows = self.db.execute(
            select(month.label("m"), SpeciesObservation.source, func.count(SpeciesObservation.id))
            .group_by("m", SpeciesObservation.source)
            .order_by("m")
        ).all()
        buckets: dict[str, dict] = {}
        for m, source, cnt in rows:
            key = m.date().isoformat()
            b = buckets.setdefault(key, {"month": key, "gbif": 0, "inaturalist": 0, "upload": 0, "total": 0})
            b[source if source in ("gbif", "inaturalist", "upload") else "upload"] += int(cnt)
            b["total"] += int(cnt)
        return [buckets[k] for k in sorted(buckets)]

    def observations_geojson(self, limit: int = 2000) -> dict:
        """Observation points as a GeoJSON FeatureCollection (biodiversity map)."""
        rows = self.db.execute(
            select(
                ST_X(SpeciesObservation.location),
                ST_Y(SpeciesObservation.location),
                Species.scientific_name,
                Species.conservation_status,
                Species.endemic,
                SpeciesObservation.source,
                SpeciesObservation.date,
                Region.name,
            )
            .join(Species, Species.id == SpeciesObservation.species_id)
            .outerjoin(Region, Region.id == SpeciesObservation.region_id)
            .order_by(SpeciesObservation.date.desc())
            .limit(limit)
        ).all()
        features = [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [float(lon), float(lat)]},
                "properties": {
                    "scientific_name": name,
                    "conservation_status": status,
                    "endemic": bool(endemic),
                    "source": source,
                    "date": date.isoformat() if date else None,
                    "region": region,
                },
            }
            for lon, lat, name, status, endemic, source, date, region in rows
        ]
        return {"type": "FeatureCollection", "features": features}

    def decline_risk(self) -> list[dict]:
        """Species-decline watch: species observed inside detected deforestation
        zones, weighted by IUCN status and the region's vegetation loss.

        Cross-references SpeciesObservation.region_id with regions that carry a
        DeforestationEvent (FR-7.2 support, exposed for the dashboard)."""
        loss_by_region = dict(
            self.db.execute(
                select(
                    DeforestationEvent.region_id,
                    func.max(DeforestationEvent.vegetation_loss),
                ).group_by(DeforestationEvent.region_id)
            ).all()
        )
        at_risk = {rid: float(loss) for rid, loss in loss_by_region.items() if rid is not None}
        if not at_risk:
            return []

        rows = self.db.execute(
            select(
                Species.id,
                Species.scientific_name,
                Species.conservation_status,
                Species.endemic,
                SpeciesObservation.region_id,
                Region.name,
                func.count(SpeciesObservation.id),
            )
            .join(SpeciesObservation, SpeciesObservation.species_id == Species.id)
            .outerjoin(Region, Region.id == SpeciesObservation.region_id)
            .where(SpeciesObservation.region_id.in_(list(at_risk)))
            .group_by(
                Species.id, Species.scientific_name, Species.conservation_status,
                Species.endemic, SpeciesObservation.region_id, Region.name,
            )
        ).all()

        agg: dict[int, dict] = {}
        for sid, name, status, endemic, rid, region_name, cnt in rows:
            entry = agg.setdefault(
                sid,
                {
                    "species_id": sid,
                    "scientific_name": name,
                    "conservation_status": status,
                    "endemic": bool(endemic),
                    "observations_at_risk": 0,
                    "regions": [],
                    "max_loss": 0.0,
                },
            )
            entry["observations_at_risk"] += int(cnt)
            if region_name and region_name not in entry["regions"]:
                entry["regions"].append(region_name)
            entry["max_loss"] = max(entry["max_loss"], at_risk.get(rid, 0.0))

        result = []
        for entry in agg.values():
            weight = _STATUS_WEIGHT.get(entry["conservation_status"], 0.3)
            score = weight * (0.4 + entry["max_loss"]) * (1 + min(entry["observations_at_risk"], 40) / 40)
            entry["risk_score"] = round(score, 3)
            entry["max_loss"] = round(entry["max_loss"], 3)
            if entry["conservation_status"] in ("CR", "EN") and entry["max_loss"] >= 0.12:
                entry["risk_level"] = "high"
            elif weight >= 0.4 or entry["max_loss"] >= 0.12:
                entry["risk_level"] = "medium"
            else:
                entry["risk_level"] = "low"
            result.append(entry)

        result.sort(key=lambda r: r["risk_score"], reverse=True)
        return result
