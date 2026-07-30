"""Bake the simplified region polygons exported from PostGIS into a compact
TS module of SVG paths (equirectangular projection, fitted to a 0..W viewBox)."""
import json
import math
import sys

SRC = sys.argv[1]
OUT = sys.argv[2]
W = 300.0  # viewBox width; height derived from aspect

rows = json.load(open(SRC, encoding="utf-8"))
for r in rows:
    r["geom"] = json.loads(r["g"])

# --- collect rings -----------------------------------------------------------
def rings(geom):
    if geom["type"] == "Polygon":
        return [geom["coordinates"][0]]
    if geom["type"] == "MultiPolygon":
        return [p[0] for p in geom["coordinates"]]
    return []

def ring_area(ring):
    a = 0.0
    for i in range(len(ring) - 1):
        x1, y1 = ring[i][0], ring[i][1]
        x2, y2 = ring[i + 1][0], ring[i + 1][1]
        a += x1 * y2 - x2 * y1
    return abs(a) / 2.0

all_pts = [pt for r in rows for ring in rings(r["geom"]) for pt in ring]
lons = [p[0] for p in all_pts]
lats = [p[1] for p in all_pts]
min_lon, max_lon = min(lons), max(lons)
min_lat, max_lat = min(lats), max(lats)
mid_lat = (min_lat + max_lat) / 2.0
kx = math.cos(math.radians(mid_lat))  # equirectangular longitude correction

span_x = (max_lon - min_lon) * kx
span_y = max_lat - min_lat
scale = W / span_x
H = span_y * scale

def proj(lon, lat):
    return ((lon - min_lon) * kx * scale, (max_lat - lat) * scale)

def path_for(geom):
    out = []
    rs = rings(geom)
    biggest = max(ring_area(r) for r in rs) if rs else 0
    for ring in rs:
        # drop specks (offshore islets) — they add bytes, not signal
        if ring_area(ring) < biggest * 0.02:
            continue
        pts = []
        last = None
        for lon, lat in ring:
            x, y = proj(lon, lat)
            s = f"{x:.1f},{y:.1f}"
            if s != last:
                pts.append(s)
                last = s
        if len(pts) < 3:
            continue
        out.append("M" + "L".join(pts) + "Z")
    return "".join(out)

entries = []
for r in rows:
    cx, cy = proj(float(r["cx"]), float(r["cy"]))
    entries.append(
        {
            "code": r["code"],
            "name": r["name"],
            "biome": r["biome"],
            "cx": round(cx, 1),
            "cy": round(cy, 1),
            "d": path_for(r["geom"]),
        }
    )

lines = [
    "// AUTO-GENERATED from the PostGIS `regions` table (ST_SimplifyPreserveTopology,",
    "// tolerance 0.035°), projected equirectangular and fitted to the viewBox below.",
    "// Regenerate with the SQL + script noted in web/README.md when regions change.",
    "",
    "export interface RegionShape {",
    "  code: string;",
    "  name: string;",
    "  biome: string;",
    "  /** Label/marker anchor inside the polygon, in viewBox units. */",
    "  cx: number;",
    "  cy: number;",
    "  /** SVG path data in viewBox units. */",
    "  d: string;",
    "}",
    "",
    f"export const MAP_VIEWBOX = {{ w: {W:.0f}, h: {H:.1f} }};",
    "",
    "export const REGION_SHAPES: RegionShape[] = [",
]
for e in entries:
    lines.append(
        "  { code: %s, name: %s, biome: %s, cx: %s, cy: %s, d: %s },"
        % (
            json.dumps(e["code"]),
            json.dumps(e["name"]),
            json.dumps(e["biome"]),
            e["cx"],
            e["cy"],
            json.dumps(e["d"]),
        )
    )
lines.append("];")
lines.append("")

open(OUT, "w", encoding="utf-8").write("\n".join(lines))
print(f"regions={len(entries)} viewBox={W:.0f}x{H:.1f} bytes={sum(len(l) for l in lines)}")
