# ProxiMeter Version Information

## Application Version

- **Version**: 0.3.0
- **Feature**: React 19.2 SPA with Tailwind + shadcn/ui Frontend
- **Branch**: 003-frontend-react-migration
- **Date**: 2025-10-21

## Technology Stack

### Core Framework
- **Python**: 3.12 (container base: python:3.12-slim-trixie)
- **FastAPI**: Latest (ASGI web framework)
- **Uvicorn**: Latest (ASGI server)
- **Pydantic**: v2 (data validation)
- **React**: 19.2.0 (frontend SPA)
- **TypeScript**: 5.4.x (strict mode)
- **Vite**: 5.x (bundler/dev server)
- **Tailwind CSS**: 3.4.x (utility-first styling)
- **shadcn/ui**: 2025-10 snapshot (Radix UI + Tailwind component library)

### Dependencies
- **PyYAML**: YAML configuration persistence
- **opencv-python-headless**: RTSP stream decoding and MJPEG encoding
- **starlette**: ASGI toolkit (FastAPI dependency)
- **python-multipart**: Form data handling
- **prometheus-client**: Metrics exposition
- **class-variance-authority**: Utility for shadcn/ui variant generation
- **tailwind-merge**: Tailwind class merging helper (used by shadcn/ui `cn`)
- **lucide-react**: Icon set used by shadcn/ui components
- **react-hook-form**: Form state management paired with shadcn/ui form primitives
- **zod**: Runtime schema validation used in forms

### Development Tools
- **pytest**: Unit and integration testing (backend)
- **ruff**: Python linting and formatting
- **Vitest**: Frontend unit testing
- **@testing-library/react**: React component testing
- **ESLint**: JavaScript/TypeScript linting (includes tailwindcss and react hooks plugins)
- **Prettier**: Code formatting
- **shadcn CLI**: Component generator (`npx shadcn@latest`)

## Runtime Environment

### Container
- **Base Image**: python:3.12-slim-trixie
- **Platform**: linux/amd64
- **User**: Non-root (appuser, UID 10001)
- **Entrypoint**: `/app/entrypoint.sh`

### Environment Variables
- `APP_PORT`: Server port (default: 8000)
- `LOG_LEVEL`: Logging level (default: INFO)
- `CI_DRY_RUN`: Dry-run mode for CI (default: false)

### Volumes
- `/app/config`: Configuration persistence (config.yml)

### Exposed Ports
- `${APP_PORT}`: HTTP server (default: 8000)

### Health Check
- **Endpoint**: `/health`
- **Interval**: 10s
- **Timeout**: 2s
- **Start Period**: 5s
- **Retries**: 3

## API Endpoints

### UI Routes
- `GET /`: React SPA entry point (served static bundle)

### REST API
- `GET /api/streams`: List all streams
- `POST /api/streams`: Create stream
- `GET /api/streams/{id}`: Get stream details
- `PATCH /api/streams/{id}`: Update stream (partial)
- `DELETE /api/streams/{id}`: Delete stream
- `POST /api/streams/reorder`: Reorder streams

### Playback
- `GET /play/{id}.mjpg`: MJPEG stream (multipart/x-mixed-replace, ≤5 FPS)

### Monitoring
- `GET /health`: Health check (returns `{"status": "ok"}`)
- `GET /metrics`: Prometheus metrics

## Metrics Exposed

### HTTP Metrics
- `http_requests_total`: Total HTTP requests (labels: method, endpoint, status)

### Stream Metrics
- `streams_created_total`: Total streams created
- `streams_deleted_total`: Total streams deleted
- `streams_reordered_total`: Total reorder operations

### Playback Metrics
- `active_playback_sessions`: Current active MJPEG sessions
- `playback_frames_total`: Total MJPEG frames served (label: stream_id)
- `playback_fps_current`: Current FPS for active streams (label: stream_id)

## Version Emission

The entrypoint script (`entrypoint.sh`) emits version information on startup:
- Python version
- FastAPI version
- Uvicorn version
- OpenCV version
- Pydantic version

Example output:
```
=== ProxiMeter RTSP Streams ===
Python version: Python 3.12.x
FastAPI version: 0.x.x
Uvicorn version: 0.x.x
OpenCV version: 4.x.x
Pydantic version: 2.x.x
===============================
```

## CI/CD Integration

### CI_DRY_RUN Mode
When `CI_DRY_RUN=true`, the entrypoint:
1. Emits version information
2. Exits without starting the server (exit code 0)

This allows CI pipelines to verify the container builds correctly and dependencies are installed without running the server.

### Build Platform
- **Target**: linux/amd64
- **Builder**: Docker Buildx

### Image Registry
- **Registry**: GitHub Container Registry (ghcr.io)
- **Image**: ghcr.io/clsferguson/proximeter:latest
- **Tag Strategy**: Branch-based (e.g., `002-fastapi-rtsp-streams`)

## Migration Notes

### From 001-flask-hello-counter
- **Framework**: Flask → FastAPI
- **Server**: Gunicorn (WSGI) → Uvicorn (ASGI)
- **Feature**: Hello counter → RTSP stream management
- **Removed**: Counter routes, counter UI, counter metrics
- **Added**: Stream CRUD, MJPEG playback, drag-drop reordering
