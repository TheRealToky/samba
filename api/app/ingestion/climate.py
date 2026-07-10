"""Climate provider: NASA POWER (live) + deterministic sample.

NASA POWER is point-based and needs no API key. Region climate samples the
region centroid (flagged simplification). T2M -> temperature, PRECTOTCORR ->
rainfall, RH2M -> humidity.
"""
from __future__ import annotations

from datetime import datetime

from app.ingestion.base import ClimateRecord
from app.ingestion.sampling import sample_climate
from app.geo.madagascar import bbox_centroid, bbox_polygon_wkt

_POWER_URL = "https://power.larc.nasa.gov/api/temporal/monthly/point"


class NasaPowerClimateProvider:
    name = "nasa_power"

    def __init__(self, mode: str = "sample"):
        self.mode = mode

    def fetch_climate(self, region: dict, start: datetime, end: datetime) -> list[ClimateRecord]:
        if self.mode != "live":
            return sample_climate(region, start, end)
        return self._fetch_live(region, start, end)

    def _fetch_live(self, region: dict, start: datetime, end: datetime) -> list[ClimateRecord]:
        import httpx

        lon, lat = bbox_centroid(tuple(region["bbox"]))
        wkt = bbox_polygon_wkt(tuple(region["bbox"]))
        params = {
            "parameters": "T2M,PRECTOTCORR,RH2M",
            "community": "AG",
            "longitude": lon,
            "latitude": lat,
            "start": start.strftime("%Y"),
            "end": end.strftime("%Y"),
            "format": "JSON",
        }
        resp = httpx.get(_POWER_URL, params=params, timeout=60)
        resp.raise_for_status()
        params_block = resp.json()["properties"]["parameter"]
        t2m = params_block.get("T2M", {})
        prec = params_block.get("PRECTOTCORR", {})
        rh = params_block.get("RH2M", {})

        records: list[ClimateRecord] = []
        for key in sorted(t2m):
            # keys are YYYYMM (plus a YYYY13 annual value NASA appends — skip it)
            if len(key) != 6 or key.endswith("13"):
                continue
            year, month = int(key[:4]), int(key[4:])
            d = datetime(year, month, 15, tzinfo=start.tzinfo)
            records.append(
                ClimateRecord(
                    date=d,
                    temperature=_clean(t2m.get(key)),
                    rainfall=_clean(prec.get(key)),
                    humidity=_clean(rh.get(key)),
                    location_wkt=wkt,
                )
            )
        return records


def _clean(v):
    # NASA POWER uses -999 as a fill value.
    if v is None or v <= -900:
        return None
    return float(v)
