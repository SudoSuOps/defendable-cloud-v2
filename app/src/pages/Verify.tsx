import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Button, ErrorNote, Field, inputClass } from "../components/ui";

function Wordmark() {
  return (
    <Link to="/" className="mb-8 flex items-center justify-center gap-2.5" aria-label="DefendableCloud Vault">
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
  );
}

// Accepts a raw token, a /r/<token> path, or a full share URL.
// Returns the token alone, or null if no token can be extracted.
function extractToken(raw: string): string | null {
  const s = raw.trim();
  if (!s) return null;
  const m = s.match(/\/r\/([A-Za-z0-9_-]+)/);
  if (m) return m[1];
  if (/^[A-Za-z0-9_-]+$/.test(s)) return s;
  return null;
}

export function Verify() {
  const nav = useNavigate();
  const [raw, setRaw] = useState("");
  const [err, setErr] = useState<string | null>(null);

  function submit(e: React.FormEvent) {
    e.preventDefault();
    const token = extractToken(raw);
    if (!token) {
      setErr("That doesn't look like a share link or token. Expected a URL like /r/<token> or the token itself.");
      return;
    }
    setErr(null);
    nav(`/r/${token}`);
  }

  return (
    <div className="relative flex min-h-screen items-center justify-center px-6 py-12">
      <div className="absolute inset-0 brand-grid" aria-hidden="true" />
      <div className="relative w-full max-w-lg">
        <Wordmark />

        <div className="rounded-xl border border-white/8 bg-white/[0.02] p-6">
          <p className="font-mono text-xs uppercase tracking-widest text-honey-300/80">
            Verify a receipt
          </p>
          <h1 className="mt-2 text-2xl font-semibold tracking-tight text-paper">
            Paste a share link.
          </h1>
          <p className="mt-3 text-sm leading-relaxed text-paper/65">
            We'll open the receipt, recompute its hash, and check the per-org chain.
            No sign-in required. Verification is client-side — no server trust.
          </p>

          <form onSubmit={submit} className="mt-6">
            <Field
              label="Share link or token"
              hint="e.g. https://app.defendablecloud.com/r/shr_3f7c…  or  shr_3f7c…"
            >
              <input
                className={inputClass}
                type="text"
                autoFocus
                placeholder="https://app.defendablecloud.com/r/…"
                value={raw}
                onChange={(e) => setRaw(e.target.value)}
              />
            </Field>
            <div className="mt-5">
              <Button type="submit" className="w-full">
                Open and verify
              </Button>
            </div>
            {err && (
              <div className="mt-3">
                <ErrorNote>{err}</ErrorNote>
              </div>
            )}
          </form>

          <div className="mt-6 border-t border-white/5 pt-5">
            <p className="font-mono text-xs uppercase tracking-widest text-paper/40">What this proves</p>
            <ul className="mt-2 space-y-1.5 text-sm leading-relaxed text-paper/65">
              <li>· The receipt's content matches its recorded SHA-256.</li>
              <li>· The receipt links to the prior receipt in the same org's hash chain.</li>
              <li>· The verdict, findings, and approver were sealed at the time of mint.</li>
            </ul>
          </div>
        </div>

        <p className="mt-6 text-center text-xs text-paper/30">
          Don't have a receipt yet? <Link to="/login" className="text-honey-300/70 hover:text-honey-200">Sign in</Link> to mint one. · to the shed
        </p>
      </div>
    </div>
  );
}
