import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { Button, ErrorNote, Field, inputClass, Spinner } from "../components/ui";

export function Login() {
  const [email, setEmail] = useState("");
  const [state, setState] = useState<"idle" | "sending" | "sent">("idle");
  const [err, setErr] = useState<string | null>(null);
  const [devLink, setDevLink] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setErr(null);
    setState("sending");
    try {
      const r = await api<{ ok: boolean; sent: boolean; dev_link?: string }>("/auth/request", {
        method: "POST",
        body: { email: email.trim() },
        auth: false,
      });
      setDevLink(r.dev_link ?? null);
      setState("sent");
    } catch (e: any) {
      setErr(e.message || "could not send the link");
      setState("idle");
    }
  }

  return (
    <div className="relative flex min-h-screen items-center justify-center px-6">
      <div className="absolute inset-0 brand-grid" aria-hidden="true" />
      <div className="relative w-full max-w-sm">
        <Link to="/" className="mb-8 flex items-center justify-center gap-2.5">
          <svg viewBox="0 0 32 32" className="h-8 w-8" aria-hidden="true">
            <rect width="32" height="32" rx="6" fill="#0a0a0a" stroke="#e6ab2a" strokeWidth="1" />
            <g fill="none" stroke="#f6c64b" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
              <path d="M8 6h12l4 4v16H8z" />
              <path d="M12 12h8M12 16h10M12 20h6" strokeWidth="1.2" opacity="0.7" />
            </g>
          </svg>
          <span className="text-lg font-semibold tracking-tight text-paper">
            DefendableCloud <span className="text-paper/40">Vault</span>
          </span>
        </Link>

        {state === "sent" ? (
          <div className="rounded-xl border border-white/8 bg-white/[0.02] p-6 text-center">
            <p className="text-sm font-medium uppercase tracking-widest text-honey-300">Check your email</p>
            <p className="mt-3 text-sm leading-relaxed text-paper/70">
              We sent a one-time sign-in link to <span className="text-paper">{email}</span>. It expires shortly.
            </p>
            {devLink && (
              <a
                href={devLink}
                className="mt-5 inline-block rounded-md border border-honey-400/40 bg-honey-300/10 px-4 py-2 text-xs font-medium text-honey-200 hover:bg-honey-300/20"
              >
                Dev link (email not configured) — sign in
              </a>
            )}
          </div>
        ) : (
          <form onSubmit={submit} className="rounded-xl border border-white/8 bg-white/[0.02] p-6">
            <p className="mb-5 text-sm leading-relaxed text-paper/70">
              Sign in to create and verify Proof of Execution. No password — we email you a one-time link.
            </p>
            <Field label="Work email">
              <input
                className={inputClass}
                type="email"
                required
                autoFocus
                placeholder="you@company.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </Field>
            <div className="mt-5">
              <Button type="submit" className="w-full" disabled={state === "sending"}>
                {state === "sending" ? <Spinner label="Sending…" /> : "Email me a sign-in link"}
              </Button>
            </div>
            {err && <div className="mt-3"><ErrorNote>{err}</ErrorNote></div>}
          </form>
        )}
        <p className="mt-6 text-center text-xs text-paper/30">Swarm and Bee LLC · to the shed</p>
      </div>
    </div>
  );
}
