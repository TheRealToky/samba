// Thin API client. Uses same-origin relative URLs; nginx (prod) / vite proxy
// (dev) forwards /api to the backend.

const TOKEN_KEY = "samba_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}
export function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token);
}
export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = { ...(options.headers as Record<string, string>) };
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(`/api/v1${path}`, { ...options, headers });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {
      /* ignore */
    }
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  const ct = res.headers.get("content-type") ?? "";
  return (ct.includes("application/json") ? res.json() : (res.text() as unknown)) as Promise<T>;
}

export const api = {
  get: <T>(p: string) => request<T>(p),
  post: <T>(p: string, body?: unknown) =>
    request<T>(p, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    }),
  patch: <T>(p: string, body?: unknown) =>
    request<T>(p, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    }),
};

export interface RegisteredUser {
  id: number;
  name: string;
  email: string;
  role: string;
}

/** Self-registration. The backend always assigns the default (least-privileged)
 *  role and returns the new user — not a token, so callers log in afterwards. */
export async function register(name: string, email: string, password: string): Promise<RegisteredUser> {
  const res = await fetch("/api/v1/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, email, password }),
  });
  if (!res.ok) throw new RegistrationError(res.status, await readDetail(res));
  return res.json();
}

/** Carries the HTTP status so the form can react to 409 (email taken) etc. */
export class RegistrationError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "RegistrationError";
  }
}

/** FastAPI returns `detail` as a string, or a list of validation objects. */
async function readDetail(res: Response): Promise<string> {
  try {
    const { detail } = await res.json();
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail) && detail.length) {
      const first = detail[0];
      const field = Array.isArray(first?.loc) ? first.loc[first.loc.length - 1] : null;
      return field ? `${field}: ${first.msg}` : String(first?.msg ?? res.statusText);
    }
  } catch {
    /* fall through to the status text */
  }
  return res.statusText || "Registration failed";
}

export async function login(email: string, password: string): Promise<string> {
  const form = new URLSearchParams({ username: email, password });
  const res = await fetch("/api/v1/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: form.toString(),
  });
  if (!res.ok) throw new Error("Invalid email or password");
  const data = await res.json();
  setToken(data.access_token);
  return data.access_token;
}

export function downloadUrl(reportId: number): string {
  return `/api/v1/reports/${reportId}/download`;
}
