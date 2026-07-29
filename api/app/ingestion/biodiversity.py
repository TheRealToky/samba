"""Biodiversity providers: GBIF + iNaturalist (live) + deterministic sample.

Both read APIs are auth-free. A composite provider merges them: GBIF is the
canonical bulk source (it already aggregates iNaturalist research-grade records),
and iNaturalist is pulled from the recent tail of the window (width set by
`settings.biodiversity_inat_recent_days`; 0 = full window) to feed the
community/photo use case while keeping overlap — and double-counting — bounded.

Live pulls paginate up to `limit` records/region and set a descriptive
User-Agent (iNaturalist requests one). Conservation status / endemism are left
unset here; that enrichment is Stage 3.
"""
from __future__ import annotations

import time
from datetime import datetime, timedelta

import httpx

from app.config import settings
from app.ingestion.base import ObservationRecord
from app.ingestion.sampling import sample_observations

_GBIF_URL = "https://api.gbif.org/v1/occurrence/search"
_INAT_URL = "https://api.inaturalist.org/v1/observations"
_USER_AGENT = "SAMBA/0.1 (Madagascar biodiversity monitoring; +https://github.com/samba)"

# GBIF caps a page at 300; iNaturalist at 200 (and page*per_page <= 10_000).
_GBIF_PAGE = 300
_INAT_PAGE = 200
_INAT_MAX_OFFSET = 10_000


def _get_json(client: httpx.Client, url: str, params: dict, retries: int = 3) -> dict:
    """GET with small backoff on transient network/5xx errors."""
    for attempt in range(retries):
        try:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            return resp.json()
        except (httpx.TransportError, httpx.HTTPStatusError) as exc:
            if attempt == retries - 1:
                raise
            print(f"[biodiversity] retry {attempt + 1} for {url}: {exc}", flush=True)
            time.sleep(1.5 * (attempt + 1))
    return {}  # unreachable


class GBIFProvider:
    name = "gbif"

    def __init__(self, mode: str = "sample"):
        self.mode = mode

    def fetch_observations(self, region, start, end, limit) -> list[ObservationRecord]:
        if self.mode != "live":
            return [r for r in sample_observations(region, start, end, limit) if r.source == "gbif"]
        return self._fetch_live(region, start, end, limit)

    def _fetch_live(self, region, start, end, limit) -> list[ObservationRecord]:
        bbox = region.get("bbox")
        if bbox is None:  # custom region without geometry — can't spatially filter
            return []
        lon_min, lat_min, lon_max, lat_max = bbox
        out: list[ObservationRecord] = []
        offset = 0
        with httpx.Client(timeout=60, headers={"User-Agent": _USER_AGENT}) as client:
            while len(out) < limit:
                params = {
                    "country": "MG",
                    "hasCoordinate": "true",
                    "decimalLatitude": f"{lat_min},{lat_max}",
                    "decimalLongitude": f"{lon_min},{lon_max}",
                    "year": f"{start.year},{end.year}",
                    "limit": min(_GBIF_PAGE, limit - len(out)),
                    "offset": offset,
                }
                body = _get_json(client, _GBIF_URL, params)
                results = body.get("results", [])
                if not results:
                    break
                for rec in results:
                    obs = _gbif_record(rec, start)
                    if obs is not None:
                        out.append(obs)
                offset += len(results)
                if body.get("endOfRecords"):
                    break
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
        bbox = region.get("bbox")
        if bbox is None:
            return []
        lon_min, lat_min, lon_max, lat_max = bbox
        # Recent tail only (see module docstring); configurable, 0 = full window.
        recent_days = settings.biodiversity_inat_recent_days
        d1 = start if recent_days <= 0 else max(start, end - timedelta(days=recent_days))
        out: list[ObservationRecord] = []
        page = 1
        with httpx.Client(timeout=60, headers={"User-Agent": _USER_AGENT}) as client:
            while len(out) < limit and page * _INAT_PAGE <= _INAT_MAX_OFFSET:
                params = {
                    "nelat": lat_max, "nelng": lon_max, "swlat": lat_min, "swlng": lon_min,
                    "d1": d1.strftime("%Y-%m-%d"), "d2": end.strftime("%Y-%m-%d"),
                    "geo": "true", "per_page": min(_INAT_PAGE, limit - len(out)),
                    "order_by": "observed_on", "page": page,
                }
                body = _get_json(client, _INAT_URL, params)
                results = body.get("results", [])
                if not results:
                    break
                for rec in results:
                    obs = _inat_record(rec, start)
                    if obs is not None:
                        out.append(obs)
                page += 1
                time.sleep(1.0)  # iNaturalist asks for <= ~60 requests/minute
        return out


def _gbif_record(rec: dict, start: datetime) -> ObservationRecord | None:
    # Prefer GBIF's canonical `species` over `scientificName` (which carries the
    # author string) so names match across sources and the Species table.
    name = rec.get("species") or rec.get("scientificName")
    lat, lon = rec.get("decimalLatitude"), rec.get("decimalLongitude")
    if not name or lat is None or lon is None:
        return None
    year = rec.get("year") or start.year
    return ObservationRecord(
        date=datetime(int(year), int(rec.get("month") or 1), int(rec.get("day") or 1), tzinfo=start.tzinfo),
        scientific_name=str(name).split(" (")[0].strip(),
        lon=float(lon),
        lat=float(lat),
        source="gbif",
        conservation_status=None,
        endemic=False,
        extra={"gbif_key": rec.get("key")},
    )


def _inat_record(rec: dict, start: datetime) -> ObservationRecord | None:
    taxon = rec.get("taxon") or {}
    name = taxon.get("name")
    geo = rec.get("geojson") or {}
    coords = geo.get("coordinates")
    if not name or not coords:
        return None
    observed = rec.get("observed_on") or start.strftime("%Y-%m-%d")
    try:
        d = datetime.fromisoformat(observed).replace(tzinfo=start.tzinfo)
    except ValueError:
        d = start
    return ObservationRecord(
        date=d,
        scientific_name=str(name).strip(),
        lon=float(coords[0]),
        lat=float(coords[1]),
        source="inaturalist",
        conservation_status=None,
        endemic=False,
        extra={"inat_id": rec.get("id")},
    )


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
