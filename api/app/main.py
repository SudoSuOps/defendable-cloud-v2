from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.config import settings
from app.routes import agents, auth, cooks, datasets, eval, healthz, incidents, membership, org, projects, public, runner, runs


def create_app() -> FastAPI:
    s = settings()
    app = FastAPI(
        title="DefendableCloud API",
        description=(
            "Hosted Proof of Execution for agentic work. Create a Run, attach evidence, "
            "run verification checks, approve, and issue a hash-chained receipt — JSON + PDF, "
            "stored and shareable. To the shed."
        ),
        version=__version__,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=s.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    app.include_router(healthz.router)
    app.include_router(auth.router)
    app.include_router(org.router)
    app.include_router(membership.router)
    app.include_router(projects.router)
    app.include_router(agents.router)
    app.include_router(incidents.router)
    app.include_router(runs.router)
    app.include_router(eval.router)
    app.include_router(datasets.router)
    app.include_router(cooks.router)
    app.include_router(runner.router)
    app.include_router(public.router)

    @app.get("/")
    def root():
        return {
            "service": "defendable-cloud-api",
            "version": __version__,
            "tagline": "Cloud receipts for agentic work.",
            "endpoints": [
                "/healthz",
                "/auth/request", "/auth/verify", "/auth/me",
                "/projects",
                "/runs", "/runs/{id}", "/runs/{id}/evidence", "/runs/{id}/checks",
                "/runs/{id}/approve", "/runs/{id}/receipt",
                "/share/{token}", "/share/{token}/pdf", "/ledger/verify",
            ],
        }

    return app


app = create_app()
