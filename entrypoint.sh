#!/bin/bash
set -e

# Emit version information
echo "=== ProxiMeter RTSP Streams ==="
echo "Python version: $(python --version 2>&1)"
echo "FastAPI version: $(python -c 'import fastapi; print(fastapi.__version__)' 2>/dev/null || echo 'unknown')"
echo "Uvicorn version: $(python -c 'import uvicorn; print(uvicorn.__version__)' 2>/dev/null || echo 'unknown')"
echo "OpenCV version: $(python -c 'import cv2; print(cv2.__version__)' 2>/dev/null || echo 'unknown')"
echo "Pydantic version: $(python -c 'import pydantic; print(pydantic.__version__)' 2>/dev/null || echo 'unknown')"
echo "==============================="

# Check for CI_DRY_RUN mode
if [ "${CI_DRY_RUN}" = "true" ] || [ "${CI_DRY_RUN}" = "1" ] || [ "${CI_DRY_RUN}" = "yes" ]; then
    echo "CI_DRY_RUN=true detected. Exiting without starting server."
    exit 0
fi

# Get APP_PORT from environment or default to 8000
APP_PORT="${APP_PORT:-8000}"
echo "Starting Uvicorn on 0.0.0.0:${APP_PORT}"

# Start the ASGI server
exec uvicorn src.app.wsgi:app \
    --host 0.0.0.0 \
    --port "${APP_PORT}" \
    --log-config /dev/null
