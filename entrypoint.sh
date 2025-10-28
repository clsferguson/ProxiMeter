#!/bin/bash
set -e

# ============================================================================
# Version Info
# ============================================================================
echo "=== ProxiMeter RTSP Streams ==="
echo "Python: $(python --version 2>&1)"
echo "FastAPI: $(python -c 'import fastapi; print(fastapi.__version__)' 2>/dev/null || echo 'N/A')"
echo "Uvicorn: $(python -c 'import uvicorn; print(uvicorn.__version__)' 2>/dev/null || echo 'N/A')"
echo "FFmpeg: $(ffmpeg -version 2>/dev/null | head -1 || echo 'N/A')"
echo "==============================="

# ============================================================================
# GPU Detection (Runtime) - GPU-specific, must run as root
# ============================================================================

GPU_BACKEND_DETECTED="none"

echo "🔍 Detecting GPU hardware..."

# NVIDIA GPU
if command -v nvidia-smi &> /dev/null && nvidia-smi &> /dev/null; then
    echo "✅ NVIDIA GPU detected"
    GPU_BACKEND_DETECTED="nvidia"
    nvidia-smi --query-gpu=name,driver_version --format=csv,noheader 2>/dev/null | head -1 | \
        awk -F',' '{printf "   GPU: %s | Driver: %s\n", $1, $2}'
    echo "   Using host NVIDIA driver libraries"

# AMD GPU
elif command -v rocm-smi &> /dev/null && rocm-smi &> /dev/null; then
    echo "✅ AMD GPU detected"
    GPU_BACKEND_DETECTED="amd"
    rocm-smi --showproductname 2>/dev/null | head -1 | sed 's/^/   /' || true
    echo "   Using host AMD ROCm driver"

# Intel GPU
elif command -v vainfo &> /dev/null && vainfo 2>/dev/null | grep -q "VAProfile"; then
    echo "✅ Intel GPU detected"
    GPU_BACKEND_DETECTED="intel"
    vainfo 2>/dev/null | grep "Driver version" | sed 's/^/   /' || true
    echo "   Using host Intel VA-API driver"

# Fallback: DRI devices present
elif [ -d "/dev/dri" ] && [ "$(ls -A /dev/dri 2>/dev/null)" ]; then
    echo "ℹ️  /dev/dri devices detected"
    GPU_BACKEND_DETECTED="intel"
    ls -la /dev/dri/ 2>/dev/null | grep -E "card|render" | sed 's/^/   /' || true

else
    echo "⚠️  No GPU detected"
    echo "   Application requires GPU hardware acceleration"
fi

export GPU_BACKEND_DETECTED
echo "🎯 Selected GPU Backend: $GPU_BACKEND_DETECTED"

# ============================================================================
# FFmpeg GPU Capability Check
# ============================================================================
echo ""
echo "🔧 FFmpeg hardware acceleration support:"
ffmpeg -hwaccels 2>&1 | tail -n +2 | head -n -1 | sed 's/^/   /'

if ffmpeg -hwaccels 2>&1 | grep -qE "cuda|vaapi|qsv"; then
    echo "✅ GPU acceleration available"
else
    echo "⚠️  No GPU acceleration in FFmpeg"
fi

# ============================================================================
# CI Dry Run Check
# ============================================================================
if [ "${CI_DRY_RUN}" = "true" ] || [ "${CI_DRY_RUN}" = "1" ]; then
    echo ""
    echo "CI_DRY_RUN detected - exiting without starting server"
    exit 0
fi

# ============================================================================
# Start Application (drop to appuser)
# ============================================================================
APP_PORT="${APP_PORT:-8000}"
export PYTHONPATH=/app/src:${PYTHONPATH}

echo ""
echo "👤 Dropping privileges to appuser..."
echo "🌐 Starting FastAPI on 0.0.0.0:${APP_PORT}..."
echo ""

# Drop to appuser and start app
exec su -s /bin/bash -c "exec uvicorn app.main:app --host 0.0.0.0 --port ${APP_PORT}" appuser
