import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";
import { Badge, Button, Card, ErrorNote, Field, inputClass, Spinner } from "../components/ui";

type MembershipStatus = "pending" | "approved" | "active" | "waitlisted" | "inactive";

interface CheckoutOut {
  url: string;
  session_id: string;
  expires_at: number;
}

interface MembershipApplicationView {
  company_name?: string;
  intended_use?: string;
  referral_source?: string;
}

interface Membership {
  status: MembershipStatus;
  applied_at: string | null;
  activated_at: string | null;
  seat_number: number | null;
  cap: number;
  active_count: number;
  waitlist_position: number | null;
  application: MembershipApplicationView | null;
}

interface OrgInfo {
  id: string;
  name: string;
  slug: string;
  member_count: number;
  receipt_count: number;
  plan: "free" | "pro" | "enterprise";
  created_at: string | null;
}

interface ApiKeyRow {
  id: string;
  name: string;
  key_prefix: string;
  created_at: string | null;
  last_used_at: string | null;
  revoked: boolean;
}

interface ApiKeyCreated {
  id: string;
  name: string;
  key_prefix: string;
  secret: string;
  created_at: string | null;
}

interface OrgMember {
  id: string;
  email: string;
  name: string | null;
  role: "owner" | "member";
  created_at: string | null;
}

interface OrgInvite {
  id: string;
  email: string;
  role: "owner" | "member";
  expires_at: string;
  accepted_at: string | null;
  created_at: string | null;
}

interface InviteCreated {
  id: string;
  email: string;
  role: "owner" | "member";
  invite_url: string;
  expires_at: string;
  created_at: string | null;
}

interface UsageStats {
  receipts_lifetime: number;
  receipts_this_month: number;
  org_seq: number;
  earned_lanes: number;
}

const PLAN_LABEL: Record<string, string> = {
  free: "Free",
  pro: "Pro",
  enterprise: "Enterprise",
};

