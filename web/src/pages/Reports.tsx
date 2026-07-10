import { useEffect, useState } from "react";
import { api, downloadUrl, getToken } from "../api";

interface Report { id: number; format: string; created_at: string; object_key: string | null; }

export default function Reports() {
  const [reports, setReports] = useState<Report[]>([]);
  const [busy, setBusy] = useState(false);

  function load() {
    api.get<Report[]>("/reports").then(setReports).catch(() => {});
  }
  useEffect(load, []);

  async function generate(format: "csv" | "pdf") {
    setBusy(true);
    try {
      await api.post<Report>("/reports", { format });
      load();
    } finally {
      setBusy(false);
    }
  }

  // Download needs the bearer token, so fetch as a blob and save.
  async function download(r: Report) {
    const res = await fetch(downloadUrl(r.id), { headers: { Authorization: `Bearer ${getToken()}` } });
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `samba_report_${r.id}.${r.format}`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div>
      <div className="section-title">
        <div>
          <h1>Environmental Reports</h1>
          <div className="subtitle">Exportable regional summaries: NDVI change, deforestation status, richness and alerts.</div>
        </div>
        <div className="row-actions">
          <button className="btn" disabled={busy} onClick={() => generate("csv")}>Export CSV</button>
          <button className="btn" disabled={busy} onClick={() => generate("pdf")}>Export PDF</button>
        </div>
      </div>

      <div className="panel">
        <p className="muted" style={{ marginTop: 0 }}>
          Reports summarise each region: NDVI change, deforestation status, species richness, and active alerts.
        </p>
        <table>
          <thead>
            <tr><th>ID</th><th>Format</th><th>Created</th><th></th></tr>
          </thead>
          <tbody>
            {reports.map((r) => (
              <tr key={r.id}>
                <td>#{r.id}</td>
                <td><span className="badge deforestation">{r.format.toUpperCase()}</span></td>
                <td>{new Date(r.created_at).toLocaleString()}</td>
                <td><button className="btn-sm" onClick={() => download(r)}>Download</button></td>
              </tr>
            ))}
            {reports.length === 0 && (
              <tr><td colSpan={4} className="muted">No reports yet — export one above.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
