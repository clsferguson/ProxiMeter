# ProxiMeter Development Guide

This guide explains how to set up and run ProxiMeter for development and testing.

## Architecture Overview

ProxiMeter is a full-stack application with:
- **Backend**: Python 3.12 FastAPI server running on `http://localhost:8000`
- **Frontend**: React 19.2 TypeScript SPA (Vite dev server on `http://localhost:5173` or production build served from backend)

The frontend communicates with the backend via REST API endpoints under `/api/*`.

## Prerequisites

- Python 3.12+ (for backend)
- Node.js LTS (for frontend)
- FFmpeg (for backend RTSP stream processing)
- Docker (optional, for containerized development)

## Backend Setup

### Option 1: Docker (Recommended)

```bash
# From repo root
docker compose up --build
```

This starts the backend on `http://localhost:8000`.

### Option 2: Local Python Development

```bash
# From repo root
cd backend
python -m pip install -r requirements.txt

# Set environment variables (optional, defaults provided)
# export APP_PORT=8000
# export IMAGE_SIZE=640

# Start the server
python -m uvicorn src.app.main:app --host 0.0.0.0 --port 8000 --reload
```

The backend will be available at `http://localhost:8000`.

### Verify Backend Health

```bash
curl http://localhost:8000/health
# Expected response: {"status":"ok"}
```

## Frontend Development

### Setup

```bash
cd frontend
npm install
```

### Development Server

```bash
npm run dev
```

This starts a Vite dev server on `http://localhost:5173` with:
- Hot module reloading (HMR) for instant updates
- Automatic API proxy to backend (`/api` → `http://localhost:8000`)
- TypeScript type checking in real-time

### Build for Production

```bash
npm run build
npm run preview  # Test production build locally
```

The production build is output to `frontend/dist/` and deployed to the backend's static file server.

## Common Development Workflow

```bash
# Terminal 1: Start backend (Docker)
docker compose up

# Terminal 2: Start frontend dev server
cd frontend && npm run dev

# Terminal 3: Optional - Watch backend logs
docker compose logs -f
```

Open `http://localhost:5173` in your browser. Changes to the frontend code will auto-reload.

## Troubleshooting

### Error: "Unexpected token '<', '<!doctype' is not valid JSON"

This error means the API endpoint is returning HTML (likely an error page) instead of JSON.

**Causes**:
1. Backend is not running
2. Backend is running on wrong port
3. API endpoint path is incorrect
4. VITE_API_URL environment variable is misconfigured

**Solutions**:
1. Verify backend is running:
   ```bash
   curl http://localhost:8000/health
   ```
   
2. Check `VITE_API_URL` in `frontend/.env.development`:
   ```env
   VITE_API_URL=http://localhost:8000
   ```
   
3. Restart frontend dev server after changing environment variables:
   ```bash
   # Kill the dev server (Ctrl+C) and restart
   npm run dev
   ```

### Error: "Network error: Failed to connect to the backend"

**Causes**:
- Backend not running
- Backend running on different port
- CORS issues
- Firewall blocking localhost:8000

**Solutions**:
1. Check backend is running: `curl http://localhost:8000/health`
2. Check port: Backend defaults to 8000, frontend defaults to 5173
3. Verify environment: Check `frontend/.env.development`
4. Check firewall: Try accessing backend directly in browser

### Streams not loading / API calls failing

1. Verify backend `/api/streams` endpoint:
   ```bash
   curl http://localhost:8000/api/streams
   # Should return: []  (or list of streams if any exist)
   ```

2. Check browser console for detailed error messages
3. Check backend logs for server-side errors
4. Verify config file exists: `config/config.yml`

### ESLint or Build Errors

```bash
# Check for linting errors
npm run lint

# Fix fixable errors
npm run lint -- --fix

# Clean install dependencies
rm -rf node_modules package-lock.json
npm install
```

## Environment Variables

### Frontend (`.env.development`)

```env
# Backend API URL - change this if backend is on different machine/port
VITE_API_URL=http://localhost:8000

# Dev server configuration
VITE_DEV_SERVER_HOST=127.0.0.1
VITE_DEV_SERVER_PORT=5173
```

### Backend (`.env` or Docker environment)

- `APP_PORT=8000` - Backend port
- `IMAGE_SIZE=640` - YOLO model input size
- `GPU_BACKEND=cpu` - GPU backend (cpu, cuda, rocm)
- `YOLO_MODEL=yolov8n.pt` - YOLO model
- `MQTT_ENABLED=false` - Enable MQTT publishing
- `MQTT_HOST=localhost`
- `MQTT_PORT=1883`
- `MQTT_TOPIC=proximeter/scores`

## Testing

### Frontend

```bash
# Run unit tests
npm run test

# Run tests in watch mode
npm run test -- --watch

# Generate coverage report
npm run test -- --coverage
```

### Backend

```bash
cd ../
pytest --cov=src tests/
```

## Production Build

```bash
# Build frontend
cd frontend
npm run build

# This outputs static files to dist/
# These are automatically served by the backend when deployed to Docker
```

## Docker Deployment

The included `Dockerfile` and `docker-compose.yml` handle:
1. Building frontend (Node.js build stage)
2. Building backend (Python runtime)
3. Serving frontend static files from backend
4. Mounting config volume for persistence

```bash
# Build and run
docker compose up --build

# Run in background
docker compose up -d

# View logs
docker compose logs -f

# Stop
docker compose down
```

## Next Steps

- [Frontend Development](frontend/README.md)
- [Backend Documentation](specs/002-fastapi-rtsp-streams/)
- [Specification](specs/003-frontend-react-migration/spec.md)
