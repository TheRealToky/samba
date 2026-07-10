import { useEffect, useMemo, useState } from "react";
import {
  Area, AreaChart, Bar, BarChart, Cell, Pie, PieChart, ResponsiveContainer,
  Tooltip, XAxis, YAxis, CartesianGrid,
} from "recharts";
import { api } from "../api";
import { Kpi, PanelHead } from "../components/ui";
import {
  IconAxe, IconBell, IconCamera, IconDatabase, IconPaw, IconSatellite, IconThermometer,
} from "../components/icons";
import { CHART, IUCN_COLOR, IUCN_LABEL, statusKey } from "../lib/species";

interface Summary { regions: number; satellite_data: number; climate_data: number; species: number; species_observations: number; }
interface Richness { region_name: string; species_richness: number; observations: number; }
interface DefEvent { id: number; vegetation_loss: number; region_id: number; }
interface Alert { id: number; alert_type: string; severity: string; message: string; }
interface StatusRow { status: string; species: number; observations: number; }
interface TrendRow { month: string; gbif: number; inaturalist: number; upload: number; total: number; }
interface RegionalRow { region_name: string; ndvi_change: number | null; biome: string; }

const monthLabel = (m: string) => m.slice(0, 7);

export default function Dashboard() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [richness, setRichness] = useState<Richness[]>([]);
  const [events, setEvents] = useState<DefEvent[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [statusRows, setStatusRows] = useState<StatusRow[]>([]);
  const [trend, setTrend] = useState<TrendRow[]>([]);
  const [regional, setRegional] = useState<RegionalRow[]>([]);

  useEffect(() => {
    api.get<Summary>("/ingestion/summary").then(setSummary).catch(() => {});
    api.get<Richness[]>("/species/richness").then(setRichness).catch(() => {});
    api.get<DefEvent[]>("/deforestation-events").then(setEvents).catch(() => {});
    api.get<Alert[]>("/alerts").then(setAlerts).catch(() => {});
    api.get<StatusRow[]>("/species/status-breakdown").then(setStatusRows).catch(() => {});
    api.get<TrendRow[]>("/species/observation-trend").then(setTrend).catch(() => {});
    api.get<RegionalRow[]>("/climate/regional").then(setRegional).catch(() => {});
  }, []);

  const avgLoss = events.length ? events.reduce((s, e) => s + e.vegetation_loss, 0) / events.length : 0;
  const highAlerts = alerts.filter((a) => a.severity === "high" || a.severity === "critical").length;
  const endangered = statusRows.filter((r) => r.status === "CR" || r.status === "EN").reduce((s, r) => s + r.species, 0);

  const trendData = useMemo(() => trend.map((t) => ({ ...t, m: monthLabel(t.month) })), [trend]);
  const pieData = useMemo(
    () => statusRows.map((r) => ({ name: statusKey(r.status), value: r.species })),
    [statusRows]
  );
  const lossRanking = useMemo(
    () =>
      regional
        .map((r) => ({ region: r.region_name, loss: r.ndvi_change != null ? -r.ndvi_change : 0 }))
        .sort((a, b) => b.loss - a.loss)
        .slice(0, 8),
    [regional]
  );

  return (
    <div>
      <section className="hero">
        <div className="hero-eyebrow">National environmental status · Madagascar</div>
        <h1>The state of Madagascar's forests, climate &amp; wildlife</h1>
        <p>
          SAMBA unifies satellite vegetation monitoring, climate reanalysis and biodiversity records into one
          decision-ready view — tracking deforestation, warming trends and the endemic species most at risk.
        </p>
        <div className="hero-stats">
          <div className="hero-stat"><div className="n">{summary?.regions ?? "—"}</div><div className="l">Regions monitored</div></div>
          <div className="hero-stat"><div className="n">{summary?.species ?? "—"}</div><div className="l">Species tracked</div></div>
          <div className="hero-stat"><div className="n">{(summary?.species_observations ?? 0).toLocaleString()}</div><div className="l">Observations</div></div>
          <div className="hero-stat"><div className="n">{(summary?.satellite_data ?? 0).toLocaleString()}</div><div className="l">Satellite readings</div></div>
        </div>
      </section>

      <div className="grid kpi-row">
        <Kpi icon={<IconAxe size={18} />} accent="danger" label="Deforestation zones" value={events.length}
          hint={`avg NDVI loss ${avgLoss.toFixed(3)}`} />
        <Kpi icon={<IconPaw size={18} />} accent="amber" label="Endangered species" value={endangered}
          hint={`CR + EN of ${summary?.species ?? "—"} tracked`} />
        <Kpi icon={<IconBell size={18} />} accent="violet" label="Active alerts" value={alerts.length}
          hint={`${highAlerts} high severity`} />
        <Kpi icon={<IconSatellite size={18} />} accent="green" label="Observations logged" value={(summary?.species_observations ?? 0).toLocaleString()}
          hint="GBIF + iNaturalist records" />
      </div>

      <div className="grid col-2-1" style={{ marginTop: 18 }}>
        <div className="panel">
          <PanelHead title="Biodiversity observation activity" sub="Monthly records by source (GBIF vs iNaturalist)" />
          <ResponsiveContainer width="100%" height={280}>
            <AreaChart data={trendData} margin={{ top: 6, right: 12, bottom: 4, left: -12 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={CHART.grid} vertical={false} />
              <XAxis dataKey="m" fontSize={11} minTickGap={28} tickMargin={6} />
              <YAxis fontSize={11} />
              <Tooltip />
              <Area type="monotone" dataKey="gbif" stackId="1" stroke={CHART.gbif} fill={CHART.gbif} fillOpacity={0.14} strokeWidth={2} name="GBIF" />
              <Area type="monotone" dataKey="inaturalist" stackId="1" stroke={CHART.inaturalist} fill={CHART.inaturalist} fillOpacity={0.14} strokeWidth={2} name="iNaturalist" />
            </AreaChart>
          </ResponsiveContainer>
          <div className="inline-legend">
            <span><span className="k" style={{ background: CHART.gbif }} />GBIF (bulk occurrences)</span>
            <span><span className="k" style={{ background: CHART.inaturalist }} />iNaturalist (community)</span>
          </div>
        </div>

        <div className="panel">
          <PanelHead title="Conservation status" sub="Species by IUCN Red List category" />
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie data={pieData} dataKey="value" nameKey="name" innerRadius={54} outerRadius={82} paddingAngle={2}>
                {pieData.map((d) => (
                  <Cell key={d.name} fill={IUCN_COLOR[d.name]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
          <div className="inline-legend" style={{ justifyContent: "center" }}>
            {pieData.map((d) => (
              <span key={d.name} title={IUCN_LABEL[d.name]}>
                <span className="k" style={{ background: IUCN_COLOR[d.name] }} />{d.name} · {d.value}
              </span>
            ))}
          </div>
        </div>
      </div>

      <div className="grid two-col" style={{ marginTop: 18 }}>
        <div className="panel">
          <PanelHead title="Regions by forest loss" sub="NDVI decline since monitoring began (higher = more loss)" />
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={lossRanking} layout="vertical" margin={{ top: 4, right: 16, bottom: 4, left: 8 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={CHART.grid} horizontal={false} />
              <XAxis type="number" fontSize={11} tickFormatter={(v) => v.toFixed(2)} />
              <YAxis type="category" dataKey="region" width={104} fontSize={11} />
              <Tooltip formatter={(v: number) => v.toFixed(3)} />
              <Bar dataKey="loss" radius={[0, 5, 5, 0]}>
                {lossRanking.map((d, i) => (
                  <Cell key={i} fill={d.loss >= 0.15 ? "#c62828" : d.loss >= 0.05 ? "#ef6c00" : "#2e7d32"} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="panel">
          <PanelHead title="Recent alerts" sub={`${highAlerts} high-severity of ${alerts.length} active`} />
          <table>
            <tbody>
              {alerts.slice(0, 7).map((a) => (
                <tr key={a.id}>
                  <td style={{ width: 78 }}><span className={`badge ${a.severity}`}>{a.severity}</span></td>
                  <td>{a.message}</td>
                </tr>
              ))}
              {alerts.length === 0 && (
                <tr><td className="muted">No alerts yet — run a training pass to generate them.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      <div className="panel" style={{ marginTop: 18 }}>
        <PanelHead title="Species richness by region" sub="Distinct endemic species recorded in each region" />
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={richness} margin={{ top: 6, right: 10, bottom: 44, left: -8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={CHART.grid} vertical={false} />
            <XAxis dataKey="region_name" angle={-32} textAnchor="end" interval={0} height={64} fontSize={11} />
            <YAxis fontSize={11} allowDecimals={false} />
            <Tooltip />
            <Bar dataKey="species_richness" radius={[5, 5, 0, 0]} fill={CHART.green} name="Species richness" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="panel" style={{ marginTop: 18 }}>
        <PanelHead title="Integrated data sources" sub="SAMBA reconciles four authoritative environmental feeds" />
        <div className="source-strip">
          <span className="source-pill"><IconSatellite size={14} /> <b>Google Earth Engine</b> — Sentinel-2 / Landsat NDVI</span>
          <span className="source-pill"><IconThermometer size={14} /> <b>NASA POWER</b> — temperature, rainfall, humidity</span>
          <span className="source-pill"><IconDatabase size={14} /> <b>GBIF</b> — bulk species occurrences</span>
          <span className="source-pill"><IconCamera size={14} /> <b>iNaturalist</b> — community observations &amp; photos</span>
        </div>
      </div>
    </div>
  );
}
