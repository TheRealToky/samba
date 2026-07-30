import { FormEvent, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { RegistrationError } from "../api";
import { useAuth } from "../auth";
import AuthShell from "../components/AuthShell";
import { IconAlertCircle, IconCheck, IconEye, IconEyeOff } from "../components/icons";

type Field = "name" | "email" | "password" | "confirm";
type Values = Record<Field, string>;

const EMPTY: Values = { name: "", email: "", password: "", confirm: "" };

// Mirrors the backend contract (UserCreate): name 1–255, EmailStr, password 8–128.
// The server stays the authority — this only spares the user a round trip.
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[a-z]{2,}$/i;

function validate(v: Values): Partial<Record<Field, string>> {
  const e: Partial<Record<Field, string>> = {};
  if (!v.name.trim()) e.name = "Enter your name.";
  else if (v.name.trim().length > 255) e.name = "Name must be 255 characters or fewer.";

  if (!v.email.trim()) e.email = "Enter your email address.";
  else if (!EMAIL_RE.test(v.email.trim())) e.email = "That doesn't look like a valid email address.";

  if (!v.password) e.password = "Choose a password.";
  else if (v.password.length < 8) e.password = "Use at least 8 characters.";
  else if (v.password.length > 128) e.password = "Use 128 characters or fewer.";

  if (!v.confirm) e.confirm = "Re-type your password.";
  else if (v.confirm !== v.password) e.confirm = "Passwords don't match.";

  return e;
}

const RULES = [
  { label: "8+ characters", test: (p: string) => p.length >= 8 },
  { label: "Upper & lowercase", test: (p: string) => /[a-z]/.test(p) && /[A-Z]/.test(p) },
  { label: "A number", test: (p: string) => /\d/.test(p) },
  { label: "A symbol", test: (p: string) => /[^A-Za-z0-9]/.test(p) },
];

const STRENGTH = ["Too short", "Weak", "Fair", "Good", "Strong"];

export default function Signup() {
  const { signup } = useAuth();
  const navigate = useNavigate();
  const [values, setValues] = useState<Values>(EMPTY);
  const [touched, setTouched] = useState<Partial<Record<Field, boolean>>>({});
  const [formError, setFormError] = useState<{ message: string; emailTaken?: boolean } | null>(null);
  const [showPassword, setShowPassword] = useState(false);
  const [busy, setBusy] = useState(false);

  const errors = useMemo(() => validate(values), [values]);
  const passed = RULES.filter((r) => r.test(values.password)).length;
  const strength = values.password.length < 8 ? 0 : passed;

  const set = (field: Field) => (e: React.ChangeEvent<HTMLInputElement>) => {
    setValues((v) => ({ ...v, [field]: e.target.value }));
    if (formError) setFormError(null);
  };
  const blur = (field: Field) => () => setTouched((t) => ({ ...t, [field]: true }));
  const errorFor = (field: Field) => (touched[field] ? errors[field] : undefined);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setTouched({ name: true, email: true, password: true, confirm: true });
    setFormError(null);
    if (Object.keys(errors).length) return;

    setBusy(true);
    try {
      await signup(values.name.trim(), values.email.trim(), values.password);
      navigate("/dashboard");
    } catch (err) {
      if (err instanceof RegistrationError && err.status === 409) {
        setFormError({ message: "That email is already registered.", emailTaken: true });
      } else {
        setFormError({ message: (err as Error).message || "Something went wrong. Please try again." });
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthShell
      title="Create your account"
      subtitle="Free for researchers, students and conservation organisations."
      highlights={[
        "Live deforestation, climate and biodiversity layers",
        "Alerts ranked by severity, with acknowledgement tracking",
        "CSV and PDF exports you can hand to funders",
      ]}
      footer={
        <>
          Already have an account? <Link to="/login">Sign in</Link>
        </>
      }
    >
      <form className="auth-form" onSubmit={onSubmit} noValidate>
        {formError && (
          <div className="auth-alert" role="alert">
            <span className="auth-alert-icon"><IconAlertCircle size={15} /></span>
            <span>
              {formError.message}{" "}
              {formError.emailTaken && <Link to="/login">Sign in instead</Link>}
            </span>
          </div>
        )}

        <Text
          id="name"
          label="Full name"
          value={values.name}
          onChange={set("name")}
          onBlur={blur("name")}
          error={errorFor("name")}
          autoComplete="name"
          placeholder="Hery Rakoto"
        />

        <Text
          id="email"
          label="Work or school email"
          type="email"
          value={values.email}
          onChange={set("email")}
          onBlur={blur("email")}
          error={errorFor("email")}
          autoComplete="email"
          placeholder="you@organisation.org"
        />

        <div className="auth-field">
          <label htmlFor="password">Password</label>
          <div className="auth-input-wrap">
            <input
              id="password"
              type={showPassword ? "text" : "password"}
              value={values.password}
              onChange={set("password")}
              onBlur={blur("password")}
              autoComplete="new-password"
              aria-invalid={!!errorFor("password")}
              aria-describedby="password-help"
              className={errorFor("password") ? "invalid" : ""}
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

          <div className="auth-meter" aria-hidden="true">
            {[0, 1, 2, 3].map((i) => (
              <span key={i} className={i < strength ? `on s${strength}` : ""} />
            ))}
          </div>
          <div id="password-help" className="auth-rules">
            <span className={`auth-strength s${strength}`}>
              {values.password ? STRENGTH[strength] : "Choose a password"}
            </span>
            {RULES.map((r) => (
              <span key={r.label} className={r.test(values.password) ? "met" : ""}>
                <IconCheck size={11} /> {r.label}
              </span>
            ))}
          </div>
          {errorFor("password") && <p className="auth-error">{errorFor("password")}</p>}
        </div>

        <Text
          id="confirm"
          label="Confirm password"
          type={showPassword ? "text" : "password"}
          value={values.confirm}
          onChange={set("confirm")}
          onBlur={blur("confirm")}
          error={errorFor("confirm")}
          autoComplete="new-password"
        />

        <button className="auth-submit" disabled={busy}>
          {busy ? "Creating your account…" : "Create account"}
        </button>

        <p className="auth-note">
          New accounts start with public access. An administrator can upgrade you to researcher,
          NGO or data-scientist permissions.
        </p>
      </form>
    </AuthShell>
  );
}

function Text({
  id,
  label,
  error,
  ...input
}: {
  id: string;
  label: string;
  error?: string;
} & React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <div className="auth-field">
      <label htmlFor={id}>{label}</label>
      <input
        id={id}
        aria-invalid={!!error}
        aria-describedby={error ? `${id}-error` : undefined}
        className={error ? "invalid" : ""}
        {...input}
      />
      {error && (
        <p className="auth-error" id={`${id}-error`}>
          {error}
        </p>
      )}
    </div>
  );
}
