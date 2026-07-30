import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api";
import { useAuth } from "../auth";
import MadagascarMap, { RegionSignal } from "../components/MadagascarMap";
import { SpeciesPhoto } from "../components/ui";
import {
  IconArrowRight, IconAxe, IconBell, IconCamera, IconChevronDown, IconCpu, IconDatabase,
  IconFileText, IconLayers, IconLeaf, IconPaw, IconSatellite, IconShield, IconThermometer,
  IconUsers,
} from "../components/icons";
import { CHART, IUCN_COLOR, IUCN_LABEL, speciesMeta, statusKey } from "../lib/species";
import "../landing.css";

interface Summary {
  regions: number;
  satellite_data: number;
  climate_data: number;
  species: number;
  species_with_status: number;
  species_observations: number;
}
interface StatusRow { status: string; species: number; observations: number }
interface TrendRow { month: string; gbif: number; inaturalist: number; total: number }
interface TopSpecies {
  species_id: number;
  scientific_name: string;
  conservation_status: string | null;
  endemic: boolean;
  observations: number;
  regions: number;
}

const reducedMotion = () =>
  typeof matchMedia === "function" && matchMedia("(prefers-reduced-motion: reduce)").matches;

/** Eased count-up driven by a timer (not rAF) so it also runs in background tabs. */
function useCountUp(target: number, ms = 1500) {
  const [n, setN] = useState(0);
  useEffect(() => {
    if (!target || reducedMotion()) {
      setN(target);
      return;
    }
    const started = Date.now();
    const id = setInterval(() => {
      const p = Math.min(1, (Date.now() - started) / ms);
      setN(Math.round(target * (1 - Math.pow(1 - p, 3))));
      if (p >= 1) clearInterval(id);
    }, 32);
    return () => clearInterval(id);
  }, [target, ms]);
  return n;
}

/** Fades sections in as they scroll into view, with a safety net so content is
 *  never left hidden if the observer doesn't fire. */
