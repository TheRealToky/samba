import { useEffect, useMemo, useState } from "react";
import {
  CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis, Legend,
} from "recharts";
import { api } from "../api";

interface Region { id: number; code: string; name: string; }
interface NdviPoint { date: string; ndvi: number; }
interface AlignRow { period: string; temperature: number | null; rainfall: number | null; }
interface Prediction { payload: { points?: { period: string; value: number }[] } }

const ym = (iso: string) => iso.slice(0, 7);

export default function Trends() {
  const [regions, setRegions] = useState<Region[]>([]);
  const [regionId, setRegionId] = useState<number | null>(null);
  const [ndvi, setNdvi] = useState<NdviPoint[]>([]);
  const [align, setAlign] = useState<AlignRow[]>([]);
  const [forecast, setForecast] = useState<{ period: string; value: number }[]>([]);

  useEffect(() => {
    api.get<Region[]>("/regions").then((r) => {
      setRegions(r);
      if (r.length) setRegionId(r[0].id);
    });
  }, []);

  useEffect(() => {
    if (regionId == null) return;
    api.get<{ points: NdviPoint[] }>(`/regions/${regionId}/ndvi-series`).then((d) => setNdvi(d.points));
    api.get<{ rows: AlignRow[] }>(`/regions/${regionId}/alignment`).then((d) => setAlign(d.rows));
    api
      .get<Prediction[]>(`/predictions?type=climate_forecast&region_id=${regionId}`)
      .then((d) => setForecast(d[0]?.payload?.points ?? []))
      .catch(() => setForecast([]));
  }, [regionId]);

  const ndviData = useMemo(() => ndvi.map((p) => ({ t: ym(p.date), ndvi: p.ndvi })), [ndvi]);

  const tempData = useMemo(() => {
    const hist = align
      .filter((r) => r.temperature != null)
      .map((r) => ({ t: ym(r.period), temperature: r.temperature as number }));
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
        <h1>Trends & Forecasts</h1>
        <select value={regionId ?? ""} onChange={(e) => setRegionId(Number(e.target.value))}>
          {regions.map((r) => (
            <option key={r.id} value={r.id}>{r.name}</option>
          ))}
        </select>
      </div>

      <div className="panel" style={{ marginBottom: 18 }}>
        <h2>NDVI (vegetation greenness) over time</h2>
        <ResponsiveContainer width="100%" height={260}>
          <LineChart data={ndviData} margin={{ top: 5, right: 20, bottom: 5, left: -10 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="t" fontSize={11} minTickGap={40} />
            <YAxis domain={[0, 1]} fontSize={11} />
            <Tooltip />
            <Line type="monotone" dataKey="ndvi" stroke="#2e7d32" dot={false} strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="grid two-col">
        <div className="panel">
          <h2>Temperature: history + 12-month SARIMA forecast</h2>
          <ResponsiveContainer width="100%" height={240}>
            <LineChart data={tempData} margin={{ top: 5, right: 20, bottom: 5, left: -10 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="t" fontSize={11} minTickGap={30} />
              <YAxis fontSize={11} unit="°" />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="temperature" stroke="#ef6c00" dot={false} strokeWidth={2} />
              <Line type="monotone" dataKey="forecast" stroke="#1565c0" dot={false} strokeWidth={2} strokeDasharray="5 4" />
            </LineChart>
          </ResponsiveContainer>
        </div>
        <div className="panel">
          <h2>Rainfall (monthly mean)</h2>
          <ResponsiveContainer width="100%" height={240}>
            <LineChart data={rainData} margin={{ top: 5, right: 20, bottom: 5, left: -10 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="t" fontSize={11} minTickGap={30} />
              <YAxis fontSize={11} />
              <Tooltip />
              <Line type="monotone" dataKey="rainfall" stroke="#1565c0" dot={false} strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
