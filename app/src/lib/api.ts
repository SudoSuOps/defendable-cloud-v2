// DefendableCloud API client — JWT bearer + typed helpers.

const API_BASE = (import.meta.env.VITE_API_BASE || "https://api.defendablecloud.com").replace(/\/$/, "");
const TOKEN_KEY = "dcloud.jwt";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}
export function setToken(t: string | null) {
  if (t) localStorage.setItem(TOKEN_KEY, t);
  else localStorage.removeItem(TOKEN_KEY);
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

interface ApiOpts {
  method?: string;
  body?: unknown;
  auth?: boolean;
  formData?: FormData;
}

export async function api<T = any>(path: string, opts: ApiOpts = {}): Promise<T> {
  const headers = new Headers();
  if (opts.auth !== false) {
    const t = getToken();
    if (t) headers.set("Authorization", `Bearer ${t}`);
  }
  let body: BodyInit | undefined;
  if (opts.formData) {
    body = opts.formData;
  } else if (opts.body !== undefined) {
    headers.set("Content-Type", "application/json");
    body = JSON.stringify(opts.body);
  }
  const res = await fetch(`${API_BASE}${path}`, { method: opts.method || "GET", headers, body });
  const text = await res.text();
  let data: any = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = text;
  }
  if (!res.ok) {
    const msg = (data && data.detail) || (data && data.error) || `request failed (${res.status})`;
    throw new ApiError(res.status, typeof msg === "string" ? msg : JSON.stringify(msg));
  }
  return data as T;
}

export const apiBase = API_BASE;
