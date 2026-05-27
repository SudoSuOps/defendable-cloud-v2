import type { ButtonHTMLAttributes, ReactNode } from "react";

export function Button({
  variant = "primary",
  className = "",
  children,
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "ghost" | "danger" }) {
  const base =
    "inline-flex items-center justify-center gap-2 rounded-md px-4 py-2 text-sm font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-50";
  const styles = {
    primary: "bg-honey-300 text-ink hover:bg-honey-200",
    ghost: "border border-white/10 text-paper/80 hover:border-white/25 hover:text-paper",
    danger: "border border-red-500/40 text-red-300 hover:bg-red-500/10",
  }[variant];
  return (
    <button className={`${base} ${styles} ${className}`} {...rest}>
      {children}
    </button>
  );
}

export function Card({
  children,
  className = "",
  title,
  subtitle,
  actions,
}: {
  children?: ReactNode;
  className?: string;
  title?: ReactNode;
  subtitle?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <div className={`rounded-xl border border-white/8 bg-white/[0.02] ${className}`}>
      {(title || actions) && (
        <div className="flex items-start justify-between gap-4 border-b border-white/5 px-5 py-4">
          <div>
            {title && <div className="font-semibold tracking-tight text-paper">{title}</div>}
            {subtitle && <div className="mt-0.5 text-xs text-paper/50">{subtitle}</div>}
          </div>
          {actions}
        </div>
      )}
      <div className="px-5 py-4">{children}</div>
    </div>
  );
}

const STATUS_TONE: Record<string, string> = {
  pass: "text-emerald-300 border-emerald-400/30 bg-emerald-400/10",
  approved: "text-emerald-300 border-emerald-400/30 bg-emerald-400/10",
  receipted: "text-honey-200 border-honey-400/30 bg-honey-300/10",
  risk: "text-amber-300 border-amber-400/30 bg-amber-400/10",
  checked: "text-amber-300 border-amber-400/30 bg-amber-400/10",
  fail: "text-red-300 border-red-400/30 bg-red-400/10",
  rejected: "text-red-300 border-red-400/30 bg-red-400/10",
  skip: "text-paper/50 border-white/10 bg-white/5",
  draft: "text-paper/60 border-white/10 bg-white/5",
};

export function Badge({ value }: { value: string }) {
  const tone = STATUS_TONE[value?.toLowerCase()] || "text-paper/70 border-white/10 bg-white/5";
  return (
    <span className={`inline-block rounded-md border px-2 py-0.5 font-mono text-xs uppercase tracking-wide ${tone}`}>
      {value}
    </span>
  );
}

export function Field({
  label,
  children,
  hint,
}: {
  label: string;
  children: ReactNode;
  hint?: string;
}) {
  return (
    <label className="block">
      <span className="block text-xs font-medium uppercase tracking-widest text-paper/50">{label}</span>
      <div className="mt-2">{children}</div>
      {hint && <span className="mt-1 block text-xs text-paper/40">{hint}</span>}
    </label>
  );
}

export const inputClass =
  "w-full rounded-md border border-white/10 bg-white/[0.03] px-3.5 py-2.5 text-sm text-paper placeholder:text-paper/35 transition-colors focus:border-honey-400/50 focus:outline-none focus:ring-1 focus:ring-honey-400/40";

export function Spinner({ label }: { label?: string }) {
  return (
    <div className="flex items-center gap-2 text-sm text-paper/50">
      <span className="h-3 w-3 animate-spin rounded-full border-2 border-honey-300/30 border-t-honey-300" />
      {label || "Loading…"}
    </div>
  );
}

export function ErrorNote({ children }: { children: ReactNode }) {
  return <p className="text-sm text-red-400">{children}</p>;
}

export function Callout({ title, children }: { title?: string; children: ReactNode }) {
  return (
    <div className="rounded-lg border border-honey-400/20 bg-honey-300/[0.04] px-4 py-3 text-sm leading-relaxed text-paper/70">
      {title && (
        <div className="mb-1 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-widest text-honey-300/80">
          <span aria-hidden="true">›</span> {title}
        </div>
      )}
      {children}
    </div>
  );
}

export function ExampleList({ items }: { items: string[] }) {
  return (
    <ul className="mt-2 space-y-1">
      {items.map((it, i) => (
        <li key={i} className="flex gap-2 text-sm text-paper/60">
          <span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-honey-300/60" aria-hidden="true" />
          <span>{it}</span>
        </li>
      ))}
    </ul>
  );
}
