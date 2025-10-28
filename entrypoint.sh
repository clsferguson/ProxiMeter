#!/bin/bash
set -e

# Check if debug logging is enabled
DEBUG_MODE=false
if [ "${LOG_LEVEL}" = "DEBUG" ]; then
    DEBUG_MODE=true
fi

# ============================================================================
# Version Info
# ============================================================================
echo "=== ProxiMeter RTSP Streams ==="
echo "Python: $(python --version 2>&1)"
echo "FastAPI: $(python -c 'import fastapi; print(fastapi.__version__)' 2>/dev/null || echo 'N/A')"
echo "Uvicorn: $(python -c 'import uvicorn; print(uvicorn.__version__)' 2>/dev/null || echo 'N/A')"
echo "Pydantic: $(python -c 'import pydantic; print(pydantic.__version__)' 2>/dev/null || echo 'N/A')"
echo "FFmpeg: $(ffmpeg -version 2>/dev/null | head -1 || echo 'N/A')"
echo "==============================="

# ============================================================================
# GPU Detection (Runtime) - GPU-specific, must run as root
# ============================================================================

GPU_BACKEND_DETECTED="none"

echo "🔍 Detecting GPU hardware..."

# Function to install packages quietly
install_packages() {
    if [ "$DEBUG_MODE" = true ]; then
        apt-get update && apt-get install -y --no-install-recommends "$@"
    else
        apt-get update >/dev/null 2>&1 && apt-get install -y --no-install-recommends "$@" >/dev/null 2>&1
    fi
}

# ============================================================================
# NVIDIA GPU Detection and Setup
# ============================================================================

if command -v nvidia-smi &> /dev/null && nvidia-smi &> /dev/null; then
    echo "✅ NVIDIA GPU detected"
    GPU_BACKEND_DETECTED="nvidia"
    nvidia-smi --query-gpu=name,driver_version --format=csv,noheader 2>/dev/null | head -1 | \
        awk -F',' '{printf "   GPU: %s | Driver: %s\n", $1, $2}'

    # Install NVIDIA CUDA libraries for FFmpeg
    echo "   📦 Installing NVIDIA CUDA libraries..."

    # install_packages \
    #     gnupg2

    # wget -q https://developer.download.nvidia.com/compute/cuda/repos/debian12/x86_64/cuda-keyring_1.1-1_all.deb
    # dpkg -i cuda-keyring_1.1-1_all.deb
    # rm cuda-keyring_1.1-1_all.deb

    if ! dpkg -l | grep -q libnvcuvid1; then
    #     install_packages \
    #         libnvcuvid1 \
    #         libnvidia-encode1
        
    #     # Clean up
    #     rm -rf /var/lib/apt/lists/*

        echo "   ✅ NVIDIA libraries installed"
    else
        echo "   ✅ NVIDIA libraries already installed"
    fi

    # Verify CUDA library is accessible
    if ldconfig -p | grep -q libnvcuvid.so; then
        echo "   ✅ CUDA video codec library loaded"
    else
        echo "   ⚠️  WARNING: libnvcuvid.so not found in library path"
        echo "   Running ldconfig to refresh library cache..."
        ldconfig
    fi


# ============================================================================
# AMD GPU Detection and Setup
# ============================================================================
elif command -v rocm-smi &> /dev/null && rocm-smi &> /dev/null; then
    echo "✅ AMD GPU detected"
    GPU_BACKEND_DETECTED="amd"
    rocm-smi --showproductname 2>/dev/null | head -1 | sed 's/^/   /' || true

    # Install AMD ROCm libraries for FFmpeg VAAPI
    echo "   📦 Installing AMD VAAPI libraries..."
    if ! dpkg -l | grep -q mesa-va-drivers; then
        install_packages \
            mesa-va-drivers \
            vainfo \
            libva2 \
            libva-drm2 \
            libdrm2 \
            libdrm-amdgpu1
        echo "   ✅ AMD VAAPI libraries installed"
    else
        echo "   ✅ AMD VAAPI libraries already installed"
    fi
    
    # Verify DRI device exists
    if [ -e /dev/dri/renderD128 ]; then
        echo "   ✅ AMD DRI device found: /dev/dri/renderD128"
        # Set permissions if needed
        chmod 666 /dev/dri/renderD128 2>/dev/null || true
    else
        echo "   ⚠️  WARNING: /dev/dri/renderD128 not found"
    fi

# ============================================================================
# Intel GPU Detection and Setup
# ============================================================================
elif command -v vainfo &> /dev/null && vainfo 2>/dev/null | grep -q "VAProfile"; then
    echo "✅ Intel GPU detected"
    GPU_BACKEND_DETECTED="intel"
    vainfo 2>/dev/null | grep "Driver version" | sed 's/^/   /' || true

    # Install Intel QSV libraries for FFmpeg
    echo "   📦 Installing Intel QSV libraries..."
    if ! dpkg -l | grep -q intel-media-va-driver; then
        install_packages \
            intel-media-va-driver \
            vainfo \
            libva2 \
            libva-drm2 \
            libmfx1 \
            libdrm2 \
            libdrm-intel1
        echo "   ✅ Intel QSV libraries installed"
    else
        echo "   ✅ Intel QSV libraries already installed"
    fi
    
    # Verify DRI device exists
    if [ -e /dev/dri/renderD128 ]; then
        echo "   ✅ Intel DRI device found: /dev/dri/renderD128"
        chmod 666 /dev/dri/renderD128 2>/dev/null || true
    else
        echo "   ⚠️  WARNING: /dev/dri/renderD128 not found"
    fi

# ============================================================================
# Fall back on board GPU via /dev/dri
# ============================================================================
elif [ -d "/dev/dri" ] && [ "$(ls -A /dev/dri 2>/dev/null)" ]; then
    echo "ℹ️  /dev/dri devices detected"
    GPU_BACKEND_DETECTED="intel"
    ls -la /dev/dri/ 2>/dev/null | grep -E "card|render" | sed 's/^/   /' || true

# ============================================================================
# No GPU Detected
# ============================================================================
else
    echo "⚠️  No GPU detected"
    echo "   Application requires GPU hardware acceleration"
fi

export GPU_BACKEND_DETECTED
echo "🎯 Selected GPU Backend: $GPU_BACKEND_DETECTED"

# ============================================================================
# FFmpeg GPU Capability Check
# ============================================================================
if [ "$DEBUG_MODE" = true ]; then
    echo ""
    
    # Get comma-separated list of hwaccels
    HWACCELS=$(ffmpeg -hide_banner -hwaccels 2>&1 | tail -n +2 | grep -v '^$' | tr '\n' ',' | sed 's/,$//' | sed 's/,/, /g')
    
    echo "🔧 FFmpeg hardware acceleration support: $HWACCELS"
    
    # Check if GPU acceleration is available
    if echo "$HWACCELS" | grep -qE "cuda|vaapi|qsv"; then
        echo "✅ GPU support available in FFmpeg binary"
    else
        echo "⚠️ GPU support not available in FFmpeg binary"
    fi
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
echo "--------------------------------------------------------------------------------------------------------------------------------------------------------------------------"

# Drop to appuser and start app
exec su -s /bin/bash -c "exec uvicorn app.main:app --host 0.0.0.0 --port ${APP_PORT}" appuser