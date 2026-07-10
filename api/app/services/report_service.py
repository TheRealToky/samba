"""Report generation + export (FR-5.1, FR-5.2).

Builds a regional environmental summary and exports it as CSV or PDF, stores the
file in object storage, and records a Report row (Report.generate()/export()).
"""
from __future__ import annotations

import csv
import io
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.alert import EnvironmentalAlert
from app.models.ml import DeforestationEvent
from app.models.region import Region
from app.models.report import Report
from app.processing.alignment import ndvi_series
from app.services.species_service import SpeciesService
from app.storage.objectstore import put_bytes

_COLUMNS = [
    "region_code", "region_name", "biome",
    "ndvi_start", "ndvi_end", "ndvi_change",
    "deforestation", "vegetation_loss",
    "species_richness", "observations", "active_alerts",
]


class ReportService:
    def __init__(self, db: Session):
        self.db = db

    def build_summary(self) -> list[dict]:
        regions = list(self.db.execute(select(Region).order_by(Region.name)).scalars().all())
        richness = {r["region_code"]: r for r in SpeciesService(self.db).richness_by_region()}
        rows: list[dict] = []
        for region in regions:
            series = ndvi_series(self.db, region.id)
            ndvi_start = round(series[0][1], 4) if series else None
            ndvi_end = round(series[-1][1], 4) if series else None
            ndvi_change = round(ndvi_end - ndvi_start, 4) if series else None
            event = self.db.execute(
                select(DeforestationEvent).where(DeforestationEvent.region_id == region.id)
            ).scalars().first()
            alerts = self.db.scalar(
                select(func.count(EnvironmentalAlert.id)).where(EnvironmentalAlert.region_id == region.id)
            )
            rich = richness.get(region.code, {})
            rows.append(
                {
                    "region_code": region.code,
                    "region_name": region.name,
                    "biome": region.biome,
                    "ndvi_start": ndvi_start,
                    "ndvi_end": ndvi_end,
                    "ndvi_change": ndvi_change,
                    "deforestation": "yes" if event else "no",
                    "vegetation_loss": round(event.vegetation_loss, 4) if event else 0.0,
                    "species_richness": rich.get("species_richness", 0),
                    "observations": rich.get("observations", 0),
                    "active_alerts": int(alerts or 0),
                }
            )
        return rows

    def _csv_bytes(self, rows: list[dict]) -> bytes:
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
        return buf.getvalue().encode("utf-8")

    def _pdf_bytes(self, rows: list[dict]) -> bytes:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.units import cm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet

        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=landscape(A4), topMargin=1 * cm, bottomMargin=1 * cm)
        styles = getSampleStyleSheet()
        elements = [
            Paragraph("SAMBA — Regional Environmental Summary", styles["Title"]),
            Paragraph(f"Generated {datetime.now(timezone.utc):%Y-%m-%d %H:%M UTC}", styles["Normal"]),
            Spacer(1, 0.4 * cm),
        ]
        header = ["Region", "Biome", "NDVI start", "NDVI end", "Δ NDVI", "Deforest.", "Veg. loss", "Richness", "Obs.", "Alerts"]
        data = [header] + [
            [
                r["region_name"], r["biome"] or "-", r["ndvi_start"], r["ndvi_end"], r["ndvi_change"],
                r["deforestation"], r["vegetation_loss"], r["species_richness"], r["observations"], r["active_alerts"],
            ]
            for r in rows
        ]
        table = Table(data, repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1b5e20")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f4f0")]),
                    ("ALIGN", (2, 1), (-1, -1), "CENTER"),
                ]
            )
        )
        elements.append(table)
        doc.build(elements)
        return buf.getvalue()

    def generate(self, fmt: str, user_id: int | None = None, params: dict | None = None) -> Report:
        fmt = fmt.lower()
        if fmt not in ("csv", "pdf"):
            raise ValueError("format must be 'csv' or 'pdf'")
        rows = self.build_summary()
        if fmt == "csv":
            content, content_type = self._csv_bytes(rows), "text/csv"
        else:
            content, content_type = self._pdf_bytes(rows), "application/pdf"

        report = Report(format=fmt, user_id=user_id, params=params or {})
        self.db.add(report)
        self.db.flush()  # get id
        key = f"reports/report_{report.id}.{fmt}"
        put_bytes(key, content, content_type)
        report.object_key = key
        self.db.commit()
        self.db.refresh(report)
        return report
