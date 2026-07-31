import { ReactNode, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { IconArrowRight, IconCheck, IconLeaf } from "./icons";
import "../auth.css";

interface Summary {
  regions: number;
  species: number;
  species_observations: number;
}

/**
 * Split layout shared by sign in and sign up: a brand panel carrying the same
 * live counts as the landing page, and the form itself on the right.
 */
export default function AuthShell({
  title,
  subtitle,
  children,
  footer,
  highlights,
}: {
  title: string;
  subtitle: string;
  children: ReactNode;
  footer: ReactNode;
  highlights: string[];
}) {
  const [summary, setSummary] = useState<Summary | null>(null);

  useEffect(() => {
    api.get<Summary>("/ingestion/summary").then(setSummary).catch(() => {});
  }, []);

  const stats = [
    { n: summary?.regions, l: "Regions monitored" },
    { n: summary?.species, l: "Species tracked" },
    { n: summary?.species_observations, l: "Observations" },
  ];

  return (
    <div className="auth">
      <aside className="auth-aside">
        <Link to="/" className="auth-brand">
          <span className="auth-brand-mark"><IconLeaf size={18} /></span>
          <span className="auth-brand-text">
            SAMBA
            <span>Madagascar Environmental Hub</span>
          </span>
        </Link>

        <div className="auth-aside-body">
          <h2>Madagascar's environmental intelligence, in one place.</h2>
          <ul className="auth-highlights">
            {highlights.map((h) => (
              <li key={h}>
                <span className="auth-tick"><IconCheck size={12} /></span>
                {h}
              </li>
            ))}
          </ul>
          <div className="auth-stats">
            {stats.map((s) => (
              <div key={s.l}>
                <b>{s.n != null ? s.n.toLocaleString() : "—"}</b>
                <span>{s.l}</span>
              </div>
            ))}
          </div>
        </div>

        <p className="auth-aside-foot">
          Sentinel-2 / Landsat via Google Earth Engine · NASA POWER · GBIF · iNaturalist
        </p>
      </aside>

      <main className="auth-main">
        <Link className="auth-back" to="/">
          Back to the home page <IconArrowRight size={13} />
        </Link>

        <div className="auth-card">
          <div className="auth-card-head">
            <h1>{title}</h1>
            <p>{subtitle}</p>
          </div>
          {children}
        </div>

        <div className="auth-alt">{footer}</div>
      </main>
    </div>
  );
}
