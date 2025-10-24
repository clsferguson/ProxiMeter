# ProxiMeter — RTSP Object Detection Scoring for Home Automation

A FastAPI + React TypeScript application for real-time object detection scoring on RTSP camera streams. Create polygon zones, define scoring criteria (distance, coordinates, size), and stream scores to home automation systems via SSE or MQTT. NOT a video recorder or NVR.

- **Backend**: Python 3.12, FastAPI, Uvicorn, Pydantic v2, PyYAML, FFmpeg (RTSP processing), Shapely (polygon geometry)
- **Frontend**: React 19.2, TypeScript 5+, Vite, Tailwind CSS, shadcn/ui component system (optional animation: framer-motion, react-bits, aceternity UI, motion-bits)
- **Features**: 
  - RTSP stream management (add/edit/delete)
  - Polygon zone editor with visual overlays on live stream preview
  - Real-time object detection scoring: distance from target, camera coordinates, bounding box size
  - SSE score streaming (mandatory) + optional MQTT publishing
  - NO video recording or storage (live frames only for inference)
- **Endpoints**: `/` (React SPA), `/api/streams` (REST), `/api/zones` (REST), `/api/scores/stream` (SSE), `/health`, `/metrics`
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

### FFmpeg Configuration

ProxiMeter uses FFmpeg for RTSP stream processing with hardware acceleration support.

**GPU Acceleration**:
- **NVIDIA**: Requires NVIDIA drivers + CUDA. Docker: `--gpus all`. Env: `GPU_BACKEND=nvidia`.
- **AMD**: Requires ROCm. Env: `GPU_BACKEND=amd`.
- **Intel**: Requires oneAPI. Env: `GPU_BACKEND=intel`.
- Detection: `entrypoint.sh` sets `GPU_BACKEND_DETECTED` (nvidia/amd/intel/none).

**Custom FFmpeg Params**:
- In UI: Textarea for flags (e.g., `-rtsp_transport tcp -timeout 10000000`).
- Defaults: `-hide_banner -loglevel warning -threads 2 -rtsp_transport tcp -timeout 10000000` + GPU flags.
- Validation: Whitelists safe flags; rejects shell metachars (`; & | > <`); probes with `ffprobe` on save.

**Troubleshooting FFmpeg**:
- Logs: Check container logs for FFmpeg stderr (`docker logs proximeter`).
- Test: `docker exec -it proximeter ffmpeg -version`.
- GPU: `docker exec -it proximeter nvidia-smi` (NVIDIA).

### Custom Port

If port 8000 is in use, set the `APP_PORT` environment variable:

```bash
APP_PORT=8080 docker compose up --build
```

Or edit `docker-compose.yml` and change the ports mapping.

### Frontend Development Workflow

Use the Vite development server for rapid UI iteration. The frontend uses Tailwind CSS and the shadcn/ui component library.

```bash
cd frontend
npm install
npx shadcn@latest init # idempotent: ensures shadcn config is up to date
npm run dev
```

The dev server runs on `http://localhost:5173` and proxies API calls to the backend (configured in `vite.config.ts`).

#### Tailwind CSS & shadcn/ui Guidelines

**Design Tokens**:
- Tailwind tokens are defined in `tailwind.config.ts`; extend this file instead of writing ad-hoc CSS.
- Use Tailwind utilities for spacing, colors, typography, and responsive breakpoints.
- Breakpoints: `sm` (640px), `md` (768px), `lg` (1024px), `xl` (1280px), `2xl` (1536px).
- Minimum touch target size: `44x44px` (use `h-11 w-11` or equivalent Tailwind spacing).

**Component Architecture**:
- UI primitives live under `src/components/ui/` and are generated via `npx shadcn@latest add <component>`.
- Custom components SHOULD compose shadcn/ui exports and utilities such as `cn` for class merging.
- Use `class-variance-authority` (CVA) for component variants; see shadcn/ui examples.
- Global theming (light/dark) is managed through the `ThemeProvider` established in `main.tsx`.

**Adding New Components**:
```bash
cd frontend
npx shadcn@latest add button  # Adds Button component to src/components/ui/button.tsx
npx shadcn@latest add card    # Adds Card component
npx shadcn@latest add dialog  # Adds Dialog component
```

**Component Documentation**:
- Document prop types and shadcn/ui primitives used in JSDoc comments.
- Example:
  ```typescript
  /**
   * StreamCard - Displays a single RTSP stream with status and actions.
   * Composes shadcn/ui Card, Badge, Button, and DropdownMenu primitives.
   * @param stream - Stream object with id, name, url, status
   * @param onEdit - Callback when edit button is clicked
   * @param onDelete - Callback when delete button is clicked
   */
  export function StreamCard({ stream, onEdit, onDelete }: StreamCardProps) {
    // ...
  }
  ```

#### TypeScript & Code Quality

- **Strict Mode**: TypeScript strict mode is enabled in `tsconfig.json`. All types must be explicit.
- **Linting**: ESLint with Tailwind CSS and accessibility plugins. Run `npm run lint` to check.
- **Formatting**: Prettier is configured. Run `npm run format` to auto-format code.
- **Testing**: Vitest + React Testing Library. Run `npm run test` to execute tests.

#### Build & Optimization

- **Production Build**: `npm run build` creates an optimized bundle in `dist/`.
- **Bundle Size**: Target <500KB gzipped. Tree-shake unused shadcn/ui components by importing only what you use.
- **Environment Variables**: Frontend uses hardcoded API base URL `/api` (relative path). No build-time configuration needed.

#### Common Tasks

```bash
cd frontend

# Development
npm run dev              # Start Vite dev server (http://localhost:5173)
npm run build           # Build production bundle
npm run preview         # Preview production build locally

# Code Quality
npm run lint            # Run ESLint
npm run format          # Format code with Prettier
npm run test            # Run Vitest tests
npm run test:ui         # Run tests with UI

# shadcn/ui
npx shadcn@latest add <component>  # Add a new component
npx shadcn@latest list             # List available components
```

## Project Structure

```
backend/
  src/app/
    main.py                    # FastAPI ASGI application entry point
    config_io.py               # YAML persistence (atomic writes)
    logging_config.py          # JSON logging configuration
    metrics.py                 # Prometheus metrics
    api/
      health.py                # Health endpoint
      streams.py               # REST API for streams + playback
      errors.py                # Error schemas and handlers
    models/
      stream.py                # Pydantic models (Stream, NewStream, EditStream)
    services/
      streams_service.py       # Business logic for stream management
    utils/
      rtsp.py                  # FFmpeg-based RTSP/MJPEG playback utilities
      validation.py            # RTSP URL validation with FFmpeg probe
      strings.py               # Credential masking helpers
    middleware/
      rate_limit.py            # Rate limiting middleware
      request_id.py            # Request ID middleware
  tests/                       # Backend tests

frontend/
  src/
    components/                # React components
    pages/                     # Page components (landing, add, edit, play)
    hooks/                     # Custom React hooks
    services/                  # API client services
    lib/                       # Utility functions
  tests/                       # Frontend tests
  package.json
  tsconfig.json
  vite.config.ts
  index.html

config/
  config.yml                   # Stream persistence (mounted volume)
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

- **Design system**: shadcn/ui primitives on Tailwind CSS ensure consistent spacing, typography, and theming.
- **Header animation**: Centered on landing, animates to top-left on playback (400-700ms)
- **Equal-width buttons**: Stream buttons in responsive grid (same width per row)
- **Mobile-friendly**: Responsive layout
- **Accessibility**: Keyboard navigation, ARIA labels, focus management baked into shadcn/ui components

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
