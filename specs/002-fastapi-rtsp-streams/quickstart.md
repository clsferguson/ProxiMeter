# Quickstart for ProxiMeter RTSP Streams

Prerequisites
- Docker with buildx on amd64

Run
- docker buildx build --platform=linux/amd64 -t proximeter:dev .
- docker run --rm -p 8000:8000 -v $PWD/config:/app/config proximeter:dev

Usage
- Open http://localhost:8000
- Click "Add stream", enter Name and RTSP URL (credentials allowed in URL)
- Playback view opens; header animates; use Back to return to landing
- Manage streams: edit (pencil), delete (with confirm), drag handle to reorder

Notes
- Streams are stored in config/config.yml in the mounted volume
- LAN-only; no auth; do not expose to WAN
- Playback capped at ≤5 FPS; no audio
