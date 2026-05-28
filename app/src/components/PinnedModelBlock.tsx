// Shared surface for the `pinned_model` block on a cook receipt payload.
// Used by ShareView (public receipt page) and RunDetail (member workspace).
// The block is books-and-records: identity + sealed card_sha256 + anchor
// pointer to the pin receipt. Verifiable out-of-band via the share link.

import { Card } from "./ui";

export interface PinnedModel {
  slug: string;
  name: string;
  base: string;
  params_b: number;
  card_sha256: string;
  pinned_at?: string | null;
  declaration?: string | null;
  client_ref?: string | null;
  pin_receipt_id?: string | null;
  pin_receipt_sha256?: string | null;
  pin_share_url?: string | null;
}

export function PinnedModelBlock({ pin, className }: { pin: PinnedModel; className?: string }) {
  // Pin share URL points at the API · convert to the public proof page URL
  // on this app's origin (consistent with how cook lift-proof links work
  // elsewhere — the user expects /r/<token>, not the bare API URL).
  const pinReceiptUrl = pin.pin_share_url
    ? toAppReceiptUrl(pin.pin_share_url)
    : null;

  return (
    <Card
      className={className}
      title="Model declared via pin"
      subtitle="Sealed onto the chain when the cook receipt minted"
    >
      <div className="flex flex-wrap items-baseline gap-3">
        <h3 className="text-base font-semibold text-paper">{pin.name}</h3>
        <span className="rounded-md border border-honey-400/30 bg-honey-300/[0.08] px-2 py-0.5 font-mono text-[10px] uppercase tracking-wide text-honey-200">
          {pin.slug}
        </span>
      </div>
      <p className="mt-1 font-mono text-xs text-paper/45">
        {pin.base} · {pin.params_b}B
      </p>

      <dl className="mt-4 space-y-2 font-mono text-xs">
        <Row k="pinned_at" v={pin.pinned_at ? new Date(pin.pinned_at).toISOString() : "—"} />
        {pin.declaration && <Row k="declaration" v={pin.declaration} />}
        {pin.client_ref && <Row k="client_ref" v={pin.client_ref} />}
        <Row k="card_sha256" v={pin.card_sha256} mono />
        {pin.pin_receipt_sha256 && <Row k="pin_receipt_sha256" v={pin.pin_receipt_sha256} mono />}
      </dl>

      {pinReceiptUrl && (
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <a
            href={pinReceiptUrl}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1.5 text-sm font-medium text-honey-200 underline underline-offset-2 hover:text-honey-100"
          >
            View pin receipt
            <span aria-hidden="true">→</span>
          </a>
          {pin.pin_receipt_id && (
            <span className="font-mono text-[10px] text-paper/35">{pin.pin_receipt_id}</span>
          )}
        </div>
      )}
    </Card>
  );
}

export function PinnedModelInline({ pin }: { pin: PinnedModel }) {
  const pinReceiptUrl = pin.pin_share_url ? toAppReceiptUrl(pin.pin_share_url) : null;
  return (
    <div className="mt-4 flex flex-wrap items-center gap-2 rounded-md border border-honey-400/20 bg-honey-300/[0.04] px-3 py-2 text-xs">
      <span className="rounded border border-honey-400/30 bg-honey-300/[0.08] px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-wide text-honey-200">
        pinned
      </span>
      <span className="text-paper/70">{pin.name}</span>
      <span className="font-mono text-[10px] text-paper/35">{pin.slug}</span>
      {pinReceiptUrl && (
        <a
          href={pinReceiptUrl}
          target="_blank"
          rel="noreferrer"
          className="ml-auto text-honey-200 underline underline-offset-2 hover:text-honey-100"
        >
          View pin receipt →
        </a>
      )}
    </div>
  );
}

function Row({ k, v, mono }: { k: string; v: string; mono?: boolean }) {
  return (
    <div className="flex items-baseline justify-between gap-4">
      <dt className="shrink-0 text-paper/40">{k}</dt>
      <dd className={`break-all text-right ${mono ? "text-paper/75" : "text-paper/85"}`}>{v}</dd>
    </div>
  );
}

// `pin_share_url` is sealed into the cook receipt as the bare API URL
// (https://api.defendablecloud.com/share/shr_...). For UX consistency we
// surface the public proof page at our app origin (/r/<token>). If parsing
// fails, fall back to the original URL so the link still works.
function toAppReceiptUrl(apiShareUrl: string): string {
  try {
    const u = new URL(apiShareUrl);
    const parts = u.pathname.split("/").filter(Boolean);
    const i = parts.indexOf("share");
    if (i >= 0 && parts[i + 1]) {
      return `${window.location.origin}/r/${parts[i + 1]}`;
    }
  } catch {
    /* fall through */
  }
  return apiShareUrl;
}
