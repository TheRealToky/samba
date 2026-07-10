import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth";
import Layout from "./components/Layout";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Biodiversity from "./pages/Biodiversity";
import Climate from "./pages/Climate";
import MapView from "./pages/MapView";
import Alerts from "./pages/Alerts";
import Reports from "./pages/Reports";
import { ReactNode } from "react";

function Protected({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="centered">Loading…</div>;
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        element={
          <Protected>
            <Layout />
          </Protected>
        }
      >
        <Route path="/" element={<Dashboard />} />
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
