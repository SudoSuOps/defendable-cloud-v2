import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";
import { Badge, Button, Card, ErrorNote, Spinner } from "../components/ui";

interface AdminApplicationRow {
  org_id: string;
  org_slug: string;
  org_name: string;
  applicant_email: string | null;
  status: "pending" | "waitlisted";
  applied_at: string | null;
  waitlist_position: number | null;
  company_name: string | null;
  intended_use: string | null;
  referral_source: string | null;
}

interface ApplicationList {
  applications: AdminApplicationRow[];
  count: number;
}

export function Admin() {
  const { me } = useAuth();
  const [rows, setRows] = useState<AdminApplicationRow[] | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [flash, setFlash] = useState<string | null>(null);

  async function load() {
    try {
      const r = await api<ApplicationList>("/admin/applications");
      setRows(r.applications);
    } catch (e: any) {
      setErr(e.message || String(e));
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function approve(slug: string, label: string) {
    setErr(null);
    setBusy(slug);
    try {
      await api(`/admin/applications/${encodeURIComponent(slug)}/approve`, {
        method: "POST",
      });
      setFlash(`${label} approved · awaiting their $100 activation.`);
      await load();
      window.setTimeout(() => setFlash(null), 6000);
    } catch (e: any) {
      setErr(e.message || String(e));
    } finally {
      setBusy(null);
    }
  }

  return (
    <div>
      <p className="text-sm font-medium uppercase tracking-widest text-honey-300">Admin</p>
      <h1 className="mt-2 text-3xl font-semibold tracking-tight text-paper">
        Membership review queue.
      </h1>
      <p className="mt-3 max-w-2xl text-sm leading-relaxed text-paper/60">
        Pending and waitlisted applications. Approve flips the org to{" "}
        <span className="font-mono text-paper/80">approved</span> · they then
        pay the $100 annual fee via Stripe to activate the seat.
      </p>
      <p className="mt-2 text-xs text-paper/40">
        Acting as <span className="font-mono text-paper/60">{me?.email}</span>
      </p>

      {err && <div className="mt-4"><ErrorNote>{err}</ErrorNote></div>}
      {flash && (
        <div className="mt-4 rounded-md border border-emerald-400/30 bg-emerald-400/5 px-4 py-3 text-sm text-emerald-200">
          {flash}
        </div>
      )}

      {!rows && !err && <div className="mt-6"><Spinner label="Loading applications…" /></div>}

      {rows && rows.length === 0 && (
        <Card className="mt-6">
          <p className="text-sm text-paper/65">
            No pending applications. The queue is clear.
          </p>
        </Card>
      )}

      {rows && rows.length > 0 && (
        <div className="mt-6 space-y-3">
          {rows.map((r) => (
            <Card
              key={r.org_id}
              actions={
                <Badge value={r.status} />
              }
            >
              <div className="flex flex-wrap items-baseline gap-3">
                <h3 className="text-lg font-semibold text-paper">
                  {r.company_name || r.org_name}
                </h3>
                <span className="font-mono text-xs text-paper/45">{r.org_slug}</span>
                {r.applied_at && (
                  <span className="font-mono text-[10px] text-paper/35">
                    applied {new Date(r.applied_at).toLocaleString()}
                  </span>
                )}
                {r.status === "waitlisted" && r.waitlist_position != null && (
                  <span className="font-mono text-[10px] text-amber-300/80">
                    #{r.waitlist_position} in line
                  </span>
                )}
              </div>

              {r.intended_use && (
                <p className="mt-3 text-sm leading-relaxed text-paper/75">
                  {r.intended_use}
                </p>
              )}

              <dl className="mt-4 grid gap-x-8 gap-y-1.5 text-xs sm:grid-cols-2">
                <Row k="applicant" v={r.applicant_email || "—"} />
                <Row k="org name" v={r.org_name} />
                {r.referral_source && <Row k="referral" v={r.referral_source} />}
              </dl>

              <div className="mt-5 flex flex-wrap items-center gap-3 border-t border-white/5 pt-4">
                <Button
                  disabled={busy === r.org_slug}
                  onClick={() => approve(r.org_slug, r.company_name || r.org_name)}
                >
                  {busy === r.org_slug ? "Approving…" : "Approve"}
                </Button>
                <span className="text-xs text-paper/45">
                  They'll see the Activate · $100 / year CTA on their /org page.
                </span>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex items-baseline justify-between gap-3 border-b border-white/5 py-1">
      <dt className="text-paper/40">{k}</dt>
      <dd className="break-all text-right text-paper/85">{v}</dd>
    </div>
  );
}
