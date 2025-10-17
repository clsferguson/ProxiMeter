# syntax=docker/dockerfile:1.7-labs
FROM python:3.12-slim as base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

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
EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=2s --start-period=5s --retries=3 \
  CMD wget -qO- http://127.0.0.1:8000/health || exit 1

CMD ["gunicorn","-w","2","-b","0.0.0.0:8000","src.app.wsgi:app"]