export function Org() {
  const { me } = useAuth();
  const [org, setOrg] = useState<OrgInfo | null>(null);
  const [keys, setKeys] = useState<ApiKeyRow[] | null>(null);
  const [usage, setUsage] = useState<UsageStats | null>(null);
  const [membership, setMembership] = useState<Membership | null>(null);
  const [members, setMembers] = useState<OrgMember[] | null>(null);
  const [invites, setInvites] = useState<OrgInvite[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  // API key create flow state
  const [showCreate, setShowCreate] = useState(false);
  const [newKeyName, setNewKeyName] = useState("");
  const [createdKey, setCreatedKey] = useState<ApiKeyCreated | null>(null);
  const [createdInvite, setCreatedInvite] = useState<InviteCreated | null>(null);
  const [copied, setCopied] = useState(false);

  // Apply for membership form state
  const [applyCompany, setApplyCompany] = useState("");
  const [applyUse, setApplyUse] = useState("");
  const [applyReferral, setApplyReferral] = useState("");
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState<"owner" | "member">("member");
  const isOwner = me?.role === "owner";

  async function load() {
    try {
      const [o, u, m, memberList] = await Promise.all([
        api<OrgInfo>("/org"),
        api<UsageStats>("/org/usage"),
        api<Membership>("/membership"),
        api<{ members: OrgMember[] }>("/org/members"),
      ]);
      setOrg(o);
      setUsage(u);
      setMembership(m);
      setMembers(memberList.members);
      const canManage = memberList.members.some((member) => member.id === me?.id && member.role === "owner");
      if (canManage) {
        const [k, inv] = await Promise.all([
          api<{ api_keys: ApiKeyRow[] }>("/org/api-keys"),
          api<{ invites: OrgInvite[] }>("/org/invites"),
        ]);
        setKeys(k.api_keys);
        setInvites(inv.invites);
      } else {
        setKeys([]);
        setInvites([]);
      }
    } catch (e: any) {
      setErr(e.message || String(e));
    }
  }

  async function applyForMembership() {
    if (!applyCompany.trim()) return;
    setErr(null);
    setBusy("apply");
    try {
      const out = await api<Membership>("/membership/apply", {
        method: "POST",
        body: {
          company_name: applyCompany.trim(),
          intended_use: applyUse.trim() || undefined,
          referral_source: applyReferral.trim() || undefined,
        },
      });
      setMembership(out);
      setApplyCompany("");
      setApplyUse("");
      setApplyReferral("");
    } catch (e: any) {
      setErr(e.message || String(e));
    } finally {
      setBusy(null);
    }
  }

  async function startCheckout() {
    setErr(null);
    setBusy("checkout");
    try {
      const out = await api<CheckoutOut>("/membership/checkout", {
        method: "POST",
        body: { return_to_origin: window.location.origin },
      });
      // Hand off to Stripe-hosted checkout. The webhook flips status to
      // active when payment lands; we re-fetch /membership on the success
      // round-trip below.
      window.location.assign(out.url);
    } catch (e: any) {
      setErr(e.message || String(e));
      setBusy(null);
    }
  }

  useEffect(() => {
    if (me) load();
  }, [me?.id]);

  // Surface Stripe's success / cancel return param. Success additionally
  // triggers a re-fetch so the freshly-active state shows up without a manual
  // reload (the webhook fires async; we poll once after a beat).
  const [checkoutResult, setCheckoutResult] = useState<"success" | "cancel" | null>(null);
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const r = params.get("checkout");
    if (r === "success" || r === "cancel") {
      setCheckoutResult(r);
      // Strip the param so the banner doesn't survive a refresh.
      params.delete("checkout");
      const next = window.location.pathname + (params.toString() ? `?${params}` : "");
      window.history.replaceState({}, "", next);
      if (r === "success") {
        // The webhook flips status async — give it ~2s then refetch.
        const t = window.setTimeout(() => load(), 2000);
        return () => window.clearTimeout(t);
      }
    }
  }, []);

  async function createKey() {
    if (!newKeyName.trim()) return;
    setErr(null);
    setBusy("create");
    try {
      const out = await api<ApiKeyCreated>("/org/api-keys", {
        method: "POST",
        body: { name: newKeyName.trim() },
      });
      setCreatedKey(out);
      setNewKeyName("");
      setShowCreate(false);
      await load();
    } catch (e: any) {
      setErr(e.message || String(e));
    } finally {
      setBusy(null);
    }
  }

  async function createInvite() {
    if (!inviteEmail.trim()) return;
    setErr(null);
    setBusy("invite");
    try {
      const out = await api<InviteCreated>("/org/invites", {
        method: "POST",
        body: { email: inviteEmail.trim(), role: inviteRole },
      });
      setCreatedInvite(out);
      setInviteEmail("");
      setInviteRole("member");
      await load();
    } catch (e: any) {
      setErr(e.message || String(e));
    } finally {
      setBusy(null);
    }
  }

  async function revoke(id: string) {
    if (!confirm("Revoke this API key? Existing integrations using it will start failing immediately.")) return;
    setBusy(`revoke:${id}`);
    try {
      await api(`/org/api-keys/${id}`, { method: "DELETE" });
      await load();
    } catch (e: any) {
      setErr(e.message || String(e));
    } finally {
      setBusy(null);
    }
  }

  if (err && !org) return <ErrorNote>{err}</ErrorNote>;
  if (!org || !keys || !usage || !membership || !members) return <Spinner label="Loading workspace…" />;

  const m = membership;
  const hasApplied = !!m.applied_at;
  const seatsLeft = Math.max(0, m.cap - m.active_count);

  return (
    <div className="mx-auto max-w-3xl">
      <p className="text-sm font-medium uppercase tracking-widest text-honey-300">Workspace</p>
      <h1 className="mt-2 text-3xl font-semibold tracking-tight text-paper">{org.name}</h1>
      {err && <div className="mt-4"><ErrorNote>{err}</ErrorNote></div>}

      {checkoutResult === "success" && (
        <div className="mt-4 rounded-md border border-emerald-400/30 bg-emerald-400/5 px-4 py-3 text-sm text-emerald-200">
          Payment received · finalizing your seat assignment. The membership card will update shortly.
        </div>
      )}
      {checkoutResult === "cancel" && (
        <div className="mt-4 rounded-md border border-amber-400/30 bg-amber-400/5 px-4 py-3 text-sm text-amber-200">
          Checkout cancelled · no charge made. Your seat hold is still good · activate any time.
        </div>
      )}

      {/* Membership — the headline. */}
      {m.status === "active" ? (
        <Card
          className="mt-6 border-honey-400/40"
          title="Membership · active"
          subtitle="DefendableCloud member · seat held"
          actions={<Badge value="active" />}
        >
          <div className="grid gap-x-8 gap-y-2 text-sm sm:grid-cols-2">
            <Row k="Seat number" v={`${m.seat_number ?? "—"} / ${m.cap}`} />
            <Row k="Member since" v={m.activated_at ? new Date(m.activated_at).toLocaleDateString() : "—"} />
            <Row k="Community" v={`${m.active_count}/${m.cap} active members`} />
            <Row k="Annual fee" v="$100 · billed monthly relationship" />
          </div>
          <p className="mt-4 text-sm text-paper/65">
            All datasets and the CLI are open to you. Compute billed monthly on the relationship — no checkouts, no surprises.
          </p>
        </Card>
      ) : m.status === "waitlisted" ? (
        <Card
          className="mt-6 border-amber-400/40"
          title="Membership · waitlisted"
          subtitle={`You're ${m.waitlist_position ? `#${m.waitlist_position}` : ""} in line · cap is ${m.cap}`}
          actions={<Badge value="waitlisted" />}
        >
          <p className="text-sm text-paper/70">
            DefendableCloud is members-only and capped at <span className="font-semibold text-paper">{m.cap}</span> active seats at a time — real valued members, not an open door. You'll roll into active when a seat opens.
          </p>
          {m.application && (
            <dl className="mt-4 grid gap-x-8 gap-y-2 text-sm sm:grid-cols-2">
              <Row k="Company" v={m.application.company_name || "—"} />
              <Row k="Applied" v={m.applied_at ? new Date(m.applied_at).toLocaleString() : "—"} />
            </dl>
          )}
        </Card>
      ) : m.status === "approved" ? (
        <Card
          className="mt-6 border-emerald-400/40"
          title="Membership · approved"
          subtitle="One step left · activate your seat with the $100/year fee"
          actions={<Badge value="approved" />}
        >
          <p className="text-sm leading-relaxed text-paper/70">
            Welcome aboard. Pay the annual <span className="font-semibold text-paper">$100</span> via secure Stripe checkout and your seat goes live the moment payment lands.
          </p>
          {m.application && (
            <dl className="mt-4 grid gap-x-8 gap-y-2 text-sm sm:grid-cols-2">
              <Row k="Company" v={m.application.company_name || "—"} />
              <Row k="Applied" v={m.applied_at ? new Date(m.applied_at).toLocaleString() : "—"} />
              <Row k="Seats" v={`${m.active_count}/${m.cap} active · ${seatsLeft} open`} />
              <Row k="Annual fee" v="$100 · one-time · manual renewal yearly" />
            </dl>
          )}
          <div className="mt-5 flex flex-wrap items-center gap-3 border-t border-white/5 pt-4">
            <Button disabled={busy === "checkout"} onClick={startCheckout}>
              {busy === "checkout" ? "Opening Stripe…" : "Activate · $100 / year"}
            </Button>
            <span className="text-xs text-paper/45">
              Stripe-hosted checkout. We never see your card. Datasets are free with membership · compute billed monthly.
            </span>
          </div>
        </Card>
      ) : hasApplied ? (
        <Card
          className="mt-6 border-honey-400/40"
          title="Membership · application received"
          subtitle="Reviewing personally · we'll reach out within 48 hours"
          actions={<Badge value="pending" />}
        >
          <p className="text-sm text-paper/70">
            Thanks for applying. DefendableCloud is members-only — we keep it ~{m.cap} at a time so every relationship is real. We'll reach out to <span className="text-paper">{org.name}</span> directly.
          </p>
          {m.application && (
            <dl className="mt-4 grid gap-x-8 gap-y-2 text-sm sm:grid-cols-2">
              <Row k="Company" v={m.application.company_name || "—"} />
              <Row k="Applied" v={m.applied_at ? new Date(m.applied_at).toLocaleString() : "—"} />
              <Row k="Referral" v={m.application.referral_source || "—"} />
              <Row k="Seats" v={`${m.active_count}/${m.cap} active · ${seatsLeft} open`} />
            </dl>
          )}
        </Card>
      ) : (
        <Card
          className="mt-6 border-honey-400/40"
          title="Apply for membership"
          subtitle={`$100/year · capped at ${m.cap} active seats · ${seatsLeft} open`}
        >
          <p className="text-sm leading-relaxed text-paper/70">
            DefendableCloud is a members-only community. Datasets are free, compute is billed monthly on the relationship — no nickel-and-dime, no checkouts. We cap seats at <span className="font-semibold text-paper">{m.cap}</span> so every member gets real value.
          </p>
          <div className="mt-5 space-y-4">
            <Field label="Company / Organization" hint="What we'll refer to you as">
              <input
                className={inputClass}
                value={applyCompany}
                placeholder="Acme Capital Partners"
                onChange={(e) => setApplyCompany(e.target.value)}
              />
            </Field>
            <Field label="Intended use" hint="What you'd want to cook · what you'd want to prove">
              <textarea
                className={inputClass}
                rows={3}
                value={applyUse}
                placeholder="e.g. underwriting an agent for CRE deal review, with audit-grade receipts for the IC"
                onChange={(e) => setApplyUse(e.target.value)}
              />
            </Field>
            <Field label="How did you hear about us?" hint="Optional · helps us understand how the community is growing">
              <input
                className={inputClass}
                value={applyReferral}
                placeholder="Mr. Defendable on X, Pain in the Shed, a member referral, …"
                onChange={(e) => setApplyReferral(e.target.value)}
              />
            </Field>
            <div className="flex flex-wrap items-center gap-3 border-t border-white/5 pt-4">
              <Button disabled={busy === "apply" || !applyCompany.trim()} onClick={applyForMembership}>
                {busy === "apply" ? "Submitting…" : "Apply for membership"}
              </Button>
              <span className="text-xs text-paper/45">
                A human reads every application. We'll reach out within 48 hours.
              </span>
            </div>
          </div>
        </Card>
      )}

      {/* Org info */}
      <Card className="mt-6" title="Org" subtitle="Books-and-records identity for the vault">
        <dl className="grid gap-x-8 gap-y-2 text-sm sm:grid-cols-2">
          <Row k="Slug" v={org.slug} />
          <Row k="Members" v={String(org.member_count)} />
          <Row k="Receipts" v={String(org.receipt_count)} />
          <Row k="Created" v={org.created_at ? new Date(org.created_at).toLocaleString() : "—"} />
        </dl>
      </Card>

      {/* Members + RBAC */}
      <Card
        className="mt-6"
        title="Members"
        subtitle="Owner/member roles · owner-only invites and API key management"
        actions={<Badge value={isOwner ? "owner" : "member"} />}
      >
        <ul className="space-y-3">
          {members.map((m) => (
            <li
              key={m.id}
              className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-white/8 bg-white/[0.02] px-4 py-3"
            >
              <div>
                <div className="font-medium text-paper">{m.email}</div>
                <div className="mt-1 font-mono text-xs text-paper/40">
                  joined {m.created_at ? new Date(m.created_at).toLocaleDateString() : "—"}
                </div>
              </div>
              <Badge value={m.role} />
            </li>
          ))}
        </ul>

        {isOwner && (
          <div className="mt-5 border-t border-white/5 pt-5">
            <div className="grid gap-3 sm:grid-cols-[1fr_8rem_8rem]">
              <input
                className={inputClass}
                type="email"
                placeholder="teammate@company.com"
                value={inviteEmail}
                onChange={(e) => setInviteEmail(e.target.value)}
              />
              <select
                className={inputClass}
                value={inviteRole}
                onChange={(e) => setInviteRole(e.target.value as "owner" | "member")}
              >
                <option value="member">member</option>
                <option value="owner">owner</option>
              </select>
              <Button disabled={busy === "invite" || !inviteEmail.trim()} onClick={createInvite}>
                {busy === "invite" ? "Inviting…" : "Invite"}
              </Button>
            </div>
            {invites.length > 0 && (
              <ul className="mt-4 space-y-2 text-sm">
                {invites.slice(0, 5).map((i) => (
                  <li key={i.id} className="flex flex-wrap items-center justify-between gap-3 text-paper/60">
                    <span>{i.email}</span>
                    <span className="font-mono text-xs">
                      {i.accepted_at ? "accepted" : `expires ${new Date(i.expires_at).toLocaleDateString()}`}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </Card>

      {/* Usage */}
      <Card className="mt-6" title="Usage" subtitle="What this org has minted">
        <dl className="grid gap-x-8 gap-y-2 text-sm sm:grid-cols-2">
          <Row k="Receipts this month" v={String(usage.receipts_this_month)} />
          <Row k="Receipts lifetime" v={String(usage.receipts_lifetime)} />
          <Row k="Chain position (org_seq)" v={String(usage.org_seq)} />
          <Row k="Earned lanes" v={String(usage.earned_lanes)} />
        </dl>
      </Card>

      {/* Plan */}
      <Card
        className="mt-6"
        title="Plan"
        subtitle="Metered billing lands in the next sprint"
        actions={<Badge value={PLAN_LABEL[org.plan] || org.plan} />}
      >
        <p className="text-sm text-paper/65">
          You're on the <span className="font-semibold text-paper">{PLAN_LABEL[org.plan]}</span> plan. Receipts and cooks are free during the beta — metered billing (Stripe) is the next-and-final sprint.
        </p>
        <div className="mt-4">
          <Button variant="ghost" disabled>
            Upgrade coming soon
          </Button>
        </div>
      </Card>

      {/* API keys */}
      <Card
        className="mt-6"
        title="API keys"
        subtitle="Bearer tokens for programmatic access · same auth as the CLI"
        actions={
          !showCreate ? (
            <Button onClick={() => setShowCreate(true)}>+ New key</Button>
          ) : null
        }
      >
        {showCreate && (
          <div className="mb-5 rounded-lg border border-honey-400/30 bg-honey-300/[0.04] p-4">
            <Field label="Key name" hint="Pick something memorable — e.g. 'production-vault-runner'">
              <input
                className={inputClass}
                value={newKeyName}
                autoFocus
                placeholder="production-vault-runner"
                onChange={(e) => setNewKeyName(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") createKey();
                }}
              />
            </Field>
            <div className="mt-4 flex flex-wrap gap-3">
              <Button disabled={busy === "create" || !newKeyName.trim()} onClick={createKey}>
                {busy === "create" ? "Creating…" : "Create key"}
              </Button>
              <Button
                variant="ghost"
                onClick={() => {
                  setShowCreate(false);
                  setNewKeyName("");
                }}
              >
                Cancel
              </Button>
            </div>
          </div>
        )}

        {keys.length === 0 && !showCreate ? (
          <p className="text-sm text-paper/55">
            No API keys yet. The CLI uses your magic-link JWT for now — API keys are useful for CI / production integrations where a long-lived bearer is required.
          </p>
        ) : (
          <ul className="space-y-3">
            {keys.map((k) => (
              <li
                key={k.id}
                className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-white/8 bg-white/[0.02] px-4 py-3"
              >
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-medium text-paper">{k.name}</span>
                    {k.revoked && <Badge value="revoked" />}
                  </div>
                  <div className="mt-1 flex flex-wrap items-center gap-4 font-mono text-xs text-paper/40">
                    <span>{k.key_prefix}…</span>
                    <span>
                      created {k.created_at ? new Date(k.created_at).toLocaleDateString() : "—"}
                    </span>
                    {k.last_used_at && (
                      <span>last used {new Date(k.last_used_at).toLocaleDateString()}</span>
                    )}
                  </div>
                </div>
                {!k.revoked && (
                  <Button
                    variant="danger"
                    disabled={busy === `revoke:${k.id}`}
                    onClick={() => revoke(k.id)}
                  >
                    {busy === `revoke:${k.id}` ? "Revoking…" : "Revoke"}
                  </Button>
                )}
              </li>
            ))}
          </ul>
        )}
      </Card>

      {/* Modal: created key (one-time secret display) */}
      {createdKey && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-ink/85 backdrop-blur-sm px-4"
          onClick={() => setCreatedKey(null)}
        >
          <div
            className="w-full max-w-lg rounded-xl border border-honey-400/30 bg-ink/95 p-6 shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <p className="font-mono text-xs uppercase tracking-widest text-honey-300/80">
              API key created
            </p>
            <h2 className="mt-2 text-xl font-semibold text-paper">{createdKey.name}</h2>
            <p className="mt-3 text-sm text-paper/70">
              This is the <span className="font-semibold text-paper">only time</span> the full key
              is shown. Save it now to your secret manager — if you lose it, revoke and create
              another.
            </p>
            <div className="mt-5 rounded-md border border-honey-400/30 bg-honey-300/[0.06] p-3">
              <div className="break-all font-mono text-xs text-honey-100">{createdKey.secret}</div>
            </div>
            <div className="mt-5 flex flex-wrap gap-3">
              <Button
                onClick={() => {
                  navigator.clipboard.writeText(createdKey.secret);
                  setCopied(true);
                  setTimeout(() => setCopied(false), 1500);
                }}
              >
                {copied ? "Copied ✓" : "Copy key"}
              </Button>
              <Button
                variant="ghost"
                onClick={() => {
                  setCreatedKey(null);
                  setCopied(false);
                }}
              >
                I've saved it
              </Button>
            </div>
            <p className="mt-4 font-mono text-[10px] uppercase tracking-widest text-paper/35">
              use as: <span className="text-paper/55">Authorization: Bearer {createdKey.key_prefix}…</span>
            </p>
          </div>
        </div>
      )}

      {createdInvite && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-ink/85 backdrop-blur-sm px-4"
          onClick={() => setCreatedInvite(null)}
        >
          <div
            className="w-full max-w-lg rounded-xl border border-honey-400/30 bg-ink/95 p-6 shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <p className="font-mono text-xs uppercase tracking-widest text-honey-300/80">
              Invite created
            </p>
            <h2 className="mt-2 text-xl font-semibold text-paper">{createdInvite.email}</h2>
            <p className="mt-3 text-sm text-paper/70">
              Send this one-time invite link through your normal secure channel. It expires in 7 days.
            </p>
            <div className="mt-5 rounded-md border border-honey-400/30 bg-honey-300/[0.06] p-3">
              <div className="break-all font-mono text-xs text-honey-100">{createdInvite.invite_url}</div>
            </div>
            <div className="mt-5 flex flex-wrap gap-3">
              <Button
                onClick={() => {
                  navigator.clipboard.writeText(createdInvite.invite_url);
                  setCopied(true);
                  setTimeout(() => setCopied(false), 1500);
                }}
              >
                {copied ? "Copied ✓" : "Copy invite"}
              </Button>
              <Button
                variant="ghost"
                onClick={() => {
                  setCreatedInvite(null);
                  setCopied(false);
                }}
              >
                Done
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex justify-between gap-3 border-b border-white/5 py-1">
      <dt className="text-paper/45">{k}</dt>
      <dd className="text-right text-paper/80">{v}</dd>
    </div>
  );
}
