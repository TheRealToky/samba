import { useEffect, useState } from "react";
import { api } from "../api";
import { useAuth } from "../auth";

interface Alert {
  id: number;
  alert_type: string;
  severity: string;
  message: string;
  acknowledged: boolean;
  created_at: string;
}

const CAN_ACK = ["environmental_researcher", "ngo_policymaker", "administrator"];

export default function Alerts() {
  const { user } = useAuth();
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [filter, setFilter] = useState<string>("all");

  function load() {
    api.get<Alert[]>("/alerts").then(setAlerts).catch(() => {});
  }
  useEffect(load, []);

  const canAck = !!user && CAN_ACK.includes(user.role);
  const shown = filter === "all" ? alerts : alerts.filter((a) => a.alert_type === filter);

  async function acknowledge(id: number) {
    await api.patch(`/alerts/${id}/acknowledge`);
    load();
  }

  return (
    <div>
      <div className="section-title">
        <h1>Environmental Alerts</h1>
        <select value={filter} onChange={(e) => setFilter(e.target.value)}>
          <option value="all">All types</option>
          <option value="deforestation">Deforestation</option>
          <option value="biodiversity">Biodiversity</option>
        </select>
      </div>

      <div className="panel">
        <table>
          <thead>
            <tr>
              <th>Type</th>
              <th>Severity</th>
              <th>Message</th>
              <th>Status</th>
              {canAck && <th></th>}
            </tr>
          </thead>
          <tbody>
            {shown.map((a) => (
              <tr key={a.id}>
                <td><span className={`badge ${a.alert_type}`}>{a.alert_type}</span></td>
                <td><span className={`badge ${a.severity}`}>{a.severity}</span></td>
                <td>{a.message}</td>
                <td>{a.acknowledged ? "✓ acknowledged" : <span className="muted">open</span>}</td>
                {canAck && (
                  <td>
                    {!a.acknowledged && (
                      <button className="btn-sm" onClick={() => acknowledge(a.id)}>Acknowledge</button>
                    )}
                  </td>
                )}
              </tr>
            ))}
            {shown.length === 0 && (
              <tr><td colSpan={5} className="muted">No alerts.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
