#!/bin/bash
set -e

echo "=== ProxiMeter RTSP Streams ==="
echo "Python version: $(python --version 2>&1)"
echo "FastAPI version: $(python -c 'import fastapi; print(fastapi.__version__)' 2>/dev/null || echo 'unknown')"
echo "Uvicorn version: $(python -c 'import uvicorn; print(uvicorn.__version__)' 2>/dev/null || echo 'unknown')"
echo "Pydantic version: $(python -c 'import pydantic; print(pydantic.__version__)' 2>/dev/null || echo 'unknown')"
echo "FFmpeg version: $(ffmpeg -version 2>/dev/null | head -1 || echo 'unknown')"
echo "==============================="

# ============================================================================
# GPU Detection and Library Installation (as root)
# ============================================================================

GPU_BACKEND_DETECTED="none"

echo "🔍 Detecting GPU hardware..."

# Check for NVIDIA GPU
if command -v nvidia-smi &> /dev/null && nvidia-smi &> /dev/null; then
    echo "✅ NVIDIA GPU detected"
    GPU_BACKEND_DETECTED="nvidia"
    
    # Install NVIDIA CUDA libraries at runtime
    echo "📦 Installing NVIDIA CUDA libraries..."
    apt-get update -qq
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        wget \
        gnupg2 \
        ca-certificates
    
    # Add NVIDIA CUDA repository
    wget -qO - https://developer.download.nvidia.com/compute/cuda/repos/debian12/x86_64/3bf863cc.pub | apt-key add - 2>/dev/null || true
    echo "deb https://developer.download.nvidia.com/compute/cuda/repos/debian12/x86_64 /" > /etc/apt/sources.list.d/cuda.list
    
    apt-get update -qq
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        libnvcuvid1 \
        libnvidia-encode1 || echo "⚠️  Could not install some NVIDIA libraries"
    
    rm -rf /var/lib/apt/lists/*
    echo "✅ NVIDIA libraries installed"

# Check for AMD GPU
elif command -v rocm-smi &> /dev/null && rocm-smi &> /dev/null; then
    echo "✅ AMD GPU detected"
    GPU_BACKEND_DETECTED="amd"
    
    # Install AMD VAAPI libraries
    echo "📦 Installing AMD VAAPI libraries..."
    apt-get update -qq
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        va-driver-all \
        libva-drm2 \
        libva2 \
        mesa-va-drivers
    
    rm -rf /var/lib/apt/lists/*
    echo "✅ AMD libraries installed"

# Check for Intel GPU
elif command -v vainfo &> /dev/null && vainfo 2>/dev/null | grep -q "VAProfile"; then
    echo "✅ Intel GPU detected"
    GPU_BACKEND_DETECTED="intel"
    
    # Install Intel QSV libraries
    echo "📦 Installing Intel QSV libraries..."
    apt-get update -qq
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        intel-media-va-driver-non-free \
        libmfx1 \
        vainfo || echo "⚠️  Could not install some Intel libraries"
    
    rm -rf /var/lib/apt/lists/*
    echo "✅ Intel libraries installed"

elif [ -d "/dev/dri" ]; then
    echo "ℹ️  /dev/dri detected, assuming Intel GPU"
    GPU_BACKEND_DETECTED="intel"
    
    # Install Intel QSV libraries
    echo "📦 Installing Intel QSV libraries..."
    apt-get update -qq
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        intel-media-va-driver-non-free \
        libmfx1 \
        vainfo || echo "⚠️  Could not install some Intel libraries"
    
    rm -rf /var/lib/apt/lists/*
    echo "✅ Intel libraries installed"

else
    echo "⚠️  No GPU detected - running without hardware acceleration"
    echo "   This application requires GPU support for optimal performance"
fi

export GPU_BACKEND_DETECTED
echo "🎯 GPU Backend: $GPU_BACKEND_DETECTED"

# Verify FFmpeg has GPU support
echo "🔧 Verifying FFmpeg GPU support..."
ffmpeg -hwaccels 2>&1 | grep -E "cuda|vaapi|qsv" && echo "✅ GPU acceleration available" || echo "⚠️  No GPU acceleration in FFmpeg"

# ============================================================================
# CI Dry Run Check
# ============================================================================

if [ "${CI_DRY_RUN}" = "true" ] || [ "${CI_DRY_RUN}" = "1" ] || [ "${CI_DRY_RUN}" = "yes" ]; then
    echo "CI_DRY_RUN=true detected. Exiting without starting server."
    exit 0
fi

# ============================================================================
# Start Application (drop to appuser)
# ============================================================================

APP_PORT="${APP_PORT:-8000}"
export PYTHONPATH=/app/src:${PYTHONPATH}

echo "👤 Switching to appuser..."
echo "🌐 Starting FastAPI server on 0.0.0.0:${APP_PORT}..."

# Drop privileges to appuser and start the app
exec su -s /bin/bash -c "exec uvicorn app.main:app --host 0.0.0.0 --port ${APP_PORT}" appuser
