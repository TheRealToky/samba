"""Madagascar region definitions (single source of truth for seeding + sampling).

The 24 current Malagasy regions with **real administrative boundaries**. Geometry
comes from the bundled ``data/madagascar_regions.geojson`` (built offline from
geoBoundaries ADM1/ADM2 by ``scripts/build_regions_geojson.py`` — see that file
for provenance and the district dissolves behind Vatovavy/Fitovinany and
Ambatosoa/Analanjirofo). This module stays dependency-light: it only reads JSON
and derives each region's bounding box, so migrations and workers can import it
without pulling in any geo stack.

``REGIONS`` is what the rest of the system consumes: each entry carries the real
``geometry`` (GeoJSON dict, used to seed ``Region.geom``) plus a derived ``bbox``
(the geometry's envelope). Sampling / climate-centroid / GEE / training all key
off ``bbox`` and ``biome``, so they keep working unchanged; only the seed geometry
became precise. ``REGION_META`` is the human-facing catalogue (code / name /
biome / former province / capital).
"""
from __future__ import annotations

import json
from pathlib import Path

_DATA_FILE = Path(__file__).parent / "data" / "madagascar_regions.geojson"

# code, name, dominant biome, former province, regional capital.
# The 24 regions as of 2025 (22 from 2004 + the Vatovavy/Fitovinany split of 2021
# and the Ambatosoa/Analanjirofo split of 2023). `code` is stable — the original
# eight prototype codes are unchanged so their region_id FKs survive the upgrade.
REGION_META: list[dict] = [
    {"code": "DIANA", "name": "Diana", "biome": "rainforest", "province": "Antsiranana", "capital": "Antsiranana"},
    {"code": "SAVA", "name": "Sava", "biome": "rainforest", "province": "Antsiranana", "capital": "Sambava"},
    {"code": "ITASY", "name": "Itasy", "biome": "highland", "province": "Antananarivo", "capital": "Miarinarivo"},
    {"code": "ANALAMANGA", "name": "Analamanga", "biome": "highland", "province": "Antananarivo", "capital": "Antananarivo"},
    {"code": "VAKINANKARATRA", "name": "Vakinankaratra", "biome": "highland", "province": "Antananarivo", "capital": "Antsirabe"},
    {"code": "BONGOLAVA", "name": "Bongolava", "biome": "highland", "province": "Antananarivo", "capital": "Tsiroanomandidy"},
    {"code": "SOFIA", "name": "Sofia", "biome": "dry_deciduous", "province": "Mahajanga", "capital": "Antsohihy"},
    {"code": "BOENY", "name": "Boeny", "biome": "dry_deciduous", "province": "Mahajanga", "capital": "Mahajanga"},
    {"code": "BETSIBOKA", "name": "Betsiboka", "biome": "dry_deciduous", "province": "Mahajanga", "capital": "Maevatanana"},
    {"code": "MELAKY", "name": "Melaky", "biome": "dry_deciduous", "province": "Mahajanga", "capital": "Maintirano"},
    {"code": "ALAOTRA_MANGORO", "name": "Alaotra-Mangoro", "biome": "rainforest", "province": "Toamasina", "capital": "Ambatondrazaka"},
    {"code": "ATSINANANA", "name": "Atsinanana", "biome": "rainforest", "province": "Toamasina", "capital": "Toamasina"},
    {"code": "AMBATOSOA", "name": "Ambatosoa", "biome": "rainforest", "province": "Toamasina", "capital": "Maroantsetra"},
    {"code": "ANALANJIROFO", "name": "Analanjirofo", "biome": "rainforest", "province": "Toamasina", "capital": "Fenoarivo Atsinanana"},
    {"code": "AMORON_I_MANIA", "name": "Amoron'i Mania", "biome": "highland", "province": "Fianarantsoa", "capital": "Ambositra"},
    {"code": "MATSIATRA_AMBONY", "name": "Matsiatra Ambony", "biome": "highland", "province": "Fianarantsoa", "capital": "Fianarantsoa"},
    {"code": "VATOVAVY", "name": "Vatovavy", "biome": "rainforest", "province": "Fianarantsoa", "capital": "Mananjary"},
    {"code": "FITOVINANY", "name": "Fitovinany", "biome": "rainforest", "province": "Fianarantsoa", "capital": "Manakara"},
    {"code": "ATSIMO_ATSINANANA", "name": "Atsimo-Atsinanana", "biome": "rainforest", "province": "Fianarantsoa", "capital": "Farafangana"},
    {"code": "IHOROMBE", "name": "Ihorombe", "biome": "highland", "province": "Fianarantsoa", "capital": "Ihosy"},
    {"code": "MENABE", "name": "Menabe", "biome": "dry_deciduous", "province": "Toliara", "capital": "Morondava"},
    {"code": "ATSIMO_ANDREFANA", "name": "Atsimo-Andrefana", "biome": "spiny_forest", "province": "Toliara", "capital": "Toliara"},
    {"code": "ANDROY", "name": "Androy", "biome": "spiny_forest", "province": "Toliara", "capital": "Ambovombe"},
    {"code": "ANOSY", "name": "Anosy", "biome": "littoral", "province": "Toliara", "capital": "Tolagnaro"},
]


def _iter_lonlat(coordinates):
    """Yield every (lon, lat) pair in an arbitrarily nested GeoJSON coord array."""
    if coordinates and isinstance(coordinates[0], (int, float)):
        yield coordinates[0], coordinates[1]
    else:
        for part in coordinates:
            yield from _iter_lonlat(part)


def _bbox_of(geometry: dict) -> tuple[float, float, float, float]:
    lons, lats = [], []
    for lon, lat in _iter_lonlat(geometry["coordinates"]):
        lons.append(lon)
        lats.append(lat)
    return (min(lons), min(lats), max(lons), max(lats))


def _load_regions() -> list[dict]:
    fc = json.loads(_DATA_FILE.read_text(encoding="utf-8"))
    geom_by_code = {f["properties"]["code"]: f["geometry"] for f in fc["features"]}
    regions: list[dict] = []
    for meta in REGION_META:
        geometry = geom_by_code.get(meta["code"])
        if geometry is None:
            raise RuntimeError(
                f"region {meta['code']} missing from {_DATA_FILE.name}; "
                "rebuild it with scripts/build_regions_geojson.py"
            )
        regions.append({**meta, "geometry": geometry, "bbox": _bbox_of(geometry)})
    return regions


# The 24 regions with real geometry + derived envelope. Built once at import.
REGIONS: list[dict] = _load_regions()


def bbox_polygon_wkt(bbox: tuple[float, float, float, float]) -> str:
    lon_min, lat_min, lon_max, lat_max = bbox
    return (
        f"POLYGON(({lon_min} {lat_min}, {lon_max} {lat_min}, "
        f"{lon_max} {lat_max}, {lon_min} {lat_max}, {lon_min} {lat_min}))"
    )


def bbox_centroid(bbox: tuple[float, float, float, float]) -> tuple[float, float]:
    lon_min, lat_min, lon_max, lat_max = bbox
    return ((lon_min + lon_max) / 2.0, (lat_min + lat_max) / 2.0)
