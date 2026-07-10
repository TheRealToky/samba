"""Satellite provider: Google Earth Engine (live) + deterministic sample.

Live mode derives a scalar mean NDVI per region per month from Sentinel-2 via
`reduceRegion` — matching the SatelliteData.ndvi shape. It requires a GEE-
registered GCP project and a service-account key (GEE_* settings); the import is
lazy so the earthengine-api package is only needed for live mode.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta

from app.config import settings
from app.ingestion.base import SatelliteRecord
from app.ingestion.sampling import sample_satellite
from app.geo.madagascar import bbox_polygon_wkt


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

    def _fetch_live(self, region: dict, start: datetime, end: datetime) -> list[SatelliteRecord]:
        ee = self._init_ee()
        lon_min, lat_min, lon_max, lat_max = region["bbox"]
        geom = ee.Geometry.Rectangle([lon_min, lat_min, lon_max, lat_max])
        wkt = bbox_polygon_wkt(tuple(region["bbox"]))

        def with_ndvi(img):
            return img.addBands(img.normalizedDifference(["B8", "B4"]).rename("NDVI"))

        records: list[SatelliteRecord] = []
        cursor = datetime(start.year, start.month, 1, tzinfo=start.tzinfo)
        while cursor <= end:
            nxt = (cursor.replace(day=28) + timedelta(days=8)).replace(day=1)
            col = (
                ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
                .filterBounds(geom)
                .filterDate(cursor.strftime("%Y-%m-%d"), nxt.strftime("%Y-%m-%d"))
                .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 40))
                .map(with_ndvi)
            )
            composite = col.select("NDVI").median()
            value = composite.reduceRegion(
                reducer=ee.Reducer.mean(), geometry=geom, scale=250, maxPixels=1e9
            ).get("NDVI")
            ndvi = value.getInfo() if value is not None else None
            if ndvi is not None:
                records.append(
                    SatelliteRecord(date=cursor, ndvi=round(float(ndvi), 4), location_wkt=wkt)
                )
            cursor = nxt
        return records
