import { lazy, ReactNode, Suspense } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth";
import Layout from "./components/Layout";
import Landing from "./pages/Landing";
import Login from "./pages/Login";
import Signup from "./pages/Signup";

// The authenticated pages pull in MapLibre and the heavier chart views. Loading
// them lazily keeps the public landing page's first paint off that payload.
const Dashboard = lazy(() => import("./pages/Dashboard"));
const Biodiversity = lazy(() => import("./pages/Biodiversity"));
const Climate = lazy(() => import("./pages/Climate"));
const MapView = lazy(() => import("./pages/MapView"));
const Alerts = lazy(() => import("./pages/Alerts"));
const Reports = lazy(() => import("./pages/Reports"));

function Protected({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="centered">Loading…</div>;
  if (!user) return <Navigate to="/login" replace />;
  return <Suspense fallback={<div className="centered">Loading…</div>}>{children}</Suspense>;
}

export default function App() {
  return (
    <Routes>
      {/* Public marketing surface */}
      <Route path="/" element={<Landing />} />
      <Route path="/login" element={<Login />} />
      <Route path="/signup" element={<Signup />} />
      <Route
        element={
          <Protected>
            <Layout />
          </Protected>
        }
      >
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/biodiversity" element={<Biodiversity />} />
        <Route path="/climate" element={<Climate />} />
        <Route path="/map" element={<MapView />} />
        <Route path="/alerts" element={<Alerts />} />
        <Route path="/reports" element={<Reports />} />
        {/* legacy path */}
        <Route path="/trends" element={<Navigate to="/climate" replace />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
