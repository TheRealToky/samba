import { useEffect, useRef, useState } from "react";
import maplibregl from "maplibre-gl";
import { api } from "../api";
import { IUCN_COLOR, IUCN_LABEL, speciesMeta, statusKey } from "../lib/species";

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

const obsColor: any = ["match", ["get", "conservation_status"]];
for (const key of ["CR", "EN", "VU", "NT", "LC", "DD"]) obsColor.push(key, IUCN_COLOR[key]);
obsColor.push(IUCN_COLOR.NA);

export default function MapView() {
  const ref = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const obsRef = useRef<any>(null);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showObs, setShowObs] = useState(false);

  useEffect(() => {
    let cancelled = false;
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
      for (const f of geo.features) f.properties.loss = lossByCode.get(f.properties.code) ?? 0;

      if (cancelled || !ref.current) return;
      const map = new maplibregl.Map({ container: ref.current, style: BASE_STYLE as any, center: [46.7, -18.9], zoom: 4.6 });
      mapRef.current = map;
      map.addControl(new maplibregl.NavigationControl(), "top-right");

      map.on("load", () => {
        map.addSource("regions", { type: "geojson", data: geo });
        map.addLayer({
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
        map.addLayer({ id: "region-line", type: "line", source: "regions", paint: { "line-color": "#ffffff", "line-width": 1.2 } });
        map.addLayer({
          id: "region-label",
          type: "symbol",
          source: "regions",
          layout: { "text-field": ["get", "name"], "text-size": 12 },
          paint: { "text-color": "#12321a", "text-halo-color": "#ffffff", "text-halo-width": 1.4 },
        });

        map.on("click", "region-fill", (e) => {
          const f = e.features?.[0];
          if (!f) return;
          const p = f.properties as any;
          const loss = Number(p.loss);
          new maplibregl.Popup()
            .setLngLat(e.lngLat)
            .setHTML(
              `<strong>${p.name}</strong><br/>Biome: ${p.biome ?? "—"}<br/>` +
                `NDVI loss: ${loss.toFixed(3)}<br/>Status: ${
                  loss > 0.08 ? '<b style="color:#c62828">deforestation</b>' : "stable"
                }`
            )
            .addTo(map);
        });
        map.on("mouseenter", "region-fill", () => (map.getCanvas().style.cursor = "pointer"));
        map.on("mouseleave", "region-fill", () => (map.getCanvas().style.cursor = ""));
        setLoaded(true);
      });
    })().catch((err) => {
      console.error(err);
      if (!cancelled) setError(err instanceof Error ? err.message : String(err));
    });

    return () => {
      cancelled = true;
      mapRef.current?.remove();
      mapRef.current = null;
    };
  }, []);

  // Lazily add / toggle the species-observation overlay.
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !loaded) return;

    async function ensureObs() {
      if (!obsRef.current) {
        obsRef.current = await api.get<any>("/species/observations/geojson?limit=2000");
        map!.addSource("obs", { type: "geojson", data: obsRef.current });
        map!.addLayer({
          id: "obs-pts",
          type: "circle",
          source: "obs",
          paint: {
            "circle-radius": ["interpolate", ["linear"], ["zoom"], 4, 3, 8, 6],
            "circle-color": obsColor,
            "circle-stroke-color": "#fff",
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
          new maplibregl.Popup()
            .setLngLat(e.lngLat)
            .setHTML(
              `<div style="font-size:12px;line-height:1.5"><strong style="font-style:italic">${p.scientific_name}</strong><br/>` +
                `${meta.common} · ${meta.group}<br/>Status: <b style="color:${IUCN_COLOR[key]}">${IUCN_LABEL[key]}</b><br/>` +
                `Region: ${p.region ?? "—"} · ${p.source}</div>`
            )
            .addTo(map!);
        });
        map!.on("mouseenter", "obs-pts", () => (map!.getCanvas().style.cursor = "pointer"));
        map!.on("mouseleave", "obs-pts", () => (map!.getCanvas().style.cursor = ""));
      }
      map!.setLayoutProperty("obs-pts", "visibility", showObs ? "visible" : "none");
    }

    if (showObs) ensureObs().catch((e) => console.error(e));
    else if (obsRef.current && map.getLayer("obs-pts")) map.setLayoutProperty("obs-pts", "visibility", "none");
  }, [showObs, loaded]);

  return (
    <div>
      <div className="section-title">
        <div>
          <h1>Interactive Environmental Map</h1>
          <div className="subtitle">Regional deforestation risk with an optional species-observation overlay.</div>
        </div>
      </div>
      <div className="panel">
        <div className="map-toolbar">
          <div className="toggle-group">
            <button className="on" disabled>Forest loss</button>
          </div>
          <div className="toggle-group">
            <button className={showObs ? "" : "on"} onClick={() => setShowObs(false)}>Hide species</button>
            <button className={showObs ? "on" : ""} onClick={() => setShowObs(true)}>Show observations</button>
          </div>
        </div>
        <div className="map-wrap" ref={ref} />
        <div className="legend">
          <span><span className="swatch" style={{ background: "#2e7d32" }} />Stable</span>
          <span><span className="swatch" style={{ background: "#c8b900" }} />Low loss</span>
          <span><span className="swatch" style={{ background: "#ef6c00" }} />Moderate</span>
          <span><span className="swatch" style={{ background: "#c62828" }} />High loss</span>
          {showObs && <span style={{ marginLeft: 6 }}><span className="dot" style={{ background: IUCN_COLOR.CR }} />observations by IUCN status</span>}
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
