from __future__ import annotations

from functools import lru_cache
from typing import List, Optional

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

    # Membership · members-only community cap. $100/year, trust-based monthly
    # billing once active. Donovan's call: keep it ~100 at a time, real valued
    # members, not open door every hack in the game.
    membership_cap: int = Field(default=100, alias="MEMBERSHIP_CAP")
    # Where membership applications get emailed for human review.
    membership_review_email: str = Field(
        default="build@defendableos.com", alias="MEMBERSHIP_REVIEW_EMAIL"
    )

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

    @property
    def cors_origins(self) -> List[str]:
        if not self.cors_origins_raw:
            return ["*"]
        return [o.strip() for o in self.cors_origins_raw.split(",") if o.strip()]

    @property
    def email_configured(self) -> bool:
        return bool(self.resend_api_key)


@lru_cache(maxsize=1)
def settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
