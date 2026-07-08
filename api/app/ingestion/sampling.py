"""Deterministic sample-data generators.

Used when INGESTION_MODE=sample (default) so the whole pipeline runs with no
external credentials or network. Signals are engineered to be *meaningful*:
some regions carry a deforestation change-point in their NDVI series so Phase 3
change-point detection has something real to find.
"""
from __future__ import annotations

import hashlib
import math
from datetime import datetime, timedelta, timezone

from app.geo.madagascar import bbox_centroid, bbox_polygon_wkt
from app.ingestion.base import ClimateRecord, ObservationRecord, SatelliteRecord

# Baseline NDVI by biome (healthy vegetation greenness).
_BIOME_NDVI = {
    "rainforest": 0.82,
    "dry_deciduous": 0.55,
    "spiny_forest": 0.38,
    "highland": 0.50,
    "littoral": 0.60,
}
# Regions engineered to show forest loss (downward NDVI step mid-series).
_DECLINING = {"ATSINANANA", "MENABE", "BOENY"}

# Malagasy endemic species used for sample observations (IUCN-ish status).
SAMPLE_SPECIES = [
    ("Indri indri", "CR", True),
    ("Lemur catta", "EN", True),
    ("Propithecus diadema", "CR", True),
    ("Daubentonia madagascariensis", "EN", True),
    ("Microcebus murinus", "LC", True),
    ("Furcifer pardalis", "LC", True),
    ("Uroplatus phantasticus", "LC", True),
    ("Brookesia micra", "NT", True),
    ("Adansonia grandidieri", "EN", True),
    ("Ravenala madagascariensis", "LC", True),
]


def _seed(*parts: str) -> int:
    h = hashlib.sha256("|".join(parts).encode()).hexdigest()
    return int(h[:8], 16)


def _rng(seed: int):
    # Tiny deterministic LCG so results don't depend on numpy/global state.
    state = {"s": seed % (2**31 - 1) or 1}

    def nxt() -> float:
        state["s"] = (state["s"] * 1103515245 + 12345) & 0x7FFFFFFF
        return state["s"] / 0x7FFFFFFF

    return nxt


def _weekly_dates(start: datetime, end: datetime):
    d = start
    while d <= end:
        yield d
        d += timedelta(days=7)


def _monthly_dates(start: datetime, end: datetime):
    y, m = start.year, start.month
    while datetime(y, m, 1, tzinfo=timezone.utc) <= end:
        yield datetime(y, m, 15, tzinfo=timezone.utc)
        m += 1
        if m > 12:
            m = 1
            y += 1


def sample_satellite(region: dict, start: datetime, end: datetime) -> list[SatelliteRecord]:
    biome = region.get("biome", "highland")
    base = _BIOME_NDVI.get(biome, 0.5)
    wkt = bbox_polygon_wkt(tuple(region["bbox"]))
    rng = _rng(_seed(region["code"], "ndvi"))
    dates = list(_weekly_dates(start, end))
    declining = region["code"] in _DECLINING
    change_idx = int(len(dates) * 0.55) if declining else None
    total_drop = 0.22 if declining else 0.0

    records: list[SatelliteRecord] = []
    for i, d in enumerate(dates):
        # seasonal greenness (wet season peak ~ Jan/Feb in the south)
        doy = d.timetuple().tm_yday
        seasonal = 0.06 * math.sin(2 * math.pi * (doy / 365.0))
        noise = (rng() - 0.5) * 0.04
        ndvi = base + seasonal + noise
        if change_idx is not None and i >= change_idx:
            # gradual loss after the change-point
            progress = (i - change_idx) / max(1, len(dates) - change_idx)
            ndvi -= total_drop * min(1.0, progress * 1.4)
        ndvi = max(-1.0, min(1.0, ndvi))
        records.append(SatelliteRecord(date=d, ndvi=round(ndvi, 4), location_wkt=wkt))
    return records


def sample_climate(region: dict, start: datetime, end: datetime) -> list[ClimateRecord]:
    wkt = bbox_polygon_wkt(tuple(region["bbox"]))
    _, lat = bbox_centroid(tuple(region["bbox"]))
    rng = _rng(_seed(region["code"], "climate"))
    # Cooler in the highlands / far south; warmer in the north.
    mean_temp = 26.0 + (lat + 19.0) * 0.4  # lat is negative
    records: list[ClimateRecord] = []
    for d in _monthly_dates(start, end):
        month = d.month
        # Southern hemisphere: warm/wet Nov–Mar, cool/dry Jun–Aug.
        season = math.cos(2 * math.pi * ((month - 1) / 12.0))  # +1 in Jan
        temp = mean_temp + 4.0 * season + (rng() - 0.5) * 1.5
        rainfall = max(0.0, 120.0 * max(0.0, season) + 15.0 + (rng() - 0.5) * 30.0)
        humidity = max(30.0, min(100.0, 65.0 + 15.0 * season + (rng() - 0.5) * 8.0))
        records.append(
            ClimateRecord(
                date=d,
                temperature=round(temp, 2),
                humidity=round(humidity, 1),
                rainfall=round(rainfall, 1),
                location_wkt=wkt,
            )
        )
    return records


def sample_observations(region: dict, start: datetime, end: datetime, limit: int) -> list[ObservationRecord]:
    lon_min, lat_min, lon_max, lat_max = region["bbox"]
    rng = _rng(_seed(region["code"], "obs"))
    span_days = max(1, (end - start).days)
    n = min(limit, 40)
    records: list[ObservationRecord] = []
    for i in range(n):
        name, status, endemic = SAMPLE_SPECIES[int(rng() * len(SAMPLE_SPECIES)) % len(SAMPLE_SPECIES)]
        lon = lon_min + rng() * (lon_max - lon_min)
        lat = lat_min + rng() * (lat_max - lat_min)
        d = start + timedelta(days=int(rng() * span_days))
        source = "gbif" if rng() < 0.6 else "inaturalist"
        records.append(
            ObservationRecord(
                date=d,
                scientific_name=name,
                lon=round(lon, 5),
                lat=round(lat, 5),
                source=source,
                conservation_status=status,
                endemic=endemic,
            )
        )
    return records
