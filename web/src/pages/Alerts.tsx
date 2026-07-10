import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import { useAuth } from "../auth";
import { Kpi } from "../components/ui";
import { IconAlertTriangle, IconAxe, IconBell, IconCheck, IconPaw } from "../components/icons";

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

  const stats = useMemo(() => {
    const high = alerts.filter((a) => a.severity === "high" || a.severity === "critical").length;
    const defor = alerts.filter((a) => a.alert_type === "deforestation").length;
    const bio = alerts.filter((a) => a.alert_type === "biodiversity").length;
    const open = alerts.filter((a) => !a.acknowledged).length;
    return { high, defor, bio, open };
  }, [alerts]);

  async function acknowledge(id: number) {
    await api.patch(`/alerts/${id}/acknowledge`);
    load();
  }

  return (
    <div>
      <div className="section-title">
        <div>
          <h1>Environmental Alerts</h1>
          <div className="subtitle">Automated warnings generated from deforestation detection and biodiversity risk models.</div>
        </div>
        <select value={filter} onChange={(e) => setFilter(e.target.value)}>
          <option value="all">All types</option>
          <option value="deforestation">Deforestation</option>
          <option value="biodiversity">Biodiversity</option>
        </select>
      </div>

      <div className="grid kpi-row" style={{ marginBottom: 18 }}>
        <Kpi icon={<IconBell size={18} />} accent="violet" label="Active alerts" value={alerts.length} hint={`${stats.open} open`} />
        <Kpi icon={<IconAlertTriangle size={18} />} accent="danger" label="High severity" value={stats.high} hint="need attention" />
        <Kpi icon={<IconAxe size={18} />} accent="amber" label="Deforestation" value={stats.defor} hint="vegetation-loss zones" />
        <Kpi icon={<IconPaw size={18} />} accent="green" label="Biodiversity" value={stats.bio} hint="species at risk" />
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
                <td>
                  {a.acknowledged ? (
                    <span className="ack-yes"><IconCheck size={13} /> acknowledged</span>
                  ) : (
                    <span className="muted">open</span>
                  )}
                </td>
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
