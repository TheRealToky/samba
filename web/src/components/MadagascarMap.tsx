import { useMemo, useState } from "react";
import { MAP_VIEWBOX, REGION_SHAPES } from "../lib/madagascar";

/** One row of `/climate/regional`, keyed by region name. */
export interface RegionSignal {
  region_name: string;
  biome: string;
  avg_temperature: number | null;
  ndvi_change: number | null;
}

/** Vegetation-loss bands (loss = -ndvi_change), tuned to read on the dark hero. */
const BANDS = [
  { min: 0.08, color: "#ef4444", label: "Severe loss" },
  { min: 0.05, color: "#f97316", label: "High loss" },
  { min: 0.02, color: "#f5b301", label: "Moderate loss" },
  { min: -Infinity, color: "#4ade80", label: "Stable / recovering" },
];

/** Vegetation loss for a region; positive = losing greenness. */
const loss = (s: RegionSignal | undefined) => (s && s.ndvi_change != null ? -s.ndvi_change : null);

const bandFor = (l: number | null) => (l == null ? null : BANDS.find((b) => l >= b.min)!);

/**
 * Live choropleth of Madagascar's regions, drawn from baked-in simplified
 * PostGIS geometry (see lib/madagascar.ts) and coloured by the vegetation-loss
 * signal the API returns. Renders neutral — and still looks intentional — when
 * the API is unreachable.
 */
export default function MadagascarMap({ signals }: { signals: RegionSignal[] }) {
  const [hover, setHover] = useState<{ code: string; x: number; y: number } | null>(null);

  const byName = useMemo(() => {
    const m = new Map<string, RegionSignal>();
    for (const s of signals) m.set(s.region_name, s);
    return m;
  }, [signals]);

  /** Three worst-hit regions get a pulsing monitoring marker. */
  const hotspots = useMemo(
    () =>
      REGION_SHAPES.map((r) => ({ shape: r, loss: loss(byName.get(r.name)) }))
        .filter((r) => r.loss != null)
        .sort((a, b) => (b.loss as number) - (a.loss as number))
        .slice(0, 3),
    [byName]
  );

  const hovered = hover ? REGION_SHAPES.find((r) => r.code === hover.code) : null;
  const hoveredSignal = hovered ? byName.get(hovered.name) : null;

  return (
    <div className="lp-map">
      <svg
        viewBox={`-6 -6 ${MAP_VIEWBOX.w + 12} ${MAP_VIEWBOX.h + 12}`}
        className="lp-map-svg"
        role="img"
        aria-label="Map of Madagascar's regions shaded by recent vegetation loss"
        onMouseLeave={() => setHover(null)}
      >
        <defs>
          <radialGradient id="lp-halo" cx="50%" cy="45%" r="60%">
            <stop offset="0%" stopColor="#5eead4" stopOpacity="0.22" />
            <stop offset="100%" stopColor="#5eead4" stopOpacity="0" />
          </radialGradient>
          <linearGradient id="lp-scan" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#a7f3d0" stopOpacity="0" />
            <stop offset="55%" stopColor="#a7f3d0" stopOpacity="0.5" />
            <stop offset="100%" stopColor="#a7f3d0" stopOpacity="0" />
          </linearGradient>
          <clipPath id="lp-island">
            {REGION_SHAPES.map((r) => (
              <path key={r.code} d={r.d} />
            ))}
          </clipPath>
        </defs>

        <ellipse
          cx={MAP_VIEWBOX.w / 2}
          cy={MAP_VIEWBOX.h / 2}
          rx={MAP_VIEWBOX.w * 0.8}
          ry={MAP_VIEWBOX.h * 0.55}
          fill="url(#lp-halo)"
        />

        <g className="lp-map-regions">
          {REGION_SHAPES.map((r) => {
            const band = bandFor(loss(byName.get(r.name)));
            const on = hover?.code === r.code;
            return (
              <path
                key={r.code}
                d={r.d}
                fill={band ? band.color : "#ffffff"}
                fillOpacity={band ? (on ? 0.95 : 0.62) : on ? 0.22 : 0.1}
                stroke={on ? "#ffffff" : "rgba(255,255,255,0.34)"}
                strokeWidth={on ? 1.4 : 0.7}
                onMouseMove={(e) => {
                  const box = e.currentTarget.ownerSVGElement!.getBoundingClientRect();
                  setHover({
                    code: r.code,
                    x: e.clientX - box.left,
                    y: e.clientY - box.top,
                  });
                }}
              >
                <title>{r.name}</title>
              </path>
            );
          })}
        </g>

        {/* Satellite sweep — pure decoration, clipped to the island. */}
        <g clipPath="url(#lp-island)">
          <rect
            className="lp-map-scan"
            x={-10}
            y={-70}
            width={MAP_VIEWBOX.w + 20}
            height={70}
            fill="url(#lp-scan)"
          />
        </g>

        {hotspots.map(({ shape }) => (
          <g key={shape.code} className="lp-map-hotspot">
            <circle className="lp-map-ping" cx={shape.cx} cy={shape.cy} r={5} />
            <circle cx={shape.cx} cy={shape.cy} r={3} fill="#fff" />
          </g>
        ))}
      </svg>

      {hovered && (
        <div
          className="lp-map-tip"
          style={{ left: hover!.x, top: hover!.y }}
          role="status"
        >
          <strong>{hovered.name}</strong>
          <span className="lp-map-tip-biome">{hovered.biome.replace(/_/g, " ")}</span>
          {hoveredSignal?.ndvi_change != null ? (
            <span className="lp-map-tip-row">
              NDVI {hoveredSignal.ndvi_change >= 0 ? "+" : ""}
              {hoveredSignal.ndvi_change.toFixed(3)}
              {hoveredSignal.avg_temperature != null && ` · ${hoveredSignal.avg_temperature.toFixed(1)}°C`}
            </span>
          ) : (
            <span className="lp-map-tip-row">No reading yet</span>
          )}
        </div>
      )}

      <div className="lp-map-legend">
        {BANDS.map((b) => (
          <span key={b.label}>
            <i style={{ background: b.color }} />
            {b.label}
          </span>
        ))}
      </div>
    </div>
  );
}
