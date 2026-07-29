"""Region catalogue invariants (no DB): the bundled 24-region boundary file and
the Python metadata must stay in sync and well-formed."""
from __future__ import annotations

from app.geo.madagascar import REGION_META, REGIONS

# The eight prototype codes must never change: existing region_id FKs depend on
# them surviving the bounding-box -> real-boundary upgrade.
ORIGINAL_CODES = {
    "ANALAMANGA", "ATSINANANA", "SAVA", "DIANA",
    "BOENY", "MENABE", "ATSIMO_ANDREFANA", "ANOSY",
}
# Biomes referenced by the sample generator's NDVI baselines.
KNOWN_BIOMES = {"rainforest", "dry_deciduous", "spiny_forest", "highland", "littoral"}


def test_there_are_24_regions():
    assert len(REGIONS) == 24
    assert len(REGION_META) == 24


def test_codes_unique_and_stable():
    codes = [r["code"] for r in REGIONS]
    assert len(set(codes)) == 24
    assert ORIGINAL_CODES <= set(codes)


def test_meta_matches_bundled_geometry():
    # REGIONS is built by joining REGION_META with the bundled GeoJSON by code;
    # every metadata entry must resolve to a geometry.
    assert {m["code"] for m in REGION_META} == {r["code"] for r in REGIONS}


def test_every_region_has_valid_multipolygon_and_bbox():
    for r in REGIONS:
        assert r["geometry"]["type"] == "MultiPolygon"
        assert r["biome"] in KNOWN_BIOMES
        lon_min, lat_min, lon_max, lat_max = r["bbox"]
        assert lon_min < lon_max and lat_min < lat_max
        # within Madagascar's extent
        assert 42.0 < lon_min and lon_max < 51.5
        assert -26.5 < lat_min and lat_max < -11.0
