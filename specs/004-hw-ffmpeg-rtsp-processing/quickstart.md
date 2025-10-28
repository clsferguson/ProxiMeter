# Quickstart: Hardware Accelerated FFmpeg RTSP Processing

**Date**: October 23, 2025  
**Feature**: 004-hw-ffmpeg-rtsp-processing  

## Setup

1. **Prerequisites**:
   - Docker & Docker Compose
   - GPU with drivers (NVIDIA/AMD/Intel) if hardware acceleration desired
   - RTSP stream source (e.g., IP camera)

2. **Environment Variables** (in .env or docker-compose.yml):
   ```
   GPU_BACKEND=nvidia  # or amd, intel; entrypoint.sh detects and overrides
   YOLO_MODEL=yolo11n
   IMAGE_SIZE=640
   APP_PORT=8000
   MQTT_ENABLED=false  # set true for MQTT
   ```

3. **Build & Run**:
   ```bash
   docker-compose up --build
   # Or with GPU (NVIDIA example):
   docker-compose --profile gpu up --build
   ```

4. **Access UI**:
   - Open http://localhost:8000
   - Add stream: Provide RTSP URL, optional FFmpeg params (defaults auto-applied with GPU flags)

5. **Verify**:
   - Check logs for GPU detection and FFmpeg versions
   - /health should return &quot;healthy&quot;
   - Start stream; view MJPEG at /streams/{id}/mjpeg
   - Monitor metrics at /metrics

## Development

- Backend: cd src; uvicorn app.main:app --reload
- Frontend: cd frontend; npm run dev
- Test FFmpeg params: Use ffprobe in container to validate custom flags

## Troubleshooting

- No GPU detected: Check entrypoint.sh logs; ensure --gpus all in compose
- Invalid params: UI validation errors; fallback to defaults
- Stream fails: Check FFmpeg stderr in logs