# ── Extractor service ─────────────────────────────────────────────────────────
# Heavy image: docling + torch + litellm.
# Intentionally isolated so backend + celery-worker stay slim (~400 MB).
# This container is NEVER exposed outside the Docker network.
FROM python:3.12-slim

# System deps required by docling (poppler for PDF rendering, libGL for CV)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpoppler-cpp-dev \
    poppler-utils \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency resolution
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Install deps first (cache layer — only invalidated on pyproject.toml change)
COPY pyproject.toml .
RUN uv pip install --system --no-cache .

# Copy application code
COPY app/ ./app/
COPY main.py .

# Uploads volume (shared with backend + celery-worker via bind mount)
RUN mkdir -p /app/uploads

EXPOSE 8001

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "1"]
