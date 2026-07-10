import { useEffect, useMemo, useState } from "react";
import {
  Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { api } from "../api";
import { Kpi, PanelHead, SpeciesPhoto, StatusChip } from "../components/ui";
import {
  IconAlertTriangle, IconGlobe, IconMapPin, IconPaw, TaxonIcon,
} from "../components/icons";
import ObservationMap from "../components/ObservationMap";
import { CHART, IUCN_LABEL, speciesMeta, statusKey } from "../lib/species";

interface TopSpecies {
  species_id: number; scientific_name: string; conservation_status: string | null;
  endemic: boolean; observations: number; regions: number; last_seen: string | null;
}
interface StatusRow { status: string; species: number; observations: number; }
interface TrendRow { month: string; gbif: number; inaturalist: number; upload: number; total: number; }
interface Risk {
  scientific_name: string; conservation_status: string | null; endemic: boolean;
  observations_at_risk: number; regions: string[]; max_loss: number; risk_score: number; risk_level: string;
}
interface Summary { species: number; species_observations: number; }

const monthLabel = (m: string) => m.slice(0, 7);

export default function Biodiversity() {
  const [top, setTop] = useState<TopSpecies[]>([]);
  const [statusRows, setStatusRows] = useState<StatusRow[]>([]);
  const [trend, setTrend] = useState<TrendRow[]>([]);
  const [risk, setRisk] = useState<Risk[]>([]);
  const [summary, setSummary] = useState<Summary | null>(null);

  useEffect(() => {
    api.get<TopSpecies[]>("/species/top?limit=30").then(setTop).catch(() => {});
    api.get<StatusRow[]>("/species/status-breakdown").then(setStatusRows).catch(() => {});
    api.get<TrendRow[]>("/species/observation-trend").then(setTrend).catch(() => {});
    api.get<Risk[]>("/species/decline-risk").then(setRisk).catch(() => {});
    api.get<Summary>("/ingestion/summary").then(setSummary).catch(() => {});
  }, []);

  const endangered = statusRows.filter((r) => r.status === "CR" || r.status === "EN").reduce((s, r) => s + r.species, 0);
  const endemicCount = top.filter((t) => t.endemic).length;
  const maxObs = top.reduce((m, t) => Math.max(m, t.observations), 0) || 1;
  const leaderboard = top.slice(0, 8);
  const trendData = useMemo(() => trend.map((t) => ({ ...t, m: monthLabel(t.month) })), [trend]);

  return (
    <div>
      <div className="section-title">
        <div>
          <h1>Biodiversity Observatory</h1>
          <div className="subtitle">Endemic species tracking across Madagascar — occurrences, hotspots and decline risk.</div>
        </div>
      </div>

      <div className="grid kpi-row">
        <Kpi icon={<IconPaw size={18} />} accent="green" label="Species tracked" value={summary?.species ?? top.length} hint="endemic Malagasy taxa" />
        <Kpi icon={<IconAlertTriangle size={18} />} accent="danger" label="Endangered" value={endangered} hint="Critically endangered + Endangered" />
        <Kpi icon={<IconMapPin size={18} />} accent="water" label="Observations" value={(summary?.species_observations ?? 0).toLocaleString()} hint="georeferenced records" />
        <Kpi icon={<IconGlobe size={18} />} accent="violet" label="Endemic" value={endemicCount ? `${endemicCount}/${top.length}` : "—"} hint="found nowhere else on Earth" />
      </div>

      <div className="grid col-2-1" style={{ marginTop: 18 }}>
        <div className="panel">
          <PanelHead title="Most observed species" sub="Ranked by total georeferenced occurrences" />
          <div className="leaderboard">
            {leaderboard.map((s, i) => {
              const meta = speciesMeta(s.scientific_name);
              return (
                <div className="lb-row" key={s.species_id}>
                  <div className="lb-rank">{i + 1}</div>
                  <div className="lb-main">
                    <div className="lb-name">
                      <span className="lb-taxon"><TaxonIcon group={meta.group} size={14} /></span>
                      <span>{s.scientific_name}</span>
                      <StatusChip status={s.conservation_status} />
                    </div>
                    <div className="lb-bar-track">
                      <div className="lb-bar-fill" style={{ width: `${(s.observations / maxObs) * 100}%` }} />
                    </div>
                  </div>
                  <div className="lb-count">{s.observations}</div>
                </div>
              );
            })}
            {leaderboard.length === 0 && <div className="muted">No observations yet.</div>}
          </div>
        </div>

        <div className="panel">
          <PanelHead title="Red List profile" sub="Species per IUCN category" />
          <div className="stack" style={{ gap: 10 }}>
            {statusRows.map((r) => {
              const key = statusKey(r.status);
              const total = statusRows.reduce((s, x) => s + x.species, 0) || 1;
              return (
                <div key={r.status}>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12.5, marginBottom: 4 }}>
                    <span><StatusChip status={r.status} /> <span className="muted">{IUCN_LABEL[key]}</span></span>
                    <b>{r.species}</b>
                  </div>
                  <div className="lb-bar-track">
                    <div className="lb-bar-fill" style={{ width: `${(r.species / total) * 100}%`, background: `var(--green-600)` }} />
                  </div>
                </div>
              );
            })}
          </div>
          <p className="panel-note">Every species tracked here is endemic to Madagascar.</p>
        </div>
      </div>

      <div className="panel" style={{ marginTop: 18 }}>
        <PanelHead title="Species gallery" sub="Live photos from iNaturalist where available, with observation counts" />
        <div className="gallery">
          {top.map((s) => {
            const meta = speciesMeta(s.scientific_name);
            return (
              <div className="species-card" key={s.species_id}>
                <SpeciesPhoto name={s.scientific_name} status={s.conservation_status} endemic={s.endemic} />
                <div className="species-body">
                  <div className="sci">{s.scientific_name}</div>
                  <div className="common">{meta.common} · {meta.group}</div>
                  <div className="species-foot">
                    <span className="chip chip-soft">{s.regions} regions</span>
                    <span><span className="count">{s.observations}</span> <span className="count-l">obs</span></span>
                  </div>
                </div>
              </div>
            );
          })}
          {top.length === 0 && <div className="muted">No species yet.</div>}
        </div>
      </div>

      <div className="grid col-2-1" style={{ marginTop: 18 }}>
        <div className="panel">
          <PanelHead title="Observation volume over time" sub="Monthly records by data source" />
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={trendData} margin={{ top: 6, right: 12, bottom: 4, left: -12 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={CHART.grid} vertical={false} />
              <XAxis dataKey="m" fontSize={11} minTickGap={28} tickMargin={6} />
              <YAxis fontSize={11} />
              <Tooltip />
              <Bar dataKey="gbif" stackId="s" fill={CHART.gbif} name="GBIF" />
              <Bar dataKey="inaturalist" stackId="s" fill={CHART.inaturalist} name="iNaturalist" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
          <div className="inline-legend">
            <span><span className="k" style={{ background: CHART.gbif }} />GBIF</span>
            <span><span className="k" style={{ background: CHART.inaturalist }} />iNaturalist</span>
          </div>
        </div>

        <div className="panel">
          <PanelHead title="Species decline watch" sub="Endemics recorded inside active deforestation zones" />
          <div className="callout" style={{ marginBottom: 12 }}>
            <span className="ico"><IconAlertTriangle size={16} /></span>
            <span>Risk combines each species' IUCN status with the vegetation loss of the deforestation zones it was observed in.</span>
          </div>
          <div>
            {risk.slice(0, 7).map((r) => (
              <div className="risk-row" key={r.scientific_name}>
                <span className={`risk-dot ${r.risk_level}`} />
                <div className="risk-main">
                  <div className="risk-name">{r.scientific_name} <StatusChip status={r.conservation_status} /></div>
                  <div className="risk-meta">
                    {r.observations_at_risk} obs · loss {r.max_loss.toFixed(3)} · {r.regions.slice(0, 3).join(", ")}
                    {r.regions.length > 3 ? "…" : ""}
                  </div>
                </div>
                <span className="risk-score" style={{ color: r.risk_level === "high" ? "var(--danger)" : r.risk_level === "medium" ? "var(--warn)" : "var(--ok)" }}>
                  {r.risk_score.toFixed(2)}
                </span>
              </div>
            ))}
            {risk.length === 0 && <div className="muted">No species currently inside detected deforestation zones.</div>}
          </div>
        </div>
      </div>

      <div className="panel" style={{ marginTop: 18 }}>
        <PanelHead title="Observation map" sub="Every georeferenced record, coloured by conservation status" />
        <ObservationMap height={500} />
      </div>
    </div>
  );
}
