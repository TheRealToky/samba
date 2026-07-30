"""Build the bundled 24-region boundary file from geoBoundaries source data.

Output: ``app/geo/data/madagascar_regions.geojson`` — a FeatureCollection of the
24 current Malagasy regions as ``MultiPolygon`` features carrying ``code``,
``name`` and ``biome`` properties. That file is committed and loaded at runtime
with **no geo dependencies** (pure ``json``); this script is the only place that
needs ``shapely``, and it runs offline, once, when the boundaries change.

Why a build step at all: geoBoundaries ADM1 ships the 22 pre-2021 regions. Two
of those were later split along existing district (ADM2) lines:

  * Vatovavy-Fitovinany (2021) -> Vatovavy + Fitovinany
  * Analanjirofo       (2023) -> Analanjirofo (reduced) + Ambatosoa

The 20 unchanged regions come straight from ADM1; the 4 split children are the
dissolved union of their districts, so every boundary is real (no hand-drawn
geometry) and the children exactly tile their parent.

Source data: geoBoundaries gbOpen MDG ADM1 + ADM2, Open Database License (ODbL).
Download the two ``*_simplified.geojson`` files and pass them as arguments.

Usage::

    python scripts/build_regions_geojson.py ADM1.geojson ADM2.geojson
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import shapely
from shapely.geometry import MultiPolygon, mapping, shape
from shapely.ops import unary_union
from shapely.prepared import prep

# --- Build specification --------------------------------------------------
# Each entry: code, name, biome, and how to source its geometry.
#   {"adm1": <name>}                        -> take that ADM1 region verbatim
#   {"parent": <adm1 name>, "adm2": [...]}  -> dissolve these ADM2 districts
# The 24 codes/names/biomes here are the single source of truth for the build;
# they are mirrored (minus geometry) by REGION_META in app/geo/madagascar.py,
# and a test asserts the two stay in sync.
SPEC: list[dict] = [
    {"code": "DIANA", "name": "Diana", "biome": "rainforest", "adm1": "Diana"},
    {"code": "SAVA", "name": "Sava", "biome": "rainforest", "adm1": "Sava"},
    {"code": "ITASY", "name": "Itasy", "biome": "highland", "adm1": "Itasy"},
    {"code": "ANALAMANGA", "name": "Analamanga", "biome": "highland", "adm1": "Analamanga"},
    {"code": "VAKINANKARATRA", "name": "Vakinankaratra", "biome": "highland", "adm1": "Vakinankaratra"},
    {"code": "BONGOLAVA", "name": "Bongolava", "biome": "highland", "adm1": "Bongolava"},
    {"code": "SOFIA", "name": "Sofia", "biome": "dry_deciduous", "adm1": "Sofia"},
    {"code": "BOENY", "name": "Boeny", "biome": "dry_deciduous", "adm1": "Boeny"},
    {"code": "BETSIBOKA", "name": "Betsiboka", "biome": "dry_deciduous", "adm1": "Betsiboka"},
    {"code": "MELAKY", "name": "Melaky", "biome": "dry_deciduous", "adm1": "Melaky"},
    {"code": "ALAOTRA_MANGORO", "name": "Alaotra-Mangoro", "biome": "rainforest", "adm1": "Alaotra-Mangoro"},
    {"code": "ATSINANANA", "name": "Atsinanana", "biome": "rainforest", "adm1": "Atsinanana"},
    # Analanjirofo split (2023): Ambatosoa carved from the north.
    {"code": "AMBATOSOA", "name": "Ambatosoa", "biome": "rainforest",
     "parent": "Analanjirofo", "adm2": ["Maroantsetra", "Mananara-Avaratra"]},
    {"code": "ANALANJIROFO", "name": "Analanjirofo", "biome": "rainforest",
     "parent": "Analanjirofo",
     "adm2": ["Fenerive Est", "Sainte Marie", "Soanierana Ivongo", "Vavatenina"]},
    {"code": "AMORON_I_MANIA", "name": "Amoron'i Mania", "biome": "highland", "adm1": "Amoron'i Mania"},
    {"code": "MATSIATRA_AMBONY", "name": "Matsiatra Ambony", "biome": "highland", "adm1": "Matsiatra Ambony"},
    # Vatovavy-Fitovinany split (2021).
    {"code": "VATOVAVY", "name": "Vatovavy", "biome": "rainforest",
     "parent": "Vatovavy-Fitovinany", "adm2": ["Mananjary", "Nosy-Varika", "Ifanadiana"]},
    {"code": "FITOVINANY", "name": "Fitovinany", "biome": "rainforest",
     "parent": "Vatovavy-Fitovinany", "adm2": ["Ikongo", "Manakara Atsimo"]},
    {"code": "ATSIMO_ATSINANANA", "name": "Atsimo-Atsinanana", "biome": "rainforest", "adm1": "Atsimo-Atsinanana"},
    {"code": "IHOROMBE", "name": "Ihorombe", "biome": "highland", "adm1": "Ihorombe"},
    {"code": "MENABE", "name": "Menabe", "biome": "dry_deciduous", "adm1": "Menabe"},
    {"code": "ATSIMO_ANDREFANA", "name": "Atsimo-Andrefana", "biome": "spiny_forest", "adm1": "Atsimo-Andrefana"},
    {"code": "ANDROY", "name": "Androy", "biome": "spiny_forest", "adm1": "Androy"},
    {"code": "ANOSY", "name": "Anosy", "biome": "littoral", "adm1": "Anosy"},
]

_COORD_PRECISION = 6


def _load(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _by_name(fc: dict) -> dict[str, list[dict]]:
    """Map shapeName -> list of features (a name may repeat across parts)."""
    out: dict[str, list[dict]] = {}
    for f in fc["features"]:
        out.setdefault(f["properties"]["shapeName"], []).append(f)
    return out


def _clean(geom):
    """Repair simplified geometry and normalise to a MultiPolygon."""
    if not geom.is_valid:
        geom = shapely.make_valid(geom)
    if geom.geom_type == "Polygon":
        geom = MultiPolygon([geom])
    elif geom.geom_type == "GeometryCollection":
        polys = [g for g in geom.geoms if g.geom_type in ("Polygon", "MultiPolygon")]
        geom = unary_union(polys)
        if geom.geom_type == "Polygon":
            geom = MultiPolygon([geom])
    return geom


def _round(obj):
    if isinstance(obj, float):
        return round(obj, _COORD_PRECISION)
    if isinstance(obj, list):
        return [_round(x) for x in obj]
    return obj


def _assign_districts_to_parents(adm1: dict, adm2: dict) -> dict[str, set[str]]:
    """Spatially group ADM2 district names under their containing ADM1 region."""
    regions = {f["properties"]["shapeName"]: shape(f["geometry"]) for f in adm1["features"]}
    prepared = {n: prep(g) for n, g in regions.items()}
    groups: dict[str, set[str]] = {n: set() for n in regions}
    for f in adm2["features"]:
        d = f["properties"]["shapeName"]
        pt = shape(f["geometry"]).representative_point()
        hit = next((n for n, pg in prepared.items() if pg.contains(pt)), None)
        if hit is None:  # nearest as a safety net (didn't occur on gbOpen data)
            hit = min(regions, key=lambda n: regions[n].distance(pt))
        groups[hit].add(d)
    return groups


def build(adm1_path: str, adm2_path: str) -> dict:
    adm1 = _load(adm1_path)
    adm2 = _load(adm2_path)
    adm1_by = _by_name(adm1)
    adm2_by = _by_name(adm2)
    parent_districts = _assign_districts_to_parents(adm1, adm2)

    # Sanity-check every split parent is fully and disjointly covered by children.
    split_children: dict[str, list[dict]] = {}
    for e in SPEC:
        if "parent" in e:
            split_children.setdefault(e["parent"], []).append(e)
    for parent, children in split_children.items():
        used: set[str] = set()
        for c in children:
            for d in c["adm2"]:
                if d not in adm2_by:
                    raise SystemExit(f"district {d!r} (for {c['code']}) not found in ADM2")
                if d not in parent_districts[parent]:
                    raise SystemExit(f"district {d!r} is not inside parent {parent!r}")
                if d in used:
                    raise SystemExit(f"district {d!r} assigned to two children of {parent!r}")
                used.add(d)
        missing = parent_districts[parent] - used
        if missing:
            raise SystemExit(f"parent {parent!r} has unassigned districts: {sorted(missing)}")

    features = []
    for e in SPEC:
        if "adm1" in e:
            src = adm1_by.get(e["adm1"])
            if not src:
                raise SystemExit(f"ADM1 region {e['adm1']!r} not found")
            geom = _clean(unary_union([shape(f["geometry"]) for f in src]))
        else:
            parts = [shape(f["geometry"]) for d in e["adm2"] for f in adm2_by[d]]
            geom = _clean(unary_union(parts))
        features.append(
            {
                "type": "Feature",
                "properties": {"code": e["code"], "name": e["name"], "biome": e["biome"]},
                "geometry": _round(mapping(geom)),
            }
        )
    return {"type": "FeatureCollection", "features": features}


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    fc = build(sys.argv[1], sys.argv[2])
    out = Path(__file__).resolve().parents[1] / "app" / "geo" / "data" / "madagascar_regions.geojson"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(fc, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {len(fc['features'])} regions -> {out}")


if __name__ == "__main__":
    main()
