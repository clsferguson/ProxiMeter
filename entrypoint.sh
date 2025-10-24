#!/bin/bash
set -e

# Emit version information
echo "=== ProxiMeter RTSP Streams ==="
echo "Python version: $(python --version 2>&1)"
echo "FastAPI version: $(python -c 'import fastapi; print(fastapi.__version__)' 2>/dev/null || echo 'unknown')"
echo "Uvicorn version: $(python -c 'import uvicorn; print(uvicorn.__version__)' 2>/dev/null || echo 'unknown')"
echo "OpenCV version: $(python -c 'import cv2; print(cv2.__version__)' 2>/dev/null || echo 'unknown')"
echo "Pydantic version: $(python -c 'import pydantic; print(pydantic.__version__)' 2>/dev/null || echo 'unknown')"
echo "FFmpeg version: $(ffmpeg -version 2>/dev/null | head -1 || echo 'unknown')"
echo "==============================="

# Detect GPU backend
GPU_BACKEND_DETECTED="none"
if command -v nvidia-smi &> /dev/null; then
    GPU_BACKEND_DETECTED="nvidia"
    echo "Detected NVIDIA GPU"
elif command -v rocm-smi &> /dev/null; then
    GPU_BACKEND_DETECTED="amd"
    echo "Detected AMD GPU"
elif command -v vainfo &> /dev/null && vainfo | grep -q "VAProfile"; then
    GPU_BACKEND_DETECTED="intel"
    echo "Detected Intel GPU"
else
    echo "No supported GPU detected"
fi
export GPU_BACKEND_DETECTED

# Check for CI_DRY_RUN mode
if [ "${CI_DRY_RUN}" = "true" ] || [ "${CI_DRY_RUN}" = "1" ] || [ "${CI_DRY_RUN}" = "yes" ]; then
    echo "CI_DRY_RUN=true detected. Exiting without starting server."
    exit 0
fi

# Get APP_PORT from environment or default to 8000
APP_PORT="${APP_PORT:-8000}"
echo "Starting Uvicorn on 0.0.0.0:${APP_PORT}"

# Set PYTHONPATH to include src directory for proper imports
export PYTHONPATH=/app/src:${PYTHONPATH}

# Start the ASGI server
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port "${APP_PORT}"
