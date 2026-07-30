"""Species enrichment: resolve IUCN Red List category by scientific name.

Live GBIF/iNaturalist occurrences arrive without a conservation status, so after
ingestion the Species table needs a second pass to fill it in (Stage 3). The
default enricher uses GBIF's IUCN Red List category endpoint — auth-free, like
the rest of the live stack. The official IUCN Red List API (token-gated, more
authoritative) can be added later behind the same `IucnEnricher` interface.

Endemism is intentionally not set here: there is no reliable auth-free
per-country endemism signal, so `Species.endemic` is left untouched.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

import httpx

from app.ingestion.biodiversity import _USER_AGENT, _get_json


@dataclass
class SpeciesStatus:
    conservation_status: str | None
    endemic: bool | None = None  # None = "unknown, don't overwrite"


@runtime_checkable
class IucnEnricher(Protocol):
    name: str

    def status_for(self, scientific_name: str) -> SpeciesStatus | None:
        ...


class GBIFIucnEnricher:
    """IUCN category via GBIF: name -> backbone taxon key -> IUCN category."""

    name = "gbif_iucn"
    _MATCH_URL = "https://api.gbif.org/v1/species/match"
    _IUCN_URL = "https://api.gbif.org/v1/species/{key}/iucnRedListCategory"

    _CODES = {"CR", "EN", "VU", "NT", "LC", "DD", "EW", "EX", "NE"}
    _WORD_TO_CODE = {
        "CRITICALLY_ENDANGERED": "CR",
        "ENDANGERED": "EN",
        "VULNERABLE": "VU",
        "NEAR_THREATENED": "NT",
        "LEAST_CONCERN": "LC",
        "DATA_DEFICIENT": "DD",
        "EXTINCT_IN_THE_WILD": "EW",
        "EXTINCT": "EX",
        "NOT_EVALUATED": "NE",
    }

    def __init__(self) -> None:
        self._client: httpx.Client | None = None

    def _get_client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(timeout=30, headers={"User-Agent": _USER_AGENT})
        return self._client

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None

    def status_for(self, scientific_name: str) -> SpeciesStatus | None:
        client = self._get_client()
        match = _get_json(client, self._MATCH_URL, {"name": scientific_name, "strict": "false"})
        key = match.get("usageKey")
        if key is None or match.get("matchType") == "NONE":
            return None
        body = _get_json(client, self._IUCN_URL.format(key=key), {})
        code = (body.get("code") or "").upper()
        if code not in self._CODES:
            code = self._WORD_TO_CODE.get((body.get("category") or "").upper(), "")
        if not code or code == "NE":
            return None
        return SpeciesStatus(conservation_status=code)
