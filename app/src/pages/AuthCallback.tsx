import { useEffect, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { api, setToken } from "../lib/api";
import { useAuth } from "../lib/auth";
import { Button, Spinner } from "../components/ui";

export function AuthCallback() {
  const [params] = useSearchParams();
  const nav = useNavigate();
  const { refresh } = useAuth();
  const [err, setErr] = useState<string | null>(null);
  const ran = useRef(false);

  useEffect(() => {
    if (ran.current) return;
    ran.current = true;
    const token = params.get("token");
    if (!token) {
      setErr("missing token");
      return;
    }
    (async () => {
      try {
        const r = await api<{ access_token: string }>("/auth/verify", {
          method: "POST",
          body: { token },
          auth: false,
        });
        setToken(r.access_token);
        await refresh();
        nav("/", { replace: true });
      } catch (e: any) {
        setErr(e.message || "this link is invalid or expired");
      }
    })();
  }, [params, nav, refresh]);

  return (
    <div className="flex min-h-screen items-center justify-center px-6">
      {err ? (
        <div className="max-w-sm text-center">
          <p className="text-sm font-medium uppercase tracking-widest text-honey-300">Sign-in failed</p>
          <p className="mt-3 text-sm text-paper/70">{err}</p>
          <div className="mt-5 flex justify-center">
            <Button variant="ghost" onClick={() => nav("/login")}>Back to sign in</Button>
          </div>
        </div>
      ) : (
        <Spinner label="Signing you in…" />
      )}
    </div>
  );
}
