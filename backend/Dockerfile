FROM python:3.12-slim

# Install UV
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# System deps for asyncpg + docling PDF rendering
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency spec and app source (needed by hatchling to build the wheel)
COPY pyproject.toml .
COPY app/ ./app/

# Install directly into the system Python — no venv, no portability issues.
RUN uv pip install --system --no-cache .

# Copy remaining source (alembic/, main.py, alembic.ini, etc.)
COPY . .

RUN mkdir -p /app/uploads

COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

CMD ["/docker-entrypoint.sh"]
