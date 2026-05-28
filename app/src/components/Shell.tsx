import type { ReactNode } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../lib/auth";

function Wordmark() {
  return (
    <Link to="/" className="flex items-center gap-2" aria-label="DefendableCloud Vault">
      <img src="/defendable-wordmark.png" alt="Defendable" className="h-9 w-auto" />
      <span className="text-sm font-medium tracking-tight text-paper/55">Vault</span>
    </Link>
  );
}

export function Shell({ children }: { children: ReactNode }) {
  const { me, signOut } = useAuth();
  const nav = useNavigate();
  return (
    <div className="min-h-screen font-sans">
      <header className="sticky top-0 z-40 border-b border-white/5 bg-ink/80 backdrop-blur">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-3.5">
          <Wordmark />
          {me && (
            <div className="flex items-center gap-5 text-sm">
              <Link to="/" className="text-paper/60 transition-colors hover:text-paper">Runs</Link>
              <Link to="/plan" className="text-paper/60 transition-colors hover:text-paper">Plan</Link>
              <Link to="/agents" className="text-paper/60 transition-colors hover:text-paper">Agents</Link>
              <Link to="/incidents" className="text-paper/60 transition-colors hover:text-paper">Incidents</Link>
              <Link to="/datasets" className="text-paper/60 transition-colors hover:text-paper">Datasets</Link>
              <Link to="/org" className="text-paper/60 transition-colors hover:text-paper">Org</Link>
              <span className="hidden text-paper/40 sm:inline">{me.email}</span>
              <button
                onClick={() => {
                  signOut();
                  nav("/login");
                }}
                className="text-paper/60 transition-colors hover:text-paper"
              >
                Sign out
              </button>
            </div>
          )}
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-6 py-10">{children}</main>
      <footer className="mx-auto max-w-5xl px-6 py-8 text-center font-mono text-xs uppercase tracking-[0.35em] text-honey-300/40">
        // to the shed
      </footer>
    </div>
  );
}
