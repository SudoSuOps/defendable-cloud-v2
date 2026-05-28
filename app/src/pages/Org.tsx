import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { Badge, Button, Card, ErrorNote, Field, inputClass, Spinner } from "../components/ui";

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
  const [org, setOrg] = useState<OrgInfo | null>(null);
  const [keys, setKeys] = useState<ApiKeyRow[] | null>(null);
  const [usage, setUsage] = useState<UsageStats | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  // API key create flow state
  const [showCreate, setShowCreate] = useState(false);
  const [newKeyName, setNewKeyName] = useState("");
  const [createdKey, setCreatedKey] = useState<ApiKeyCreated | null>(null);
  const [copied, setCopied] = useState(false);

  async function load() {
    try {
      const [o, k, u] = await Promise.all([
        api<OrgInfo>("/org"),
        api<{ api_keys: ApiKeyRow[] }>("/org/api-keys"),
        api<UsageStats>("/org/usage"),
      ]);
      setOrg(o);
      setKeys(k.api_keys);
      setUsage(u);
    } catch (e: any) {
      setErr(e.message || String(e));
    }
  }

  useEffect(() => {
    load();
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
  if (!org || !keys || !usage) return <Spinner label="Loading workspace…" />;

  return (
    <div className="mx-auto max-w-3xl">
      <p className="text-sm font-medium uppercase tracking-widest text-honey-300">Workspace</p>
      <h1 className="mt-2 text-3xl font-semibold tracking-tight text-paper">{org.name}</h1>
      {err && <div className="mt-4"><ErrorNote>{err}</ErrorNote></div>}

      {/* Org info */}
      <Card className="mt-6" title="Org" subtitle="Books-and-records identity for the vault">
        <dl className="grid gap-x-8 gap-y-2 text-sm sm:grid-cols-2">
          <Row k="Slug" v={org.slug} />
          <Row k="Members" v={String(org.member_count)} />
          <Row k="Receipts" v={String(org.receipt_count)} />
          <Row k="Created" v={org.created_at ? new Date(org.created_at).toLocaleString() : "—"} />
        </dl>
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
