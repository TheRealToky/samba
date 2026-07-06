"""Generate realistic MOCK environmental data for the SAMBA MVP.

Creates a default researcher account, 5 fictional Madagascar regions with ~6 months
of weekly NDVI + climate readings, and a set of endemic species with observations.
Two regions contain a clear NDVI drop so that POST /analyze produces events.

Run from the `backend/` directory:  python seed.py

All data is fabricated — no real satellite/GBIF/iNaturalist APIs are contacted.
"""
from __future__ import annotations

import math
import random
from datetime import date, timedelta

from app.database import Base, SessionLocal, engine
from app import models
from app.security import hash_password

RNG = random.Random(42)
START = date(2026, 1, 1)
WEEKS = 26

DEFAULT_USER = {"name": "SAMBA Researcher", "email": "researcher@samba.mg", "password": "samba1234"}

# NDVI profile per region as a function of week index (0..WEEKS-1).
# "healthy" stays high; the others encode different deforestation signatures.
def _ndvi_healthy(base: float):
    return lambda w: base

def _ndvi_step_drop(high: float, low: float, drop_week: int):
    return lambda w: high if w < drop_week else low

def _ndvi_ramp_drop(high: float, low: float, start_w: int, end_w: int):
    def f(w):
        if w <= start_w:
            return high
        if w >= end_w:
            return low
        frac = (w - start_w) / (end_w - start_w)
        return high + (low - high) * frac
    return f


REGIONS = {
    "Ankarafa Reserve": _ndvi_healthy(0.80),          # stable, healthy -> no event
    "Menabe Corridor": _ndvi_step_drop(0.75, 0.38, 12),  # sharp clearing -> high
    "Vohimana Ridge": _ndvi_ramp_drop(0.72, 0.50, 12, 18),  # gradual -> moderate
    "Tsingy Verde": _ndvi_healthy(0.66),              # stable dry forest -> no event
    "Mangoro Basin": _ndvi_step_drop(0.80, 0.42, 19),   # late sudden loss -> high
}

SPECIES = [
    ("Lemur catta", "Endangered", True),
    ("Indri indri", "Critically Endangered", True),
    ("Propithecus candidus", "Critically Endangered", True),
    ("Brookesia micra", "Near Threatened", True),
    ("Uroplatus phantasticus", "Least Concern", True),
    ("Astrochelys radiata", "Critically Endangered", True),
]
SOURCES = ["iNaturalist (mock)", "GBIF (mock)", "field-survey (mock)"]


def _week_date(w: int) -> date:
    return START + timedelta(weeks=w)


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # Idempotent: wipe existing rows so re-seeding is clean.
        for model in (
            models.EnvironmentalAlert,
            models.DeforestationEvent,
            models.SpeciesObservation,
            models.Species,
            models.ClimateData,
            models.SatelliteData,
            models.User,
        ):
            db.query(model).delete()
        db.commit()

        # Default researcher account.
        db.add(models.User(
            name=DEFAULT_USER["name"],
            email=DEFAULT_USER["email"],
            password_hash=hash_password(DEFAULT_USER["password"]),
            role="researcher",
        ))

        # Satellite (NDVI) + climate time-series per region.
        for region, ndvi_fn in REGIONS.items():
            for w in range(WEEKS):
                d = _week_date(w)
                ndvi = max(0.0, min(1.0, ndvi_fn(w) + RNG.uniform(-0.02, 0.02)))
                db.add(models.SatelliteData(polygon_location=region, ndvi=round(ndvi, 3), date=d))

                seasonal = math.sin(2 * math.pi * w / WEEKS)  # crude wet/dry season swing
                db.add(models.ClimateData(
                    polygon_location=region,
                    temperature=round(24 + 4 * seasonal + RNG.uniform(-1.5, 1.5), 1),
                    humidity=round(70 + 15 * seasonal + RNG.uniform(-5, 5), 1),
                    rainfall=round(max(0.0, 120 * (0.5 + 0.5 * seasonal) + RNG.uniform(-20, 20)), 1),
                    date=d,
                ))

        # Species catalogue.
        species_rows = [
            models.Species(scientific_name=n, conservation_status=s, endemic=e)
            for (n, s, e) in SPECIES
        ]
        db.add_all(species_rows)
        db.flush()  # assign ids

        # Scatter observations across regions and dates.
        region_names = list(REGIONS.keys())
        for sp in species_rows:
            for _ in range(RNG.randint(4, 8)):
                db.add(models.SpeciesObservation(
                    polygon_location=RNG.choice(region_names),
                    date=_week_date(RNG.randint(0, WEEKS - 1)),
                    source=RNG.choice(SOURCES),
                    species_id=sp.id,
                ))

        db.commit()

        counts = {
            "regions": len(REGIONS),
            "satellite_rows": db.query(models.SatelliteData).count(),
            "climate_rows": db.query(models.ClimateData).count(),
            "species": db.query(models.Species).count(),
            "observations": db.query(models.SpeciesObservation).count(),
        }
        print("Seed complete:", counts)
        print(f"Login with  {DEFAULT_USER['email']}  /  {DEFAULT_USER['password']}")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
