import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth";
import { IconArrowRight, IconLeaf } from "../components/icons";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("ds@example.com");
  const [password, setPassword] = useState("password123");
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
    <div className="login-wrap">
      <form className="login-card" onSubmit={onSubmit}>
        <div className="login-brand">
          <span className="mark"><IconLeaf size={20} /></span>
          <h1>SAMBA</h1>
        </div>
        <p className="tag">Madagascar's environmental intelligence hub — deforestation, climate &amp; biodiversity.</p>
        {error && <div className="error">{error}</div>}
        <div className="field">
          <label>Email</label>
          <input value={email} onChange={(e) => setEmail(e.target.value)} type="email" required />
        </div>
        <div className="field">
          <label>Password</label>
          <input value={password} onChange={(e) => setPassword(e.target.value)} type="password" required />
        </div>
        <button className="btn" style={{ width: "100%" }} disabled={busy}>
          {busy ? "Signing in…" : "Sign in"}
        </button>
        <p className="muted" style={{ marginTop: 16 }}>
          Demo: ds@example.com / password123 (data scientist)
        </p>
      </form>
      <Link className="login-back" to="/">
        Back to the SAMBA home page <IconArrowRight size={13} />
      </Link>
    </div>
  );
}
