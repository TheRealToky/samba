"""EnrichmentService — fill Species.conservation_status for species that lack it
(Stage 3). Takes any IucnEnricher, so it's unit-testable with a stub (no network).
"""
from __future__ import annotations

import time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ingestion.enrichment import IucnEnricher
from app.models.species import Species

_COMMIT_EVERY = 25


class EnrichmentService:
    def __init__(self, db: Session, enricher: IucnEnricher):
        self.db = db
        self.enricher = enricher

    def enrich_missing(self, limit: int | None = None, throttle: float = 0.2) -> dict:
        """Look up an IUCN category for every species with no conservation_status.

        Commits in batches so a mid-run failure keeps progress. `throttle` spaces
        out external calls; set 0 in tests."""
        query = select(Species).where(Species.conservation_status.is_(None)).order_by(Species.id)
        if limit:
            query = query.limit(limit)
        species = list(self.db.execute(query).scalars().all())

        enriched = 0
        try:
            for i, sp in enumerate(species, start=1):
                try:
                    status = self.enricher.status_for(sp.scientific_name)
                except Exception as exc:  # one bad name shouldn't sink the batch
                    print(f"[enrichment] {sp.scientific_name} failed: {exc}", flush=True)
                    status = None
                if status and status.conservation_status:
                    sp.conservation_status = status.conservation_status
                    if status.endemic is not None:
                        sp.endemic = status.endemic
                    enriched += 1
                if i % _COMMIT_EVERY == 0:
                    self.db.commit()
                if throttle:
                    time.sleep(throttle)
            self.db.commit()
        finally:
            close = getattr(self.enricher, "close", None)
            if callable(close):
                close()
        return {"checked": len(species), "enriched": enriched}
