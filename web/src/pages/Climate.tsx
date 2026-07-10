import { useEffect, useMemo, useState } from "react";
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, ComposedChart, Legend, Line,
  LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { api } from "../api";
import { Kpi, PanelHead } from "../components/ui";
import { IconCloudRain, IconDroplet, IconLeaf, IconThermometer } from "../components/icons";
import { CHART } from "../lib/species";

interface OverviewRow { month: string; temperature: number | null; rainfall: number | null; humidity: number | null; ndvi: number | null; }
interface RegionalRow {
  region_id: number; region_name: string; biome: string;
  avg_temperature: number | null; avg_rainfall: number | null; avg_humidity: number | null;
  ndvi_start: number | null; ndvi_end: number | null; ndvi_change: number | null;
}
interface Region { id: number; code: string; name: string; }
interface NdviPoint { date: string; ndvi: number; }
interface AlignRow { period: string; temperature: number | null; rainfall: number | null; }
interface Prediction { payload: { points?: { period: string; value: number }[] } }

const ym = (iso: string) => iso.slice(0, 7);

export default function Climate() {
  const [overview, setOverview] = useState<OverviewRow[]>([]);
  const [regional, setRegional] = useState<RegionalRow[]>([]);
  const [regions, setRegions] = useState<Region[]>([]);
  const [regionId, setRegionId] = useState<number | null>(null);
  const [ndvi, setNdvi] = useState<NdviPoint[]>([]);
  const [align, setAlign] = useState<AlignRow[]>([]);
  const [forecast, setForecast] = useState<{ period: string; value: number }[]>([]);

  useEffect(() => {
    api.get<OverviewRow[]>("/climate/overview").then(setOverview).catch(() => {});
    api.get<RegionalRow[]>("/climate/regional").then(setRegional).catch(() => {});
    api.get<Region[]>("/regions").then((r) => {
      setRegions(r);
      if (r.length) setRegionId(r[0].id);
    });
  }, []);

  useEffect(() => {
    if (regionId == null) return;
    api.get<{ points: NdviPoint[] }>(`/regions/${regionId}/ndvi-series`).then((d) => setNdvi(d.points)).catch(() => {});
    api.get<{ rows: AlignRow[] }>(`/regions/${regionId}/alignment`).then((d) => setAlign(d.rows)).catch(() => {});
    api
      .get<Prediction[]>(`/predictions?type=climate_forecast&region_id=${regionId}`)
      .then((d) => setForecast(d[0]?.payload?.points ?? []))
      .catch(() => setForecast([]));
  }, [regionId]);

  const overviewData = useMemo(() => overview.map((r) => ({ ...r, m: ym(r.month) })), [overview]);

  // National indicators
  const nums = (k: keyof OverviewRow) => overview.map((r) => r[k]).filter((v): v is number => v != null);
  const avg = (a: number[]) => (a.length ? a.reduce((s, v) => s + v, 0) / a.length : 0);
  const avgTemp = avg(nums("temperature"));
  const avgRain = avg(nums("rainfall"));
  const avgHum = avg(nums("humidity"));
  const ndviSeries = nums("ndvi");
  const ndviChange = ndviSeries.length >= 2 ? ndviSeries[ndviSeries.length - 1] - ndviSeries[0] : 0;
  const tempSeries = nums("temperature");
  const tempChange = tempSeries.length >= 2 ? tempSeries[tempSeries.length - 1] - tempSeries[0] : 0;

  const ndviRanking = useMemo(
    () =>
      regional
        .map((r) => ({ region: r.region_name, change: r.ndvi_change ?? 0 }))
        .sort((a, b) => a.change - b.change),
    [regional]
  );

  const ndviData = useMemo(() => ndvi.map((p) => ({ t: ym(p.date), ndvi: p.ndvi })), [ndvi]);
  const tempData = useMemo(() => {
    const hist = align.filter((r) => r.temperature != null).map((r) => ({ t: ym(r.period), temperature: r.temperature as number }));
    const fc = forecast.map((p) => ({ t: ym(p.period), forecast: p.value }));
    return [...hist, ...fc];
  }, [align, forecast]);
  const rainData = useMemo(
    () => align.filter((r) => r.rainfall != null).map((r) => ({ t: ym(r.period), rainfall: r.rainfall as number })),
    [align]
  );

  return (
    <div>
      <div className="section-title">
        <div>
          <h1>Climate Change Monitor</h1>
          <div className="subtitle">National temperature, rainfall and vegetation trends from NASA POWER &amp; satellite NDVI.</div>
        </div>
      </div>

      <div className="grid kpi-row">
        <Kpi icon={<IconThermometer size={18} />} accent="amber" label="Avg temperature" value={avgTemp.toFixed(1)} unit="°C"
          trend={{ dir: tempChange > 0.1 ? "up" : tempChange < -0.1 ? "down" : "flat", text: `${tempChange >= 0 ? "+" : ""}${tempChange.toFixed(2)}°C over record` }} />
        <Kpi icon={<IconCloudRain size={18} />} accent="water" label="Avg monthly rainfall" value={avgRain.toFixed(0)} unit="mm" hint="country-wide mean" />
        <Kpi icon={<IconDroplet size={18} />} accent="green" label="Avg humidity" value={avgHum.toFixed(0)} unit="%" hint="relative humidity" />
        <Kpi icon={<IconLeaf size={18} />} accent={ndviChange < 0 ? "danger" : "green"} label="Vegetation (NDVI)" value={ndviChange >= 0 ? `+${ndviChange.toFixed(3)}` : ndviChange.toFixed(3)}
          trend={{ dir: ndviChange < -0.01 ? "down" : ndviChange > 0.01 ? "up" : "flat", text: ndviChange < 0 ? "greenness declining" : "greenness stable" }} />
      </div>

      <div className="panel" style={{ marginTop: 18 }}>
        <PanelHead title="National climate trend" sub="Monthly rainfall (bars) and mean temperature (line) across all regions" />
        <ResponsiveContainer width="100%" height={300}>
          <ComposedChart data={overviewData} margin={{ top: 6, right: 8, bottom: 4, left: -8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={CHART.grid} vertical={false} />
            <XAxis dataKey="m" fontSize={11} minTickGap={28} tickMargin={6} />
            <YAxis yAxisId="rain" fontSize={11} unit="mm" />
            <YAxis yAxisId="temp" orientation="right" fontSize={11} unit="°" domain={["dataMin - 2", "dataMax + 2"]} />
            <Tooltip />
            <Legend />
            <Bar yAxisId="rain" dataKey="rainfall" fill={CHART.water} name="Rainfall (mm)" radius={[3, 3, 0, 0]} opacity={0.75} />
            <Line yAxisId="temp" type="monotone" dataKey="temperature" stroke={CHART.amber} strokeWidth={2.5} dot={false} name="Temperature (°C)" />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      <div className="grid two-col" style={{ marginTop: 18 }}>
        <div className="panel">
          <PanelHead title="National vegetation greenness" sub="Country-wide average NDVI — falling values signal forest loss" />
          <ResponsiveContainer width="100%" height={260}>
            <AreaChart data={overviewData} margin={{ top: 6, right: 12, bottom: 4, left: -12 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={CHART.grid} vertical={false} />
              <XAxis dataKey="m" fontSize={11} minTickGap={28} tickMargin={6} />
              <YAxis fontSize={11} domain={[0, 1]} />
              <Tooltip />
              <Area type="monotone" dataKey="ndvi" stroke={CHART.green} fill={CHART.green} fillOpacity={0.14} strokeWidth={2} name="NDVI" />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        <div className="panel">
          <PanelHead title="Regions by NDVI change" sub="Net vegetation change since monitoring began" />
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={ndviRanking} layout="vertical" margin={{ top: 4, right: 18, bottom: 4, left: 8 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={CHART.grid} horizontal={false} />
              <XAxis type="number" fontSize={11} tickFormatter={(v) => v.toFixed(2)} />
              <YAxis type="category" dataKey="region" width={104} fontSize={11} />
              <Tooltip formatter={(v: number) => v.toFixed(3)} />
              <Bar dataKey="change" radius={[0, 4, 4, 0]}>
                {ndviRanking.map((d, i) => (
                  <Cell key={i} fill={d.change <= -0.15 ? "#c62828" : d.change < -0.02 ? "#ef6c00" : "#2e7d32"} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
          <p className="panel-note">Negative = vegetation loss (deforestation signal); near-zero = stable canopy.</p>
        </div>
      </div>

      <div className="section-title" style={{ marginTop: 26 }}>
        <div>
          <h1 style={{ fontSize: 18 }}>Regional deep-dive</h1>
          <div className="subtitle">Per-region vegetation, temperature forecast and rainfall.</div>
        </div>
        <select value={regionId ?? ""} onChange={(e) => setRegionId(Number(e.target.value))}>
          {regions.map((r) => (
            <option key={r.id} value={r.id}>{r.name}</option>
          ))}
        </select>
      </div>

      <div className="panel" style={{ marginBottom: 18 }}>
        <PanelHead title="NDVI (vegetation greenness) over time" />
        <ResponsiveContainer width="100%" height={240}>
          <LineChart data={ndviData} margin={{ top: 6, right: 20, bottom: 4, left: -10 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={CHART.grid} />
            <XAxis dataKey="t" fontSize={11} minTickGap={40} />
            <YAxis domain={[0, 1]} fontSize={11} />
            <Tooltip />
            <Line type="monotone" dataKey="ndvi" stroke={CHART.green} dot={false} strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="grid two-col">
        <div className="panel">
          <PanelHead title="Temperature" sub="History + 12-month SARIMA forecast" />
          <ResponsiveContainer width="100%" height={240}>
            <LineChart data={tempData} margin={{ top: 6, right: 20, bottom: 4, left: -10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={CHART.grid} />
              <XAxis dataKey="t" fontSize={11} minTickGap={30} />
              <YAxis fontSize={11} unit="°" />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="temperature" stroke={CHART.amber} dot={false} strokeWidth={2} name="History" />
              <Line type="monotone" dataKey="forecast" stroke={CHART.water} dot={false} strokeWidth={2} strokeDasharray="5 4" name="Forecast" />
            </LineChart>
          </ResponsiveContainer>
        </div>
        <div className="panel">
          <PanelHead title="Rainfall" sub="Monthly mean (mm)" />
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={rainData} margin={{ top: 6, right: 20, bottom: 4, left: -10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={CHART.grid} vertical={false} />
              <XAxis dataKey="t" fontSize={11} minTickGap={30} />
              <YAxis fontSize={11} />
              <Tooltip />
              <Bar dataKey="rainfall" fill={CHART.water} radius={[3, 3, 0, 0]} name="Rainfall (mm)" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="panel" style={{ marginTop: 18 }}>
        <PanelHead title="Regional climate comparison" sub="Averages across the monitoring record" />
        <table>
          <thead>
            <tr>
              <th>Region</th><th>Biome</th><th className="num">Avg temp (°C)</th>
              <th className="num">Rainfall (mm)</th><th className="num">Humidity (%)</th><th className="num">NDVI change</th>
            </tr>
          </thead>
          <tbody>
            {regional.map((r) => (
              <tr key={r.region_id}>
                <td>{r.region_name}</td>
                <td><span className="chip chip-biome">{r.biome.replace("_", " ")}</span></td>
                <td className="num">{r.avg_temperature?.toFixed(1) ?? "—"}</td>
                <td className="num">{r.avg_rainfall?.toFixed(0) ?? "—"}</td>
                <td className="num">{r.avg_humidity?.toFixed(0) ?? "—"}</td>
                <td className="num" style={{ color: (r.ndvi_change ?? 0) < -0.02 ? "var(--danger)" : "var(--muted)", fontWeight: 700 }}>
                  {r.ndvi_change != null ? (r.ndvi_change >= 0 ? "+" : "") + r.ndvi_change.toFixed(3) : "—"}
                </td>
              </tr>
            ))}
            {regional.length === 0 && <tr><td colSpan={6} className="muted">No climate data.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
