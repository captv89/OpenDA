# ── Stage 1: dependency resolver ────────────────────────────────────────────
FROM python:3.12-slim AS builder

# Install UV
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency spec only (layer cache optimisation)
COPY pyproject.toml .

# Create venv and install production deps (no extras) into /app/.venv
RUN uv venv .venv && \
    uv pip install --python .venv/bin/python .

# ── Stage 2: runtime ─────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

# System deps for asyncpg + docling PDF rendering
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy venv from builder
COPY --from=builder /app/.venv .venv

# Copy application source
COPY . .

# Make sure uploads dir exists
RUN mkdir -p /app/uploads

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

# Run migrations then start uvicorn
CMD ["/bin/sh", "-c", "alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port 8000 --workers 2"]
