# ProxiMeter — RTSP Stream Manager

A FastAPI web application for managing and viewing RTSP camera streams. Add, edit, reorder, and delete streams with a clean web interface. View live streams at ≤5 FPS via MJPEG playback.

- Tech: Python 3.12, FastAPI, Uvicorn, Jinja2, Pydantic v2, PyYAML, OpenCV
- Features: Add/Edit/Delete/Reorder RTSP streams, Live MJPEG playback (≤5 FPS), Persistent YAML storage
- Endpoints: `/` (Landing UI), `/api/streams` (REST API), `/play/{id}.mjpg` (Playback), `/health` (Readiness), `/metrics` (Prometheus)
- **Security Warning**: LAN-only deployment; no authentication. RTSP credentials stored in plaintext. Do NOT expose to the internet without proper hardening.

## Quick Start

### Run with Docker (recommended)

```bash
# From repo root
docker compose up --build
```

Open http://localhost:8000 to view the landing page.

### Add Your First Stream

1. Click "Add stream" on the landing page
2. Enter a name (e.g., "Front Door Camera")
3. Enter the RTSP URL (e.g., `rtsp://username:password@192.168.1.100:554/stream`)
4. Click "Add Stream"
5. Click the stream button to start playback

**Note**: RTSP URLs with credentials are stored in plaintext in `config/config.yml`. This is a LAN-only tool.

### Health Check

```bash
curl http://localhost:8000/health
# Returns: {"status":"ok"}
```

### Metrics

```bash
curl http://localhost:8000/metrics
# Returns Prometheus-format metrics
```

### Stop the Application

```bash
docker compose down
```

### Custom Port

If port 8000 is in use, set the `APP_PORT` environment variable:

```bash
APP_PORT=8080 docker compose up --build
```

Or edit `docker-compose.yml` and change the ports mapping.

## Project Structure

```
src/app/
  wsgi.py                    # FastAPI ASGI application entry point
  config_io.py               # YAML persistence (atomic writes)
  logging_config.py          # JSON logging configuration
  metrics.py                 # Prometheus metrics
  api/
    health.py                # Health endpoint
    streams.py               # REST API for streams + playback
    errors.py                # Error schemas and handlers
  ui/
    views.py                 # UI routes (landing, add, edit)
  models/
    stream.py                # Pydantic models (Stream, NewStream, EditStream)
  services/
    streams_service.py       # Business logic for stream management
  utils/
    rtsp.py                  # RTSP/MJPEG playback utilities
    validation.py            # RTSP URL validation
    strings.py               # Credential masking helpers
  middleware/
    rate_limit.py            # Rate limiting middleware
    request_id.py            # Request ID middleware
  templates/
    base.html                # Base layout with header animation
    index.html               # Landing page (stream list)
    add_stream.html          # Add stream form
    edit_stream.html         # Edit stream form
    play.html                # Playback view
  static/
    styles.css               # CSS (header animation, equal-width grid)
    app.js                   # Client-side JS (animations, drag-drop, delete confirm)
config/
  config.yml                 # Stream persistence (mounted volume)
```

## API Endpoints

### REST API

- `GET /api/streams` - List all streams (credentials masked)
- `POST /api/streams` - Create a new stream
- `GET /api/streams/{id}` - Get stream details
- `PATCH /api/streams/{id}` - Update stream (partial)
- `DELETE /api/streams/{id}` - Delete stream
- `POST /api/streams/reorder` - Reorder streams (drag-drop persistence)

### Playback

- `GET /play/{id}.mjpg` - MJPEG stream (multipart/x-mixed-replace, ≤5 FPS, no audio)

### Monitoring

- `GET /health` - Health check (returns `{"status":"ok"}`)
- `GET /metrics` - Prometheus metrics

## Features

### Stream Management

- **Add streams**: Name + RTSP URL with validation (2s connectivity probe)
- **Edit streams**: Update name or URL; re-validates on save
- **Delete streams**: Confirmation dialog before deletion
- **Reorder streams**: Drag-and-drop with visual handles; persists immediately
- **Status tracking**: Streams marked `Inactive` if RTSP unreachable

### Playback

- **MJPEG streaming**: Server-side RTSP decode via OpenCV/FFmpeg
- **Frame rate cap**: ≤5 FPS to reduce bandwidth and CPU
- **No audio**: Video only
- **Error handling**: Banner with "Back to streams" link on failure

### UI/UX

- **Header animation**: Centered on landing, animates to top-left on playback (400-700ms)
- **Equal-width buttons**: Stream buttons in responsive grid (same width per row)
- **Mobile-friendly**: Responsive layout
- **Accessibility**: Keyboard navigation, ARIA labels, focus management

## CI/CD

GitHub Actions builds the linux/amd64 Docker image, performs a smoke test hitting `/health` until it returns `200 ok` (30s timeout), and publishes the image to GitHub Container Registry (ghcr.io).

Pull the latest published image:

```bash
docker pull ghcr.io/clsferguson/proximeter:latest
```

## Security & Safety

⚠️ **LAN-ONLY DEPLOYMENT** ⚠️

- **No authentication**: Anyone on your network can view/manage streams
- **No TLS**: All traffic is unencrypted
- **Plaintext credentials**: RTSP URLs with passwords stored in `config/config.yml`
- **File writes**: Only writes to `/app/config/config.yml` (mounted volume)
- **Rate limiting**: Basic protection (5 req/s, burst 10) on mutating endpoints

**DO NOT expose this application to the internet without proper hardening:**
- Add authentication (e.g., OAuth, basic auth with TLS)
- Enable TLS/HTTPS
- Encrypt credentials at rest
- Implement proper access controls
- Add CSRF protection for production use

## License

MIT © 2025 clsferguson
