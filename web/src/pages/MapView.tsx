import { useEffect, useRef, useState } from "react";
import maplibregl from "maplibre-gl";
import { api } from "../api";

interface Region { id: number; code: string; name: string; }
interface DefEvent { region_id: number; vegetation_loss: number; }

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

export default function MapView() {
  const ref = useRef<HTMLDivElement>(null);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    let map: maplibregl.Map | null = null;
    (async () => {
      const [regions, events, geo] = await Promise.all([
        api.get<Region[]>("/regions"),
        api.get<DefEvent[]>("/deforestation-events"),
        api.get<any>("/regions/geojson"),
      ]);
      const codeById = new Map(regions.map((r) => [r.id, r.code]));
      const lossByCode = new Map<string, number>();
      for (const e of events) {
        const code = codeById.get(e.region_id);
        if (code) lossByCode.set(code, Math.max(lossByCode.get(code) ?? 0, e.vegetation_loss));
      }
      for (const f of geo.features) {
        f.properties.loss = lossByCode.get(f.properties.code) ?? 0;
      }

      if (cancelled || !ref.current) return;
      map = new maplibregl.Map({
        container: ref.current,
        style: BASE_STYLE as any,
        center: [46.7, -18.9],
        zoom: 4.6,
      });
      map.addControl(new maplibregl.NavigationControl(), "top-right");

      map.on("load", () => {
        map!.addSource("regions", { type: "geojson", data: geo });
        map!.addLayer({
          id: "region-fill",
          type: "fill",
          source: "regions",
          paint: {
            "fill-color": [
              "interpolate", ["linear"], ["get", "loss"],
              0, "#2e7d32", 0.05, "#c8b900", 0.12, "#ef6c00", 0.2, "#c62828",
            ],
            "fill-opacity": 0.72,
          },
        });
        map!.addLayer({
          id: "region-line",
          type: "line",
          source: "regions",
          paint: { "line-color": "#ffffff", "line-width": 1.2 },
        });
        map!.addLayer({
          id: "region-label",
          type: "symbol",
          source: "regions",
          layout: { "text-field": ["get", "name"], "text-size": 12 },
          paint: { "text-color": "#12321a", "text-halo-color": "#ffffff", "text-halo-width": 1.4 },
        });

        map!.on("click", "region-fill", (e) => {
          const f = e.features?.[0];
          if (!f) return;
          const p = f.properties as any;
          const loss = Number(p.loss);
          new maplibregl.Popup()
            .setLngLat(e.lngLat)
            .setHTML(
              `<strong>${p.name}</strong><br/>Biome: ${p.biome ?? "—"}<br/>` +
                `NDVI loss: ${loss.toFixed(3)}<br/>` +
                `Status: ${loss > 0.08 ? "⚠️ deforestation" : "stable"}`
            )
            .addTo(map!);
        });
        map!.on("mouseenter", "region-fill", () => (map!.getCanvas().style.cursor = "pointer"));
        map!.on("mouseleave", "region-fill", () => (map!.getCanvas().style.cursor = ""));
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
      <div className="section-title">
        <h1>Deforestation Risk Map</h1>
      </div>
      <div className="panel">
        <div className="map-wrap" ref={ref} />
        <div className="legend">
          <span><span className="swatch" style={{ background: "#2e7d32" }} />Stable</span>
          <span><span className="swatch" style={{ background: "#c8b900" }} />Low loss</span>
          <span><span className="swatch" style={{ background: "#ef6c00" }} />Moderate</span>
          <span><span className="swatch" style={{ background: "#c62828" }} />High loss</span>
          {error ? (
            <span className="error">map failed to load: {error}</span>
          ) : (
            !loaded && <span className="muted">loading map…</span>
          )}
        </div>
      </div>
    </div>
  );
}
