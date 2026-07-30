"""EnrichmentService fills conservation_status from an IucnEnricher (stubbed)."""
from __future__ import annotations

import uuid

from app.db import SessionLocal
from app.ingestion.enrichment import SpeciesStatus
from app.models.species import Species
from app.services.enrichment_service import EnrichmentService


class _StubEnricher:
    name = "stub"

    def __init__(self, mapping: dict[str, str]):
        self.mapping = mapping

    def status_for(self, scientific_name: str) -> SpeciesStatus | None:
        code = self.mapping.get(scientific_name)
        return SpeciesStatus(conservation_status=code) if code else None


def test_enrich_fills_missing_status():
    name = f"Testus specius {uuid.uuid4().hex[:8]}"
    with SessionLocal() as db:
        sp = Species(scientific_name=name, conservation_status=None)
        db.add(sp)
        db.commit()
        sid = sp.id

        result = EnrichmentService(db, _StubEnricher({name: "EN"})).enrich_missing(throttle=0)

        assert result["enriched"] >= 1
        assert db.get(Species, sid).conservation_status == "EN"


def test_enrich_leaves_unknown_species_untouched():
    name = f"Ignotus specius {uuid.uuid4().hex[:8]}"
    with SessionLocal() as db:
        sp = Species(scientific_name=name, conservation_status=None)
        db.add(sp)
        db.commit()
        sid = sp.id

        # Stub returns nothing for this name -> status stays NULL.
        EnrichmentService(db, _StubEnricher({})).enrich_missing(throttle=0)

        assert db.get(Species, sid).conservation_status is None
