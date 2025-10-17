# syntax=docker/dockerfile:1.7-labs
FROM python:3.12-slim-trixie as base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    APP_PORT=8000

WORKDIR /app

# Install system dependencies for OpenCV
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Install runtime deps
COPY requirements.txt ./
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

# Create non-root user
RUN useradd -m -u 10001 appuser

# Copy app
COPY src ./src

# Config directory (persist via volume)
RUN mkdir -p /app/config && chown -R appuser:appuser /app
VOLUME ["/app/config"]

USER appuser
EXPOSE ${APP_PORT}

HEALTHCHECK --interval=10s --timeout=2s --start-period=5s --retries=3 \
  CMD wget -qO- http://127.0.0.1:${APP_PORT}/health || exit 1

CMD uvicorn src.app.wsgi:app --host 0.0.0.0 --port ${APP_PORT} --log-config /dev/null
