"""Satellite provider: Google Earth Engine (live) + deterministic sample.

Live mode derives a scalar mean NDVI per region per month from Sentinel-2 via
`reduceRegion` — matching the SatelliteData.ndvi shape. It requires a GEE-
registered GCP project and a service-account key (GEE_* settings); the import is
lazy so the earthengine-api package is only needed for live mode.

Each month is one `reduceRegion` aggregation. Earth Engine caps how many
aggregations a single request may run concurrently ("Too many concurrent
aggregations"), so the monthly series is pulled in batches of
`GEE_MAX_MONTHS_PER_REQUEST` months per `getInfo()` (not the whole series at
once), with exponential-backoff retries for transient throttling.
"""
from __future__ import annotations

import json
import time
from datetime import datetime

from app.config import settings
from app.ingestion.base import SatelliteRecord
from app.ingestion.sampling import sample_satellite
from app.geo.madagascar import bbox_polygon_wkt

# Substrings that mark a retryable Earth Engine condition (throttling/transient).
_EE_TRANSIENT = (
    "too many", "concurrent", "timed out", "timeout",
    "quota", "rate limit", "backend error", "try again", "please retry",
)


class EarthEngineSatelliteProvider:
    name = "earth_engine"

    def __init__(self, mode: str = "sample"):
        self.mode = mode
        self._ee = None

    def fetch_ndvi(self, region: dict, start: datetime, end: datetime) -> list[SatelliteRecord]:
        if self.mode != "live":
            return sample_satellite(region, start, end)
        return self._fetch_live(region, start, end)

    # --- live -----------------------------------------------------------------
    def _init_ee(self):
        if self._ee is not None:
            return self._ee
        import ee  # lazy: only required in live mode

        with open(settings.gee_service_account_json) as fh:
            sa_email = json.load(fh)["client_email"]
        creds = ee.ServiceAccountCredentials(sa_email, settings.gee_service_account_json)
        ee.Initialize(creds, project=settings.gee_project or None)
        self._ee = ee
        return ee

    def _get_info(self, obj, attempts: int = 5):
        """`obj.getInfo()` with exponential backoff on transient EE errors."""
        delay = 2.0
        for attempt in range(1, attempts + 1):
            try:
                return obj.getInfo()
            except Exception as exc:  # ee.EEException and friends
                transient = any(s in str(exc).lower() for s in _EE_TRANSIENT)
                if attempt == attempts or not transient:
                    raise
                time.sleep(delay)
                delay *= 2

    def _fetch_live(self, region: dict, start: datetime, end: datetime) -> list[SatelliteRecord]:
        bbox = region.get("bbox")
        if bbox is None:  # custom region without geometry — nothing to clip against
            return []
        ee = self._init_ee()
        lon_min, lat_min, lon_max, lat_max = bbox
        geom = ee.Geometry.Rectangle([lon_min, lat_min, lon_max, lat_max])
        wkt = bbox_polygon_wkt(tuple(bbox))

        n_months = (end.year - start.year) * 12 + (end.month - start.month) + 1
        start_month = ee.Date.fromYMD(start.year, start.month, 1)
        s2 = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")

        def monthly_feature(offset):
            offset = ee.Number(offset)
            d0 = start_month.advance(offset, "month")
            d1 = d0.advance(1, "month")
            col = (
                s2.filterBounds(geom)
                .filterDate(d0, d1)
                .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 40))
                .map(lambda img: img.normalizedDifference(["B8", "B4"]).rename("NDVI"))
            )
            mean = col.median().reduceRegion(
                reducer=ee.Reducer.mean(), geometry=geom, scale=250, maxPixels=1e9
            ).get("NDVI")
            return ee.Feature(None, {"date": d0.format("YYYY-MM-dd"), "ndvi": mean})

        # Pull the series in month-batches so each getInfo triggers only a handful
        # of concurrent reduceRegion aggregations (see module docstring).
        batch = max(1, settings.gee_max_months_per_request)
        records: list[SatelliteRecord] = []
        for base in range(0, n_months, batch):
            offsets = ee.List.sequence(base, min(base + batch, n_months) - 1)
            fc = ee.FeatureCollection(offsets.map(monthly_feature))
            data = self._get_info(fc)
            for feat in data.get("features", []):
                props = feat.get("properties", {})
                ndvi = props.get("ndvi")
                if ndvi is None:  # fully-clouded / empty month
                    continue
                d = datetime.strptime(props["date"], "%Y-%m-%d").replace(tzinfo=start.tzinfo)
                records.append(SatelliteRecord(date=d, ndvi=round(float(ndvi), 4), location_wkt=wkt))
        return records
