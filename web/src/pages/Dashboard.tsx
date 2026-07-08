import { useEffect, useState } from "react";
import {
  Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { api } from "../api";

interface Summary {
  regions: number;
  satellite_data: number;
  climate_data: number;
  species: number;
  species_observations: number;
}
interface Richness { region_name: string; species_richness: number; observations: number; }
interface DefEvent { id: number; vegetation_loss: number; region_id: number; }
interface Alert { id: number; alert_type: string; severity: string; message: string; }

export default function Dashboard() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [richness, setRichness] = useState<Richness[]>([]);
  const [events, setEvents] = useState<DefEvent[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);

  useEffect(() => {
    api.get<Summary>("/ingestion/summary").then(setSummary).catch(() => {});
    api.get<Richness[]>("/species/richness").then(setRichness).catch(() => {});
    api.get<DefEvent[]>("/deforestation-events").then(setEvents).catch(() => {});
    api.get<Alert[]>("/alerts").then(setAlerts).catch(() => {});
  }, []);

  const avgLoss = events.length ? events.reduce((s, e) => s + e.vegetation_loss, 0) / events.length : 0;
  const highAlerts = alerts.filter((a) => a.severity === "high" || a.severity === "critical").length;

  return (
    <div>
      <div className="section-title">
        <h1>National Overview</h1>
      </div>

      <div className="grid kpi-row">
        <div className="kpi">
          <div className="label">Deforestation zones</div>
          <div className="value">{events.length}<span style={{ fontSize: 16, color: "var(--muted)" }}> / {summary?.regions ?? "—"}</span></div>
          <div className="hint">avg NDVI loss {avgLoss.toFixed(3)}</div>
        </div>
        <div className="kpi">
          <div className="label">Species tracked</div>
          <div className="value">{summary?.species ?? "—"}</div>
          <div className="hint">{summary?.species_observations ?? 0} observations</div>
        </div>
        <div className="kpi">
          <div className="label">Active alerts</div>
          <div className="value">{alerts.length}</div>
          <div className="hint">{highAlerts} high severity</div>
        </div>
        <div className="kpi">
          <div className="label">Data points</div>
          <div className="value">{(summary?.satellite_data ?? 0).toLocaleString()}</div>
          <div className="hint">satellite NDVI records</div>
        </div>
      </div>

      <div className="grid two-col" style={{ marginTop: 18 }}>
        <div className="panel">
          <h2>Species richness by region</h2>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={richness} margin={{ top: 5, right: 10, bottom: 40, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="region_name" angle={-35} textAnchor="end" interval={0} height={60} fontSize={11} />
              <YAxis fontSize={11} />
              <Tooltip />
              <Bar dataKey="species_richness" radius={[4, 4, 0, 0]}>
                {richness.map((_, i) => (
                  <Cell key={i} fill="#2e7d32" />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="panel">
          <h2>Recent alerts</h2>
          <table>
            <tbody>
              {alerts.slice(0, 8).map((a) => (
                <tr key={a.id}>
                  <td style={{ width: 90 }}>
                    <span className={`badge ${a.severity}`}>{a.severity}</span>
                  </td>
                  <td>{a.message}</td>
                </tr>
              ))}
              {alerts.length === 0 && (
                <tr>
                  <td className="muted">No alerts yet — run a training pass to generate them.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
