"""Satellite provider: Google Earth Engine (live) + deterministic sample.

Live mode derives a scalar mean NDVI per region per month from Sentinel-2 via
`reduceRegion` — matching the SatelliteData.ndvi shape. It requires a GEE-
registered GCP project and a service-account key (GEE_* settings); the import is
lazy so the earthengine-api package is only needed for live mode.

The whole monthly series is computed server-side and pulled in a single
`getInfo()` round trip (rather than one call per month) to cut latency and stay
well under Earth Engine's request quotas.
"""
from __future__ import annotations

import json
from datetime import datetime

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

        months = ee.List.sequence(0, n_months - 1)
        fc = ee.FeatureCollection(months.map(monthly_feature))
        data = fc.getInfo()  # single round trip for the whole series

        records: list[SatelliteRecord] = []
        for feat in data.get("features", []):
            props = feat.get("properties", {})
            ndvi = props.get("ndvi")
            if ndvi is None:  # fully-clouded / empty month
                continue
            d = datetime.strptime(props["date"], "%Y-%m-%d").replace(tzinfo=start.tzinfo)
            records.append(SatelliteRecord(date=d, ndvi=round(float(ndvi), 4), location_wkt=wkt))
        return records
