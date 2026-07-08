"""Biodiversity providers: GBIF + iNaturalist (live) + deterministic sample.

Both read APIs are auth-free. A composite provider merges them (the user chose
both: GBIF for bulk occurrences, iNaturalist for community photos/recent obs).
"""
from __future__ import annotations

from datetime import datetime

from app.ingestion.base import ObservationRecord
from app.ingestion.sampling import sample_observations

_GBIF_URL = "https://api.gbif.org/v1/occurrence/search"
_INAT_URL = "https://api.inaturalist.org/v1/observations"


class GBIFProvider:
    name = "gbif"

    def __init__(self, mode: str = "sample"):
        self.mode = mode

    def fetch_observations(self, region, start, end, limit) -> list[ObservationRecord]:
        if self.mode != "live":
            return [r for r in sample_observations(region, start, end, limit) if r.source == "gbif"]
        return self._fetch_live(region, start, end, limit)

    def _fetch_live(self, region, start, end, limit) -> list[ObservationRecord]:
        import httpx

        lon_min, lat_min, lon_max, lat_max = region["bbox"]
        params = {
            "country": "MG",
            "hasCoordinate": "true",
            "decimalLatitude": f"{lat_min},{lat_max}",
            "decimalLongitude": f"{lon_min},{lon_max}",
            "year": f"{start.year},{end.year}",
            "limit": min(limit, 300),
        }
        resp = httpx.get(_GBIF_URL, params=params, timeout=60)
        resp.raise_for_status()
        out: list[ObservationRecord] = []
        for rec in resp.json().get("results", []):
            name = rec.get("scientificName") or rec.get("species")
            lat, lon = rec.get("decimalLatitude"), rec.get("decimalLongitude")
            if not name or lat is None or lon is None:
                continue
            year = rec.get("year") or start.year
            out.append(
                ObservationRecord(
                    date=datetime(int(year), int(rec.get("month") or 1), int(rec.get("day") or 1), tzinfo=start.tzinfo),
                    scientific_name=name.split(" (")[0],
                    lon=float(lon),
                    lat=float(lat),
                    source="gbif",
                    conservation_status=None,
                    endemic=False,
                    extra={"gbif_key": rec.get("key")},
                )
            )
        return out


class INaturalistProvider:
    name = "inaturalist"

    def __init__(self, mode: str = "sample"):
        self.mode = mode

    def fetch_observations(self, region, start, end, limit) -> list[ObservationRecord]:
        if self.mode != "live":
            return [r for r in sample_observations(region, start, end, limit) if r.source == "inaturalist"]
        return self._fetch_live(region, start, end, limit)

    def _fetch_live(self, region, start, end, limit) -> list[ObservationRecord]:
        import httpx

        lon_min, lat_min, lon_max, lat_max = region["bbox"]
        params = {
            "nelat": lat_max, "nelng": lon_max, "swlat": lat_min, "swlng": lon_min,
            "d1": start.strftime("%Y-%m-%d"), "d2": end.strftime("%Y-%m-%d"),
            "geo": "true", "per_page": min(limit, 200), "order_by": "observed_on",
        }
        resp = httpx.get(_INAT_URL, params=params, timeout=60)
        resp.raise_for_status()
        out: list[ObservationRecord] = []
        for rec in resp.json().get("results", []):
            taxon = rec.get("taxon") or {}
            name = taxon.get("name")
            geo = rec.get("geojson") or {}
            coords = geo.get("coordinates")
            if not name or not coords:
                continue
            observed = rec.get("observed_on") or start.strftime("%Y-%m-%d")
            try:
                d = datetime.fromisoformat(observed).replace(tzinfo=start.tzinfo)
            except ValueError:
                d = start
            out.append(
                ObservationRecord(
                    date=d,
                    scientific_name=name,
                    lon=float(coords[0]),
                    lat=float(coords[1]),
                    source="inaturalist",
                    conservation_status=None,
                    endemic=False,
                    extra={"inat_id": rec.get("id")},
                )
            )
        return out


class CompositeBiodiversityProvider:
    """Merges GBIF + iNaturalist behind the single BiodiversityProvider contract."""

    name = "gbif+inaturalist"

    def __init__(self, mode: str = "sample"):
        self.providers = [GBIFProvider(mode), INaturalistProvider(mode)]

    def fetch_observations(self, region, start, end, limit) -> list[ObservationRecord]:
        out: list[ObservationRecord] = []
        for p in self.providers:
            try:
                out.extend(p.fetch_observations(region, start, end, limit))
            except Exception as exc:  # one source failing shouldn't sink the other (NFR-5)
                print(f"[biodiversity] {p.name} failed: {exc}", flush=True)
        return out
