import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth";
import AuthShell from "../components/AuthShell";
import { IconAlertCircle, IconEye, IconEyeOff } from "../components/icons";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(email, password);
      navigate("/dashboard");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthShell
      title="Welcome back"
      subtitle="Sign in to your monitoring workspace."
      highlights={[
        "Live deforestation, climate and biodiversity layers",
        "Alerts ranked by severity, with acknowledgement tracking",
        "CSV and PDF exports you can hand to funders",
      ]}
      footer={
        <>
          Don't have an account? <Link to="/signup">Create one free</Link>
        </>
      }
    >
      <form className="auth-form" onSubmit={onSubmit}>
        {error && (
          <div className="auth-alert" role="alert">
            <span className="auth-alert-icon"><IconAlertCircle size={15} /></span>
            <span>{error}</span>
          </div>
        )}

        <div className="auth-field">
          <label htmlFor="email">Email</label>
          <input
            id="email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="email"
            required
          />
        </div>

        <div className="auth-field">
          <label htmlFor="password">Password</label>
          <div className="auth-input-wrap">
            <input
              id="password"
              type={showPassword ? "text" : "password"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              required
            />
            <button
              type="button"
              className="auth-reveal"
              onClick={() => setShowPassword((s) => !s)}
              aria-label={showPassword ? "Hide password" : "Show password"}
            >
              {showPassword ? <IconEyeOff size={16} /> : <IconEye size={16} />}
            </button>
          </div>
        </div>

        <button className="auth-submit" disabled={busy}>
          {busy ? "Signing in…" : "Sign in"}
        </button>
      </form>
    </AuthShell>
  );
}