function useScrollReveal(deps: unknown[] = []) {
  useEffect(() => {
    const els = Array.from(document.querySelectorAll<HTMLElement>(".lp-reveal:not(.in)"));
    if (reducedMotion() || typeof IntersectionObserver === "undefined") {
      els.forEach((el) => el.classList.add("in"));
      return;
    }
    const io = new IntersectionObserver(
      (entries) =>
        entries.forEach((e) => {
          if (e.isIntersecting) {
            e.target.classList.add("in");
            io.unobserve(e.target);
          }
        }),
      { threshold: 0.06, rootMargin: "0px 0px -6% 0px" }
    );
    els.forEach((el) => io.observe(el));
    const failsafe = setTimeout(() => els.forEach((el) => el.classList.add("in")), 2500);
    return () => {
      io.disconnect();
      clearTimeout(failsafe);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
}

const fmt = (n: number) => n.toLocaleString();
const monthLabel = (m: string) => m.slice(0, 7);

export default function Landing() {
  const { user } = useAuth();
  const [summary, setSummary] = useState<Summary | null>(null);
  const [signals, setSignals] = useState<RegionSignal[]>([]);
  const [statusRows, setStatusRows] = useState<StatusRow[]>([]);
  const [trend, setTrend] = useState<TrendRow[]>([]);
  const [top, setTop] = useState<TopSpecies[]>([]);
  const [scrolled, setScrolled] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    api.get<Summary>("/ingestion/summary").then(setSummary).catch(() => {});
    api.get<RegionSignal[]>("/climate/regional").then(setSignals).catch(() => {});
    api.get<StatusRow[]>("/species/status-breakdown").then(setStatusRows).catch(() => {});
    api.get<TrendRow[]>("/species/observation-trend").then(setTrend).catch(() => {});
    api.get<TopSpecies[]>("/species/top?limit=40").then(setTop).catch(() => {});
  }, []);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useScrollReveal([summary, top.length]);

  const regions = useCountUp(summary?.regions ?? 0);
  const species = useCountUp(summary?.species ?? 0);
  const observations = useCountUp(summary?.species_observations ?? 0);
  const readings = useCountUp((summary?.satellite_data ?? 0) + (summary?.climate_data ?? 0));

  const threatened = statusRows
    .filter((r) => ["CR", "EN", "VU"].includes(r.status))
    .reduce((s, r) => s + r.species, 0);

  const statusBars = useMemo(() => {
    const wanted = ["CR", "EN", "VU", "NT", "LC"];
    const rows = wanted
      .map((k) => statusRows.find((r) => r.status === k))
      .filter((r): r is StatusRow => !!r);
    const max = Math.max(1, ...rows.map((r) => r.species));
    return rows.map((r) => ({ ...r, pct: (r.species / max) * 100 }));
  }, [statusRows]);

  const worstRegions = useMemo(
    () =>
      signals
        .filter((s) => s.ndvi_change != null)
        .map((s) => ({ name: s.region_name, loss: -(s.ndvi_change as number), biome: s.biome }))
        .sort((a, b) => b.loss - a.loss)
        .slice(0, 6),
    [signals]
  );
  const worstMax = Math.max(0.001, ...worstRegions.map((r) => r.loss));

  const trendData = useMemo(() => trend.map((t) => ({ ...t, m: monthLabel(t.month) })), [trend]);

  /** Marquee needs recognisable wildlife: binomials only, threatened ones first. */
  const showcase = useMemo(() => {
    const rank = (s: TopSpecies) =>
      (s.conservation_status && ["CR", "EN", "VU", "NT"].includes(s.conservation_status) ? 0 : 1) +
      (s.endemic ? -0.5 : 0);
    return top
      .filter((s) => s.scientific_name.trim().includes(" "))
      .sort((a, b) => rank(a) - rank(b) || b.observations - a.observations)
      .slice(0, 12);
  }, [top]);

  const primaryCta = user
    ? { to: "/dashboard", label: "Open your dashboard" }
    : { to: "/signup", label: "Create your free account" };

  return (
    <div className="lp">
      <header className={`lp-nav ${scrolled ? "on" : ""}`}>
        <div className="lp-nav-inner">
          <Link to="/" className="lp-brand" onClick={() => setMenuOpen(false)}>
            <span className="lp-brand-mark"><IconLeaf size={18} /></span>
            <span className="lp-brand-text">
              SAMBA
              <span>Madagascar Environmental Hub</span>
            </span>
          </Link>

          <nav className={`lp-nav-links ${menuOpen ? "open" : ""}`} onClick={() => setMenuOpen(false)}>
            <a href="#platform">Platform</a>
            <a href="#live">Live data</a>
            <a href="#species">Species</a>
            <a href="#how">How it works</a>
            <a href="#sources">Sources</a>
            {!user && (
              <Link className="lp-nav-menu-cta" to="/login">Sign in</Link>
            )}
          </nav>

          <div className="lp-nav-cta">
            {user ? (
              <Link className="lp-btn lp-btn-primary" to="/dashboard">
                Dashboard <IconArrowRight size={15} />
              </Link>
            ) : (
              <>
                <Link className="lp-btn lp-btn-quiet" to="/login">Sign in</Link>
                <Link className="lp-btn lp-btn-primary" to="/signup">
                  Get started <IconArrowRight size={15} />
                </Link>
              </>
            )}
            <button
              className="lp-burger"
              aria-label="Toggle navigation"
              aria-expanded={menuOpen}
              onClick={() => setMenuOpen((v) => !v)}
            >
              <span /><span /><span />
            </button>
          </div>
        </div>
      </header>

      {/* ---------------------------------------------------------- hero --- */}
      <section className="lp-hero">
        <div className="lp-hero-bg" aria-hidden="true">
          <span className="lp-orb lp-orb-1" />
          <span className="lp-orb lp-orb-2" />
          <span className="lp-orb lp-orb-3" />
          <div className="lp-grain" />
        </div>

        <div className="lp-hero-inner">
          <div className="lp-hero-copy">
            <span className="lp-pill">
              <span className="lp-dot" />
              Live · {summary ? `${summary.regions} regions under monitoring` : "connecting to the network"}
            </span>
            <h1>
              Madagascar's forests, climate and wildlife —
              <em> watched continuously.</em>
            </h1>
            <p>
              SAMBA fuses satellite vegetation imagery, climate reanalysis and millions of biodiversity
              records into one decision-ready picture: where forest is being lost, how the climate is
              shifting, and which endemic species are running out of habitat.
            </p>
            <div className="lp-hero-actions">
              <Link className="lp-btn lp-btn-primary lp-btn-lg" to={primaryCta.to}>
                {primaryCta.label} <IconArrowRight size={17} />
              </Link>
              <a className="lp-btn lp-btn-outline lp-btn-lg" href="#live">See the live data</a>
            </div>
            <div className="lp-hero-stats">
              <div><b>{fmt(regions)}</b><span>Regions</span></div>
              <div><b>{fmt(species)}</b><span>Species tracked</span></div>
              <div><b>{fmt(observations)}</b><span>Observations</span></div>
              <div><b>{fmt(readings)}</b><span>Sensor readings</span></div>
            </div>
          </div>

          <div className="lp-hero-map">
            <MadagascarMap signals={signals} />
          </div>
        </div>

        <a className="lp-scroll-cue" href="#platform" aria-label="Scroll to platform overview">
          <IconChevronDown size={20} />
        </a>
      </section>

      {/* -------------------------------------------------------- ticker --- */}
      <div className="lp-ticker" aria-hidden="true">
        <div className="lp-ticker-track">
          {[0, 1].map((copy) => (
            <div className="lp-ticker-run" key={copy}>
              {(signals.length ? signals : []).map((s) => (
                <span key={`${copy}-${s.region_name}`}>
                  <i className={`lp-tick-dot ${(s.ndvi_change ?? 0) < -0.05 ? "hot" : ""}`} />
                  {s.region_name}
                  <b>
                    NDVI {s.ndvi_change != null && s.ndvi_change >= 0 ? "+" : ""}
                    {s.ndvi_change != null ? s.ndvi_change.toFixed(3) : "—"}
                  </b>
                </span>
              ))}
              {!signals.length && <span>Waiting for the ingestion network…</span>}
            </div>
          ))}
        </div>
      </div>

      {/* ------------------------------------------------------ platform --- */}
      <section className="lp-section" id="platform">
        <div className="lp-wrap">
          <div className="lp-head lp-reveal">
            <span className="lp-eyebrow">The platform</span>
            <h2>One pipeline, from raw pixels to a decision you can defend</h2>
            <p>
              Every layer is reproducible: the same ingestion jobs, the same statistical models and the
              same regional alignment behind every number on the screen.
            </p>
          </div>

          <div className="lp-features">
            {FEATURES.map((f, i) => (
              <article className="lp-feature lp-reveal" key={f.title} style={{ transitionDelay: `${i * 60}ms` }}>
                <span className={`lp-feature-icon a-${f.accent}`}>{f.icon}</span>
                <h3>{f.title}</h3>
                <p>{f.body}</p>
                <span className="lp-feature-tag">{f.tag}</span>
              </article>
            ))}
          </div>
        </div>
      </section>

      {/* ----------------------------------------------------- live data --- */}
      <section className="lp-section lp-section-tint" id="live">
        <div className="lp-wrap">
          <div className="lp-head lp-reveal">
            <span className="lp-eyebrow">Live from the platform</span>
            <h2>Not a mock-up — this is the current state of the database</h2>
            <p>
              These panels query the same public endpoints the dashboard uses. They update the moment a new
              ingestion run lands.
            </p>
          </div>

          <div className="lp-live-grid">
            <div className="lp-card lp-reveal lp-card-wide">
              <div className="lp-card-head">
                <div>
                  <h3>Biodiversity observations</h3>
                  <span>Monthly records, split by source</span>
                </div>
                <span className="lp-badge">{fmt(summary?.species_observations ?? 0)} total</span>
              </div>
              {trendData.length ? (
                <ResponsiveContainer width="100%" height={230}>
                  <AreaChart data={trendData} margin={{ top: 8, right: 10, bottom: 0, left: -18 }}>
                    <defs>
                      <linearGradient id="lp-g1" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor={CHART.gbif} stopOpacity={0.35} />
                        <stop offset="100%" stopColor={CHART.gbif} stopOpacity={0.02} />
                      </linearGradient>
                      <linearGradient id="lp-g2" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor={CHART.inaturalist} stopOpacity={0.32} />
                        <stop offset="100%" stopColor={CHART.inaturalist} stopOpacity={0.02} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke={CHART.grid} vertical={false} />
                    <XAxis dataKey="m" fontSize={11} minTickGap={28} tickMargin={6} />
                    <YAxis fontSize={11} />
                    <Tooltip />
                    <Area type="monotone" dataKey="gbif" name="GBIF" stackId="1" stroke={CHART.gbif}
                      fill="url(#lp-g1)" strokeWidth={2} isAnimationActive={false} />
                    <Area type="monotone" dataKey="inaturalist" name="iNaturalist" stackId="1"
                      stroke={CHART.inaturalist} fill="url(#lp-g2)" strokeWidth={2} isAnimationActive={false} />
                  </AreaChart>
                </ResponsiveContainer>
              ) : (
                <div className="lp-empty">Waiting for observation data…</div>
              )}
              <div className="lp-legend">
                <span><i style={{ background: CHART.gbif }} />GBIF — bulk occurrence records</span>
                <span><i style={{ background: CHART.inaturalist }} />iNaturalist — community sightings</span>
              </div>
            </div>

            <div className="lp-card lp-reveal">
              <div className="lp-card-head">
                <div>
                  <h3>Conservation status</h3>
                  <span>Species by IUCN Red List category</span>
                </div>
                <span className="lp-badge lp-badge-alert">{fmt(threatened)} threatened</span>
              </div>
              <div className="lp-bars">
                {statusBars.map((r) => (
                  <div className="lp-bar-row" key={r.status}>
                    <span className="lp-bar-key" title={IUCN_LABEL[statusKey(r.status)]}>{r.status}</span>
                    <span className="lp-bar-track">
                      <i style={{ width: `${r.pct}%`, background: IUCN_COLOR[statusKey(r.status)] }} />
                    </span>
                    <span className="lp-bar-val">{fmt(r.species)}</span>
                  </div>
                ))}
                {!statusBars.length && <div className="lp-empty">Waiting for Red List data…</div>}
              </div>
              <p className="lp-card-note">
                {summary
                  ? `${fmt(summary.species_with_status)} of ${fmt(summary.species)} species carry an assessed status.`
                  : "Red List status is resolved during ingestion."}
              </p>
            </div>

            <div className="lp-card lp-reveal">
              <div className="lp-card-head">
                <div>
                  <h3>Steepest vegetation decline</h3>
                  <span>NDVI change since monitoring began</span>
                </div>
              </div>
              <div className="lp-bars">
                {worstRegions.map((r) => (
                  <div className="lp-bar-row" key={r.name}>
                    <span className="lp-bar-name">{r.name}</span>
                    <span className="lp-bar-track">
                      <i
                        style={{
                          width: `${(r.loss / worstMax) * 100}%`,
                          background: r.loss >= 0.08 ? "#c62828" : r.loss >= 0.05 ? "#ef6c00" : "#f59e0b",
                        }}
                      />
                    </span>
                    <span className="lp-bar-val">−{r.loss.toFixed(3)}</span>
                  </div>
                ))}
                {!worstRegions.length && <div className="lp-empty">Waiting for satellite data…</div>}
              </div>
              <p className="lp-card-note">Lower NDVI means less living vegetation cover in the region.</p>
            </div>
          </div>
        </div>
      </section>

      {/* ------------------------------------------------------- species --- */}
      <section className="lp-section lp-section-dark" id="species">
        <div className="lp-wrap">
          <div className="lp-head lp-head-invert lp-reveal">
            <span className="lp-eyebrow">What's at stake</span>
            <h2>Roughly nine in ten Malagasy species live nowhere else on Earth</h2>
            <p>
              SAMBA tracks each one against the habitat it depends on — so a change in forest cover becomes a
              named, ranked risk instead of a statistic.
            </p>
          </div>
        </div>

        <div className="lp-marquee">
          <div className="lp-marquee-track">
            {[0, 1].map((copy) => (
              <div className="lp-marquee-run" key={copy} aria-hidden={copy === 1}>
                {showcase.map((s) => (
                  <article className="lp-species" key={`${copy}-${s.species_id}`}>
                    <SpeciesPhoto
                      name={s.scientific_name}
                      status={s.conservation_status}
                      endemic={s.endemic}
                      height={150}
                    />
                    <div className="lp-species-body">
                      <b>{s.scientific_name}</b>
                      <span>{speciesMeta(s.scientific_name).common}</span>
                      <div className="lp-species-foot">
                        <span>{fmt(s.observations)} records</span>
                        <span>{s.regions} regions</span>
                      </div>
                    </div>
                  </article>
                ))}
                {!showcase.length &&
                  [0, 1, 2, 3, 4, 5].map((i) => <div className="lp-species lp-species-skeleton" key={`s${i}`} />)}
              </div>
            ))}
          </div>
        </div>

        <div className="lp-wrap">
          <div className="lp-species-cta lp-reveal">
            <Link className="lp-btn lp-btn-primary" to={user ? "/biodiversity" : "/signup"}>
              Explore the species atlas <IconArrowRight size={15} />
            </Link>
          </div>
        </div>
      </section>

      {/* ----------------------------------------------------------- how --- */}
      <section className="lp-section" id="how">
        <div className="lp-wrap">
          <div className="lp-head lp-reveal">
            <span className="lp-eyebrow">How it works</span>
            <h2>Four steps, running on a schedule</h2>
            <p>Ingestion is idempotent and queue-backed, so a re-run repairs gaps instead of duplicating them.</p>
          </div>

          <ol className="lp-steps">
            {STEPS.map((s, i) => (
              <li className="lp-step lp-reveal" key={s.title} style={{ transitionDelay: `${i * 80}ms` }}>
                <span className="lp-step-n">{String(i + 1).padStart(2, "0")}</span>
                <h3>{s.title}</h3>
                <p>{s.body}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      {/* --------------------------------------------------------- roles --- */}
      <section className="lp-section lp-section-tint">
        <div className="lp-wrap">
          <div className="lp-head lp-reveal">
            <span className="lp-eyebrow">Built for</span>
            <h2>Five roles, one shared source of truth</h2>
            <p>Access is scoped by role, so field data, model training and policy reporting never collide.</p>
          </div>

          <div className="lp-roles">
            {ROLES.map((r, i) => (
              <article className="lp-role lp-reveal" key={r.title} style={{ transitionDelay: `${i * 60}ms` }}>
                <span className="lp-role-icon">{r.icon}</span>
                <div>
                  <h3>{r.title}</h3>
                  <p>{r.body}</p>
                </div>
              </article>
            ))}
          </div>
        </div>
      </section>

      {/* ------------------------------------------------------- sources --- */}
      <section className="lp-section" id="sources">
        <div className="lp-wrap">
          <div className="lp-head lp-reveal">
            <span className="lp-eyebrow">Data sources</span>
            <h2>Authoritative feeds, reconciled region by region</h2>
            <p>Nothing here is synthetic. Every layer is traceable to a public scientific provider.</p>
          </div>

          <div className="lp-sources">
            {SOURCES.map((s, i) => (
              <article className="lp-source lp-reveal" key={s.name} style={{ transitionDelay: `${i * 60}ms` }}>
                <span className="lp-source-icon">{s.icon}</span>
                <b>{s.name}</b>
                <span className="lp-source-kind">{s.kind}</span>
                <p>{s.body}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      {/* ----------------------------------------------------- final cta --- */}
      <section className="lp-cta">
        <div className="lp-wrap lp-cta-inner lp-reveal">
          <div>
            <h2>Start monitoring with real data today</h2>
            <p>
              Free for researchers, students and conservation NGOs. Bring your own region, or start from the
              {summary ? ` ${summary.regions} ` : " "}already under continuous monitoring.
            </p>
          </div>
          <div className="lp-cta-actions">
            <Link className="lp-btn lp-btn-primary lp-btn-lg" to={primaryCta.to}>
              {primaryCta.label} <IconArrowRight size={17} />
            </Link>
            {!user && <Link className="lp-btn lp-btn-outline lp-btn-lg" to="/login">Sign in</Link>}
          </div>
        </div>
      </section>

      <footer className="lp-footer">
        <div className="lp-wrap lp-footer-inner">
          <div className="lp-footer-brand">
            <span className="lp-brand-mark"><IconLeaf size={18} /></span>
            <div>
              <b>SAMBA</b>
              <p>System for the Administration of Malagasy Biodiversity Assessment.</p>
            </div>
          </div>
          <nav className="lp-footer-links">
            <a href="#platform">Platform</a>
            <a href="#live">Live data</a>
            <a href="#species">Species</a>
            <a href="#how">How it works</a>
            <a href="#sources">Sources</a>
            <Link to="/login">Sign in</Link>
            <Link to="/signup">Create account</Link>
          </nav>
        </div>
        <div className="lp-wrap lp-footer-note">
          Data: Sentinel-2 / Landsat via Google Earth Engine · NASA POWER · GBIF · iNaturalist. Species photos
          courtesy of the iNaturalist community.
        </div>
      </footer>
    </div>
  );
}

const FEATURES = [
  {
    title: "Deforestation detection",
    body: "Monthly NDVI series per region, scanned with a Pettitt change-point test to pinpoint when a forest started to break down.",
    tag: "Change-point analysis",
    accent: "danger",
    icon: <IconAxe size={20} />,
  },
  {
    title: "Climate trajectories",
    body: "Temperature, rainfall and humidity reanalysis with SARIMA forecasts, so a dry season can be anticipated rather than reported.",
    tag: "SARIMA forecasting",
    accent: "amber",
    icon: <IconThermometer size={20} />,
  },
  {
    title: "Species distribution models",
    body: "Occurrence records modelled against environmental covariates to estimate where a species can still survive.",
    tag: "Habitat suitability",
    accent: "green",
    icon: <IconPaw size={20} />,
  },
  {
    title: "Automated alerts",
    body: "Model output becomes ranked, severity-tagged alerts routed to the people who can act — with acknowledgement tracking.",
    tag: "Severity ranked",
    accent: "violet",
    icon: <IconBell size={20} />,
  },
  {
    title: "Region-aligned data lake",
    body: "Satellite, climate and biodiversity feeds are resampled onto the same monthly grid per region, so layers are actually comparable.",
    tag: "Spatio-temporal join",
    accent: "water",
    icon: <IconLayers size={20} />,
  },
  {
    title: "Reports you can hand over",
    body: "Export any view as CSV or PDF, stored in object storage with a stable link for funders, ministries and field teams.",
    tag: "CSV · PDF export",
    accent: "green",
    icon: <IconFileText size={20} />,
  },
];

const STEPS = [
  {
    title: "Ingest",
    body: "Queue-backed jobs pull satellite composites, climate reanalysis and occurrence records from four public providers.",
  },
  {
    title: "Align",
    body: "Every record is snapped to a Malagasy region and a month, cleaned of duplicates and out-of-range values.",
  },
  {
    title: "Model",
    body: "Training runs produce versioned artefacts; a separate inference service serves them without touching the API.",
  },
  {
    title: "Act",
    body: "Findings surface as maps, charts and alerts — then leave the platform as a report someone can sign.",
  },
];

const ROLES = [
  {
    title: "Environmental researchers",
    body: "Query aligned time series, inspect change-points and record field observations against a region.",
    icon: <IconLeaf size={18} />,
  },
  {
    title: "NGOs & policymakers",
    body: "Track alerts by severity, acknowledge them, and export the evidence behind a funding or policy decision.",
    icon: <IconShield size={18} />,
  },
  {
    title: "Data scientists",
    body: "Trigger training runs, compare model versions and read the metrics behind every prediction.",
    icon: <IconCpu size={18} />,
  },
  {
    title: "Students & the public",
    body: "Explore the atlas, the maps and the national trends without an account getting in the way.",
    icon: <IconUsers size={18} />,
  },
];

const SOURCES = [
  {
    name: "Google Earth Engine",
    kind: "Satellite imagery",
    body: "Sentinel-2 and Landsat composites reduced to monthly NDVI per region.",
    icon: <IconSatellite size={18} />,
  },
  {
    name: "NASA POWER",
    kind: "Climate reanalysis",
    body: "Daily temperature, precipitation and humidity aggregated to a monthly regional series.",
    icon: <IconThermometer size={18} />,
  },
  {
    name: "GBIF",
    kind: "Occurrence records",
    body: "Bulk species occurrences with taxonomy, coordinates and collection dates.",
    icon: <IconDatabase size={18} />,
  },
  {
    name: "iNaturalist",
    kind: "Community science",
    body: "Research-grade community observations, including the photographs shown across the platform.",
    icon: <IconCamera size={18} />,
  },
];
