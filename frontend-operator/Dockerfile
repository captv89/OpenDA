# ── Stage 1: build ───────────────────────────────────────────────────────────
FROM node:22-alpine AS builder

# Pin pnpm version — avoids corepack hitting npm registry at build time
RUN npm install -g pnpm@10.30.1

WORKDIR /app

# Copy monorepo manifests and lockfile (cache layer)
COPY package.json pnpm-workspace.yaml pnpm-lock.yaml ./
COPY frontend-operator/package.json ./frontend-operator/

# Install only this workspace's dependencies
RUN pnpm install --frozen-lockfile --filter frontend-operator

COPY frontend-operator/ ./frontend-operator/

# Leave VITE_API_BASE empty so the JS uses relative URLs (/api/v1/...).
# Nginx's location /api/ block proxies those to http://backend:8000 internally.
# Never bake a Docker-internal hostname into the bundle — browsers can't resolve it.
ARG VITE_API_BASE=
ENV VITE_API_BASE=$VITE_API_BASE

RUN pnpm --filter frontend-operator build

# ── Stage 2: serve via Nginx ──────────────────────────────────────────────────
FROM nginx:stable-alpine AS runtime

COPY --from=builder /app/frontend-operator/dist /usr/share/nginx/html

RUN printf 'server {\n\
    listen 80;\n\
    root /usr/share/nginx/html;\n\
    index index.html;\n\
    location / {\n\
    try_files $uri $uri/ /index.html;\n\
    }\n\
    location /api/ {\n\
    proxy_pass http://backend:8000;\n\
    proxy_set_header Host $host;\n\
    proxy_set_header X-Real-IP $remote_addr;\n\
    }\n\
    }\n' > /etc/nginx/conf.d/default.conf

EXPOSE 80
