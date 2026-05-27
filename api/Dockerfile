FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    UVICORN_WORKERS=2 \
    PORT=8080

WORKDIR /app

# System deps for asyncpg + boto3 (minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        && rm -rf /var/lib/apt/lists/*

# Install python deps first (better layer caching)
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip wheel && pip install -r /app/requirements.txt

# App source
COPY app /app/app
COPY alembic.ini /app/alembic.ini

# Healthcheck (used by Fly httpz check too)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -fsS "http://localhost:${PORT}/healthz" || exit 1

EXPOSE 8080

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --workers ${UVICORN_WORKERS} --proxy-headers"]
