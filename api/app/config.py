from __future__ import annotations

from functools import lru_cache
from typing import List, Optional
from urllib.parse import urlparse

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = Field(default="development", alias="APP_ENV")
    app_name: str = Field(default="DefendableCloud API", alias="APP_NAME")
    port: int = Field(default=8080, alias="PORT")

    # Public base URL of the Vault app — magic links point here.
    app_base_url: str = Field(default="http://localhost:5173", alias="APP_BASE_URL")
    # Public base URL of this API — used to build share links.
    api_base_url: str = Field(default="http://localhost:8080", alias="API_BASE_URL")

    database_url: Optional[str] = Field(default=None, alias="DATABASE_URL")

    aws_endpoint_url_s3: str = Field(
        default="https://fly.storage.tigris.dev", alias="AWS_ENDPOINT_URL_S3"
    )
    aws_access_key_id: Optional[str] = Field(default=None, alias="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: Optional[str] = Field(default=None, alias="AWS_SECRET_ACCESS_KEY")
    aws_region: str = Field(default="auto", alias="AWS_REGION")
    tigris_bucket: str = Field(default="defendable-cloud", alias="TIGRIS_BUCKET")

    # Auth
    jwt_secret: str = Field(default="dev-insecure-change-me", alias="JWT_SECRET")
    jwt_ttl_hours: int = Field(default=720, alias="JWT_TTL_HOURS")  # 30 days
    magic_ttl_minutes: int = Field(default=30, alias="MAGIC_TTL_MINUTES")

    # Cook runner (the GPU rig) — shared bearer for the runner API
    runner_token: Optional[str] = Field(default=None, alias="RUNNER_TOKEN")
    # Compute transparency: amortized $/hr for the dedicated rig (shown on receipts)
    rig_usd_per_hour: float = Field(default=0.80, alias="RIG_USD_PER_HOUR")

    # Email (Resend)
    resend_api_key: Optional[str] = Field(default=None, alias="RESEND_API_KEY")
    email_from: str = Field(default="DefendableCloud <build@defendableos.com>", alias="EMAIL_FROM")

    cors_origins_raw: str = Field(default="", alias="CORS_ORIGINS")
    checkout_return_origins_raw: str = Field(default="", alias="CHECKOUT_RETURN_ORIGINS")

    # Membership · members-only community cap. $100/year, trust-based monthly
    # billing once active. Donovan's call: keep it ~100 at a time, real valued
    # members, not open door every hack in the game.
    membership_cap: int = Field(default=100, alias="MEMBERSHIP_CAP")
    # Where membership applications get emailed for human review.
    membership_review_email: str = Field(
        default="build@defendableos.com", alias="MEMBERSHIP_REVIEW_EMAIL"
    )

    # Comma-separated emails (lowercase) allowed to hit /admin/*. Used by
    # the in-app Admin Approval UI; the X-Internal-Key path on
    # /membership/approve remains for scripts and CLI.
    admin_emails_raw: str = Field(default="", alias="ADMIN_EMAILS")

    @property
    def admin_emails(self) -> List[str]:
        if not self.admin_emails_raw:
            return []
        return [e.strip().lower() for e in self.admin_emails_raw.split(",") if e.strip()]

    def is_admin_email(self, email: str | None) -> bool:
        if not email:
            return False
        return email.strip().lower() in self.admin_emails

    # The rails-side dataset stager calls /internal/staging-tasks +
    # /internal/stage-complete with this shared key in the X-Internal-Key
    # header. Set via `flyctl secrets set INTERNAL_API_KEY=...`. The same
    # value lives in the rails-side worker's .env. If unset, /internal/*
    # refuses all calls — fail-closed.
    internal_api_key: Optional[str] = Field(default=None, alias="INTERNAL_API_KEY")

    # Stripe · members-only one-time annual checkout. Test mode for v1
    # (sk_test_...); flip to live mode in Fly secrets when ready to charge
    # the first member. /stripe/webhook verifies the signature against
    # STRIPE_WEBHOOK_SECRET; /membership/checkout creates sessions for the
    # configured STRIPE_PRICE_ID. All three unset = membership checkout
    # surface is unavailable (503 by design — fail-closed).
    stripe_api_key: Optional[str] = Field(default=None, alias="STRIPE_API_KEY")
    stripe_webhook_secret: Optional[str] = Field(default=None, alias="STRIPE_WEBHOOK_SECRET")
    stripe_price_id: Optional[str] = Field(default=None, alias="STRIPE_PRICE_ID")
    # Where Stripe Checkout redirects on success/cancel · defaults to /org so
    # the activation CTA round-trip is one page.
    stripe_success_path: str = Field(default="/org?checkout=success", alias="STRIPE_SUCCESS_PATH")
    stripe_cancel_path: str = Field(default="/org?checkout=cancel", alias="STRIPE_CANCEL_PATH")

    # Dataset access guardrail. Counts are enforced against the immutable
    # download receipt ledger, so changing this value does not require a DB
    # migration. Default: 500 dataset grants per email/principal per rolling day.
    dataset_download_daily_limit: int = Field(default=500, alias="DATASET_DOWNLOAD_DAILY_LIMIT")

    @property
    def cors_origins(self) -> List[str]:
        if not self.cors_origins_raw:
            return ["*"]
        return [o.strip() for o in self.cors_origins_raw.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env.strip().lower() in {"prod", "production"}

    @property
    def checkout_return_origins(self) -> List[str]:
        configured = [
            o.strip().rstrip("/")
            for o in self.checkout_return_origins_raw.split(",")
            if o.strip()
        ]
        app_origin = _origin(self.app_base_url)
        out = [o for o in configured if o]
        if app_origin and app_origin not in out:
            out.append(app_origin)
        return out

    def validate_runtime(self) -> None:
        """Fail fast on production configs that would weaken auth or access.

        Development remains frictionless, but a live deploy should never boot
        with placeholder auth, wildcard CORS, or disabled email delivery.
        """
        if not self.is_production:
            return
        problems: list[str] = []
        if self.jwt_secret == "dev-insecure-change-me" or len(self.jwt_secret) < 32:
            problems.append("JWT_SECRET must be set to a strong non-default value")
        if not self.resend_api_key:
            problems.append("RESEND_API_KEY must be set so magic links are never returned inline")
        if "*" in self.cors_origins:
            problems.append("CORS_ORIGINS must be explicit in production")
        if not self.app_base_url.startswith("https://"):
            problems.append("APP_BASE_URL must be https in production")
        if not self.api_base_url.startswith("https://"):
            problems.append("API_BASE_URL must be https in production")
        if self.dataset_download_daily_limit < 1:
            problems.append("DATASET_DOWNLOAD_DAILY_LIMIT must be at least 1")
        if problems:
            raise RuntimeError("Invalid production configuration: " + "; ".join(problems))

    def allowed_checkout_origin(self, origin: str | None) -> bool:
        if not origin:
            return False
        candidate = origin.strip().rstrip("/")
        parsed = urlparse(candidate)
        if parsed.scheme not in {"https", "http"} or not parsed.netloc:
            return False
        if parsed.scheme == "http" and parsed.hostname not in {"localhost", "127.0.0.1"}:
            return False
        return candidate in self.checkout_return_origins

    @property
    def email_configured(self) -> bool:
        return bool(self.resend_api_key)


@lru_cache(maxsize=1)
def settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


def _origin(url: str) -> str:
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return ""
    return f"{parsed.scheme}://{parsed.netloc}".rstrip("/")
