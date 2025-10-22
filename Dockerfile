# syntax=docker/dockerfile:1.7-labs

FROM node:20.18.0-bookworm-slim AS frontend-deps
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN --mount=type=cache,target=/root/.npm npm ci

FROM frontend-deps AS frontend-build
COPY frontend/ ./
ENV NODE_ENV=production
# Frontend uses hardcoded relative API path '/api' (see frontend/src/lib/constants.ts)
# No build-time API URL configuration needed
RUN npm run build

FROM python:3.12-slim-trixie AS python-base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    APP_PORT=8000

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    wget \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

RUN useradd -m -u 10001 appuser

COPY src ./src
COPY entrypoint.sh ./entrypoint.sh

RUN chmod +x /app/entrypoint.sh

RUN mkdir -p /app/config && chown -R appuser:appuser /app
RUN mkdir -p /app/src/app/static/frontend
ENV STATIC_ROOT=/app/src/app/static/frontend

COPY --from=frontend-build /app/frontend/dist /app/src/app/static/frontend

VOLUME ["/app/config"]

USER appuser
EXPOSE ${APP_PORT}

HEALTHCHECK --interval=10s --timeout=2s --start-period=5s --retries=3 \
  CMD wget -qO- http://127.0.0.1:${APP_PORT}/health || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]
