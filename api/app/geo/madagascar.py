"""Madagascar region definitions (single source of truth for seeding + sampling).

SIMPLIFICATION (flagged): regions are approximate axis-aligned bounding boxes
around well-known areas, not the true administrative multipolygons. Good enough
to anchor spatial data, drive sample generation, and exercise PostGIS spatial
queries; swap in real GADM/administrative boundaries later without code changes
(the rest of the system only depends on `Region.geom`).
"""
from __future__ import annotations

# code, human name, (lon_min, lat_min, lon_max, lat_max), dominant biome
REGIONS: list[dict] = [
    {"code": "ANALAMANGA", "name": "Analamanga", "bbox": (47.0, -19.5, 48.0, -18.5), "biome": "highland"},
    {"code": "ATSINANANA", "name": "Atsinanana", "bbox": (48.8, -19.2, 49.6, -17.8), "biome": "rainforest"},
    {"code": "SAVA", "name": "Sava", "bbox": (49.5, -15.2, 50.5, -13.5), "biome": "rainforest"},
    {"code": "DIANA", "name": "Diana", "bbox": (48.5, -13.8, 49.6, -12.2), "biome": "rainforest"},
    {"code": "BOENY", "name": "Boeny", "bbox": (45.8, -16.8, 47.2, -15.4), "biome": "dry_deciduous"},
    {"code": "MENABE", "name": "Menabe", "bbox": (43.9, -20.6, 45.4, -19.2), "biome": "dry_deciduous"},
    {"code": "ATSIMO_ANDREFANA", "name": "Atsimo-Andrefana", "bbox": (43.5, -23.8, 45.0, -22.2), "biome": "spiny_forest"},
    {"code": "ANOSY", "name": "Anosy", "bbox": (46.3, -25.2, 47.3, -24.0), "biome": "littoral"},
]


def bbox_polygon_wkt(bbox: tuple[float, float, float, float]) -> str:
    lon_min, lat_min, lon_max, lat_max = bbox
    return (
        f"POLYGON(({lon_min} {lat_min}, {lon_max} {lat_min}, "
        f"{lon_max} {lat_max}, {lon_min} {lat_max}, {lon_min} {lat_min}))"
    )


def bbox_centroid(bbox: tuple[float, float, float, float]) -> tuple[float, float]:
    lon_min, lat_min, lon_max, lat_max = bbox
    return ((lon_min + lon_max) / 2.0, (lat_min + lat_max) / 2.0)
