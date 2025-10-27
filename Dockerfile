# syntax=docker/dockerfile:1.7-labs

FROM node:22.21.0-bookworm-slim AS frontend-deps
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm install -g npm@latest && \
    npm ci --legacy-peer-deps

FROM frontend-deps AS frontend-build
COPY frontend/ ./
ENV NODE_ENV=production
RUN npm run build

FROM python:3.12-slim-trixie AS python-base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    APP_PORT=8000

WORKDIR /app

# Install base dependencies (FFmpeg will work for all GPUs at build time)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    wget \
    sudo \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip && \
    pip install --root-user-action=ignore -r requirements.txt

# Create appuser but don't switch to it yet
RUN useradd -m -u 10001 appuser

COPY src ./src
COPY entrypoint.sh ./entrypoint.sh

RUN chmod +x /app/entrypoint.sh

RUN mkdir -p /app/config && chown -R appuser:appuser /app
RUN mkdir -p /app/src/app/static/frontend
ENV STATIC_ROOT=/app/src/app/static/frontend

COPY --from=frontend-build /app/frontend/dist /app/src/app/static/frontend

VOLUME ["/app/config"]

EXPOSE ${APP_PORT}

HEALTHCHECK --interval=10s --timeout=2s --start-period=5s --retries=3 \
  CMD wget -qO- http://127.0.0.1:${APP_PORT}/health || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]
