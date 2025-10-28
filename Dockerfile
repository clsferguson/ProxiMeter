# syntax=docker/dockerfile:1.7-labs

# ============================================================================
# Stage 1: Frontend Dependencies
# ============================================================================
FROM node:22.21.0-bookworm-slim AS frontend-deps
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm install -g npm@latest && \
    npm ci --legacy-peer-deps

# ============================================================================
# Stage 2: Frontend Build
# ============================================================================
FROM frontend-deps AS frontend-build
COPY frontend/ ./
ENV NODE_ENV=production
RUN npm run build

# ============================================================================
# Stage 3: Python Base + Universal Dependencies
# ============================================================================
FROM python:3.12-slim-trixie AS python-base

# environment
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    APP_PORT=8000

WORKDIR /app

# Install universal system dependencies (no GPU-specific packages)
# These are needed regardless of GPU vendor
RUN apt-get update && apt-get install -y --no-install-recommends \
    # FFmpeg with all GPU backends compiled in
    ffmpeg \
    # OpenCV dependencies
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    # Utilities
    wget \
    procps \
    # Health check and entrypoint needs
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt ./
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip && \
    pip install --root-user-action=ignore -r requirements.txt

# Create non-root user (don't switch yet - entrypoint runs GPU detection as root)
RUN useradd -m -u 10001 appuser

# Copy application code
COPY src ./src
COPY entrypoint.sh ./entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Setup directories with correct permissions
RUN mkdir -p /app/config && chown -R appuser:appuser /app
RUN mkdir -p /app/src/app/static/frontend
ENV STATIC_ROOT=/app/src/app/static/frontend

# Copy frontend build from previous stage
COPY --from=frontend-build /app/frontend/dist /app/src/app/static/frontend

# Volume for persistent config
VOLUME ["/app/config"]

# Expose port
EXPOSE ${APP_PORT}

# Health check (uses wget already installed)
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://127.0.0.1:${APP_PORT}/health/live || exit 1

# Entrypoint handles GPU detection and switching to appuser
ENTRYPOINT ["/app/entrypoint.sh"]
