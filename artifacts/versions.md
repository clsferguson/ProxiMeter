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
- **TypeScript**: 5.9.3 (strict mode enabled)
- **Vite**: 7.1.11 (bundler/dev server)
- **Tailwind CSS**: 4.1.15 (utility-first styling with @tailwindcss/vite)
- **shadcn/ui**: Latest (Radix UI + Tailwind component library)

### Backend Dependencies
- **PyYAML**: YAML configuration persistence
- **opencv-python-headless**: RTSP stream decoding and MJPEG encoding
- **starlette**: ASGI toolkit (FastAPI dependency)
- **python-multipart**: Form data handling
- **prometheus-client**: Metrics exposition
- **Shapely**: Polygon geometry for point-in-polygon checks (future zones feature)

### Frontend Dependencies
- **React**: 19.2.0 (UI framework)
- **React Router**: 7.9.4 (client-side routing)
- **React Hook Form**: 7.65.0 (form state management)
- **Zod**: 4.1.12 (runtime schema validation)
- **class-variance-authority**: 0.7.1 (shadcn/ui variant generation)
- **tailwind-merge**: 3.3.1 (Tailwind class merging helper)
- **lucide-react**: 0.546.0 (icon set for shadcn/ui components)
- **next-themes**: 0.4.6 (light/dark theme management)
- **sonner**: 2.0.7 (toast notifications)
- **@radix-ui/***: Radix UI primitives (dialog, dropdown, alert-dialog, aspect-ratio, label, select, slot)

### Development Tools
- **pytest**: Unit and integration testing (backend)
- **ruff**: Python linting and formatting
- **Vitest**: 3.2.4 (frontend unit testing)
- **@testing-library/react**: 16.3.0 (React component testing)
- **ESLint**: 9.38.0 (JavaScript/TypeScript linting with tailwindcss and react hooks plugins)
- **Prettier**: 3.6.2 (code formatting)
- **TypeScript ESLint**: 8.46.2 (TypeScript linting)
- **shadcn CLI**: Component generator (`npx shadcn@latest`)
- **Terser**: 5.x (JavaScript minification for production builds)
- **@tailwindcss/vite**: 4.1.15 (Vite integration for Tailwind CSS)

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

## Frontend Build Information

### Production Bundle
- **Target**: ES2020 (modern browsers)
- **Minification**: Terser (enabled in production)
- **Code Splitting**: Manual chunks for react-vendor, ui-vendor, and main app
- **Bundle Size**: ~150 kB gzipped (well under 500 kB target)
  - CSS: 7.57 kB gzipped
  - React vendor: 15.34 kB gzipped
  - UI vendor: 26.98 kB gzipped
  - Main app: 97.93 kB gzipped
- **Source Maps**: Disabled in production
- **Tree-shaking**: Enabled (unused shadcn/ui components removed)

### Development Server
- **Port**: 5173 (default, configurable via VITE_DEV_SERVER_PORT)
- **Host**: 127.0.0.1 (default, configurable via VITE_DEV_SERVER_HOST)
- **API Proxy**: `/api` routes proxied to backend (configurable via VITE_API_URL)
- **Hot Module Replacement**: Enabled for rapid development iteration

### TypeScript Configuration
- **Target**: ES2020
- **Module**: ESNext
- **Strict Mode**: Enabled (all strict checks active)
- **JSX**: React 17+ (new JSX transform)
- **Path Aliases**: `@` → `./src`

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
