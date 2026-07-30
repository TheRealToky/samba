import { Link, NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../auth";
import { IconLeaf } from "./icons";

const links = [
  { to: "/dashboard", label: "Overview", end: true },
  { to: "/biodiversity", label: "Biodiversity" },
  { to: "/climate", label: "Climate" },
  { to: "/map", label: "Map" },
  { to: "/alerts", label: "Alerts" },
  { to: "/reports", label: "Reports" },
];

export default function Layout() {
  const { user, logout } = useAuth();
  return (
    <div className="app-shell">
      <header className="topbar">
        <Link className="brand" to="/" title="Back to the public site">
          <span className="brand-mark"><IconLeaf size={18} /></span>
          <span className="brand-text">
            SAMBA
            <span className="brand-sub">Madagascar Environmental Hub</span>
          </span>
        </Link>
        <nav className="nav">
          {links.map((l) => (
            <NavLink key={l.to} to={l.to} end={l.end} className={({ isActive }) => (isActive ? "active" : "")}>
              {l.label}
            </NavLink>
          ))}
        </nav>
        <div className="user-box">
          <span className="user-role">{user?.role}</span>
          <span className="user-name">{user?.name}</span>
          <button className="btn-ghost" onClick={logout}>
            Sign out
          </button>
        </div>
      </header>
      <main className="content">
        <Outlet />
      </main>
      <footer className="app-footer">
        <span className="foot-brand">SAMBA</span> · Madagascar's environmental intelligence hub — deforestation,
        climate &amp; biodiversity. Data: Sentinel/Landsat via Google Earth Engine · GBIF · iNaturalist · NASA POWER.
      </footer>
    </div>
  );
}
