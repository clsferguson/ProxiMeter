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
echo "OpenCV: $(python -c 'import cv2; print(cv2.__version__)' 2>/dev/null || echo 'N/A')"
echo "FFmpeg: $(ffmpeg -version 2>/dev/null | head -1 || echo 'N/A')"
echo "Ultralytics: $(python -c 'import ultralytics; print(ultralytics.__version__)' 2>/dev/null || echo 'N/A')"
echo "ONNX Runtime: $(python -c 'import onnxruntime; print(onnxruntime.__version__)' 2>/dev/null || echo 'N/A')"
echo "==============================="

# ============================================================================
# YOLO Model Initialization
# ============================================================================
YOLO_MODEL="${YOLO_MODEL:-yolo11n}"
YOLO_IMAGE_SIZE="${YOLO_IMAGE_SIZE:-640}"
MODEL_DIR="/app/models"
MODEL_PT="${MODEL_DIR}/${YOLO_MODEL}.pt"
MODEL_ONNX="${MODEL_DIR}/${YOLO_MODEL}_${YOLO_IMAGE_SIZE}.onnx"

echo ""
echo "🤖 Initializing YOLO Model..."
echo "   Model: ${YOLO_MODEL}"
echo "   Image Size: ${YOLO_IMAGE_SIZE}x${YOLO_IMAGE_SIZE}"

# Validate YOLO_MODEL
VALID_MODELS="yolo11n yolo11s yolo11m yolo11l yolo11x yolov9t yolov9s yolov9m yolov9l yolov8n yolov8s yolov8m yolov8l yolov8x yolov7 yolov7x yolov6n yolov6s yolov6m yolov6l"
if ! echo "$VALID_MODELS" | grep -qw "$YOLO_MODEL"; then
    echo "   ❌ ERROR: Invalid YOLO_MODEL='${YOLO_MODEL}'"
    echo "   Valid options: ${VALID_MODELS}"
    exit 1
fi

# Validate YOLO_IMAGE_SIZE
VALID_SIZES="320 416 512 640 1280"
if ! echo "$VALID_SIZES" | grep -qw "$YOLO_IMAGE_SIZE"; then
    echo "   ❌ ERROR: Invalid YOLO_IMAGE_SIZE='${YOLO_IMAGE_SIZE}'"
    echo "   Valid options: ${VALID_SIZES}"
    exit 1
fi

# Create model and config directories with proper permissions
mkdir -p "${MODEL_DIR}"
chown appuser:appuser "${MODEL_DIR}"

# Create Ultralytics config directory to avoid permission errors
# Ultralytics tries to write settings.json and persistent_cache.json here
YOLO_CONFIG_DIR="${YOLO_CONFIG_DIR:-/app/config/yolo}"
mkdir -p "${YOLO_CONFIG_DIR}/Ultralytics"
chown -R appuser:appuser "${YOLO_CONFIG_DIR}"
export YOLO_CONFIG_DIR

echo "📁 Config directories:"
echo "   Models: ${MODEL_DIR}"
echo "   YOLO Config: ${YOLO_CONFIG_DIR}"

# Check if ONNX model already exists
if [ -f "${MODEL_ONNX}" ]; then
    echo "   ✅ ONNX model already cached: ${MODEL_ONNX}"
    MODEL_SIZE=$(du -h "${MODEL_ONNX}" | cut -f1)
    echo "   📦 Model size: ${MODEL_SIZE}"
else
    echo "   📥 Downloading YOLO model (first run, may take 30-60 seconds)..."

    # Download and export model using Python
    python -c "
import sys
import os
import warnings
from pathlib import Path

# Suppress warnings before importing ultralytics
os.environ['YOLO_VERBOSE'] = 'False'
warnings.filterwarnings('ignore', category=UserWarning)
warnings.filterwarnings('ignore', category=FutureWarning)

from ultralytics import YOLO
import shutil

try:
    # Download model
    print('   ⏳ Downloading ${YOLO_MODEL}.pt...')
    model = YOLO('${YOLO_MODEL}.pt')

    # Export to ONNX
    print('   ⏳ Exporting to ONNX format...')
    model.export(format='onnx', imgsz=${YOLO_IMAGE_SIZE}, simplify=True, dynamic=False)

    # Copy ONNX file to model directory (handles cross-device links)
    source_onnx = Path('${YOLO_MODEL}.onnx')
    target_onnx = Path('${MODEL_ONNX}')

    if source_onnx.exists():
        shutil.copy2(str(source_onnx), str(target_onnx))
        source_onnx.unlink()  # Remove source after copy
        print(f'   ✅ Model exported: {target_onnx}')
        print(f'   📦 Model size: {target_onnx.stat().st_size / (1024*1024):.1f} MB')
    else:
        print('   ❌ ERROR: ONNX export failed - file not found')
        sys.exit(1)

except Exception as e:
    print(f'   ❌ ERROR: Model initialization failed: {e}')
    sys.exit(1)
" 2>&1

    if [ $? -ne 0 ]; then
        echo "   ❌ ERROR: Failed to download or export YOLO model"
        echo "   Please check internet connectivity and try again"
        exit 1
    fi
fi

echo "   ✅ YOLO model ready: ${YOLO_MODEL}_${YOLO_IMAGE_SIZE}.onnx"
echo ""

# ============================================================================
# GPU Detection (Runtime) - GPU-specific, must run as root
# ============================================================================

GPU_BACKEND_DETECTED="none"

echo "🔍 Detecting GPU hardware..."

# ============================================================================
# NVIDIA GPU Detection and Setup
# ============================================================================
if command -v nvidia-smi &> /dev/null && nvidia-smi &> /dev/null; then
    echo "✅ NVIDIA GPU detected"
    GPU_BACKEND_DETECTED="nvidia"
    nvidia-smi --query-gpu=name,driver_version --format=csv,noheader 2>/dev/null | head -1 | \
        awk -F',' '{printf "   GPU: %s | Driver: %s\n", $1, $2}'

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