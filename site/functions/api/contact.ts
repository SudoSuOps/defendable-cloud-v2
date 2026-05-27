// Cloudflare Pages Function · POST /api/contact
//
// Backs the /contact form on defendableos.com. Sends the submission via
// Resend so it lands at build@defendableos.com — the Resend-verified sender
// domain for the Defendable brand stack.
//
// REQUIRED env var (Cloudflare Pages → Settings → Environment variables ·
// set for BOTH Production and Preview):
//
//   RESEND_API_KEY = re_...
//
// OPTIONAL overrides:
//   CONTACT_TO_EMAIL    (default: build@defendableos.com)
//   CONTACT_FROM_EMAIL  (default: build@defendableos.com · must be on a
//                        Resend-verified domain)

interface Env {
  RESEND_API_KEY: string;
  CONTACT_TO_EMAIL?: string;
  CONTACT_FROM_EMAIL?: string;
}

interface ContactPayload {
  name?: string;
  email?: string;
  company?: string;
  lane?: string;
  message?: string;
  company_url?: string; // honeypot — must stay empty
}

const LANE_LABELS: Record<string, string> = {
  build: "Build / dev / pilot",
  defense: "Defense / compliance / audit",
  press: "Press / analyst",
  partner: "Partner / contributor",
  other: "Other",
};

export const onRequestPost: PagesFunction<Env> = async ({ request, env }) => {
  if (!env.RESEND_API_KEY) {
    return json({ error: "RESEND_API_KEY not configured" }, 503);
  }

  const TO = env.CONTACT_TO_EMAIL || "build@defendableos.com";
  const FROM = env.CONTACT_FROM_EMAIL || "DefendableOS <build@defendableos.com>";

  let body: ContactPayload;
  try {
    body = await request.json();
  } catch {
    return json({ error: "Invalid JSON" }, 400);
  }

  // Honeypot: silently accept bot submissions so they get no signal.
  if (sanitize(body.company_url, 200)) {
    return json({ ok: true });
  }

  const name = sanitize(body.name, 200);
  const email = sanitize(body.email, 320);
  const company = sanitize(body.company, 200);
  const lane = body.lane && LANE_LABELS[body.lane] ? body.lane : "other";
  const message = sanitize(body.message, 5000);

  if (!name || !email || !message) {
    return json({ error: "Name, email, and message are required." }, 400);
  }
  if (!isEmail(email)) {
    return json({ error: "That email doesn't look right." }, 400);
  }
  if (message.length < 10) {
    return json({ error: "Tell us a little more." }, 400);
  }

  const laneLabel = LANE_LABELS[lane];
  const subject = `[${lane.toUpperCase()}] ${name}${company ? ` · ${company}` : ""}`;
  const text = [
    `Lane:    ${laneLabel}`,
    `Name:    ${name}`,
    `Email:   ${email}`,
    company ? `Company: ${company}` : null,
    "",
    "Message:",
    "─────────",
    message,
    "─────────",
    "",
    `(via defendableos.com/contact · ${new Date().toISOString()})`,
  ]
    .filter(Boolean)
    .join("\n");

  const html = `
    <div style="font-family:ui-monospace,Menlo,monospace;color:#222;line-height:1.55;max-width:640px">
      <div style="border-left:3px solid #e8b65a;padding:0 0 0 14px;margin-bottom:18px">
        <div style="font-size:11px;letter-spacing:.22em;text-transform:uppercase;color:#a87f33;font-weight:600">${escape(laneLabel)}</div>
        <div style="font-size:16px;font-weight:600;margin-top:4px">${escape(name)}${company ? ` · ${escape(company)}` : ""}</div>
        <div style="font-size:13px;color:#666">${escape(email)}</div>
      </div>
      <pre style="white-space:pre-wrap;font-family:ui-monospace,Menlo,monospace;font-size:14px;color:#222;background:#fafafa;border:1px solid #eee;border-radius:6px;padding:14px;margin:0">${escape(message)}</pre>
      <div style="font-size:11px;color:#999;margin-top:18px">via defendableos.com/contact · ${new Date().toISOString()}</div>
    </div>
  `.trim();

  try {
    const res = await fetch("https://api.resend.com/emails", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${env.RESEND_API_KEY}`,
      },
      body: JSON.stringify({ from: FROM, to: TO, reply_to: email, subject, text, html }),
    });
    if (!res.ok) {
      const errBody = await res.text();
      console.error("Resend error", res.status, errBody);
      return json({ error: `Mail provider returned ${res.status}` }, 502);
    }
    return json({ ok: true });
  } catch (err) {
    console.error("Resend network error", err);
    return json({ error: "Network failure to mail provider" }, 502);
  }
};

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", "Cache-Control": "no-store" },
  });
}

function sanitize(s: string | undefined, max: number): string {
  if (!s || typeof s !== "string") return "";
  return s.trim().slice(0, max);
}

function isEmail(s: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(s);
}

function escape(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
