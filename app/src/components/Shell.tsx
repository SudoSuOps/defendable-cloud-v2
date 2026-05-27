import type { ReactNode } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../lib/auth";

function Wordmark() {
  return (
    <Link to="/" className="flex items-center gap-2.5" aria-label="DefendableCloud Vault">
      <svg viewBox="0 0 32 32" className="h-7 w-7" aria-hidden="true">
        <rect width="32" height="32" rx="6" fill="#0a0a0a" stroke="#e6ab2a" strokeWidth="1" />
        <g fill="none" stroke="#f6c64b" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
          <path d="M8 6h12l4 4v16H8z" />
          <path d="M12 12h8M12 16h10M12 20h6" strokeWidth="1.2" opacity="0.7" />
        </g>
      </svg>
      <span className="text-sm font-semibold tracking-tight text-paper">
        DefendableCloud <span className="text-paper/40">Vault</span>
      </span>
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
              <Link to="/agents" className="text-paper/60 transition-colors hover:text-paper">Agents</Link>
              <Link to="/datasets" className="text-paper/60 transition-colors hover:text-paper">Datasets</Link>
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
