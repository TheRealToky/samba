import { useEffect, useRef, useState } from "react";
import maplibregl from "maplibre-gl";
import { api } from "../api";
import { IUCN_COLOR, IUCN_LABEL, speciesMeta, statusKey } from "../lib/species";

const BASE_STYLE = {
  version: 8 as const,
  sources: {
    osm: {
      type: "raster" as const,
      tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
      tileSize: 256,
      attribution: "© OpenStreetMap contributors",
    },
  },
  glyphs: "https://demotiles.maplibre.org/font/{fontstack}/{range}.pbf",
  layers: [{ id: "osm", type: "raster" as const, source: "osm" }],
};

// Data-driven circle color: one branch per IUCN category.
const colorExpr: any = ["match", ["get", "conservation_status"]];
for (const key of ["CR", "EN", "VU", "NT", "LC", "DD"]) {
  colorExpr.push(key, IUCN_COLOR[key]);
}
colorExpr.push(IUCN_COLOR.NA);

export default function ObservationMap({ height = 480 }: { height?: number }) {
  const ref = useRef<HTMLDivElement>(null);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [count, setCount] = useState(0);

  useEffect(() => {
    let cancelled = false;
    let map: maplibregl.Map | null = null;
    (async () => {
      const geo = await api.get<any>("/species/observations/geojson?limit=2000");
      if (cancelled || !ref.current) return;
      setCount(geo.features?.length ?? 0);

      map = new maplibregl.Map({
        container: ref.current,
        style: BASE_STYLE as any,
        center: [46.9, -19.0],
        zoom: 4.6,
      });
      map.addControl(new maplibregl.NavigationControl(), "top-right");

      map.on("load", () => {
        map!.addSource("obs", { type: "geojson", data: geo });
        map!.addLayer({
          id: "obs-pts",
          type: "circle",
          source: "obs",
          paint: {
            "circle-radius": ["interpolate", ["linear"], ["zoom"], 4, 3.2, 8, 6],
            "circle-color": colorExpr,
            "circle-stroke-color": "#ffffff",
            "circle-stroke-width": 1,
            "circle-opacity": 0.85,
          },
        });

        map!.on("click", "obs-pts", (e) => {
          const f = e.features?.[0];
          if (!f) return;
          const p = f.properties as any;
          const meta = speciesMeta(p.scientific_name);
          const key = statusKey(p.conservation_status);
          const when = p.date ? String(p.date).slice(0, 10) : "—";
          new maplibregl.Popup()
            .setLngLat(e.lngLat)
            .setHTML(
              `<div style="font-size:12px;line-height:1.5">` +
                `<strong style="font-style:italic">${p.scientific_name}</strong><br/>` +
                `${meta.common} · ${meta.group}<br/>` +
                `Status: <b style="color:${IUCN_COLOR[key]}">${IUCN_LABEL[key]}</b><br/>` +
                `Region: ${p.region ?? "—"} · ${p.source}<br/>` +
                `Seen: ${when}</div>`
            )
            .addTo(map!);
        });
        map!.on("mouseenter", "obs-pts", () => (map!.getCanvas().style.cursor = "pointer"));
        map!.on("mouseleave", "obs-pts", () => (map!.getCanvas().style.cursor = ""));
        setLoaded(true);
      });
    })().catch((err) => {
      console.error(err);
      if (!cancelled) setError(err instanceof Error ? err.message : String(err));
    });

    return () => {
      cancelled = true;
      map?.remove();
    };
  }, []);

  return (
    <div>
      <div className="map-wrap" style={{ height }} ref={ref} />
      <div className="legend">
        {["CR", "EN", "VU", "NT", "LC"].map((k) => (
          <span key={k}><span className="dot" style={{ background: IUCN_COLOR[k] }} />{k} — {IUCN_LABEL[k]}</span>
        ))}
        {error ? (
          <span className="error">map failed to load: {error}</span>
        ) : !loaded ? (
          <span className="muted">loading {count || ""} observations…</span>
        ) : (
          <span className="muted">{count.toLocaleString()} observation points</span>
        )}
      </div>
    </div>
  );
}
