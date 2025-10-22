# ProxiMeter Quick Start Guide

## Run with Docker (Recommended)

```bash
# From repo root
docker compose up --build
```

Open http://localhost:8000 in your browser.

## Run Locally (Development)

### Terminal 1: Start Backend

**With Docker:**
```bash
docker compose up
```

**With Python:**
```bash
# Requires: Python 3.12+, FFmpeg, pip packages from requirements.txt
cd backend
pip install -r requirements.txt
python -m uvicorn src.app.main:app --reload --host 0.0.0.0 --port 8000
```

### Terminal 2: Start Frontend Dev Server

```bash
cd frontend
npm install  # First time only
npm run dev
```

Open http://localhost:5173 in your browser.

## Add Your First Stream

1. Click **"Add Stream"** button
2. Enter stream name (e.g., "Front Door Camera")
3. Enter RTSP URL (e.g., `rtsp://username:password@192.168.1.100:554/stream`)
4. Click **"Add Stream"**
5. Click **"Play"** to view live stream

## Check Backend Health

```bash
curl http://localhost:8000/health
# Expected: {"status":"ok"}
```

## Stop Running Services

```bash
# If using Docker
docker compose down

# If running locally, Ctrl+C in each terminal
```

## Troubleshooting

### "Cannot fetch streams" Error

**Solution**: Make sure backend is running
```bash
# Check if backend is accessible
curl http://localhost:8000/health

# If not, start backend (Docker)
docker compose up
```

### Frontend won't connect to backend

**Solution**: Check environment variables in `frontend/.env.development`
```env
VITE_API_URL=http://localhost:8000
```

Restart frontend dev server after changes.

### Port Already in Use

```bash
# Use different port (example: 8080 for backend)
APP_PORT=8080 docker compose up

# Or kill existing process
lsof -ti:8000 | xargs kill -9  # macOS/Linux
Get-Process -Id (Get-NetTCPConnection -LocalPort 8000).OwningProcess | Stop-Process  # Windows
```

## Useful Commands

```bash
# View backend logs
docker compose logs -f

# Stop and remove volumes
docker compose down -v

# Production build
cd frontend && npm run build

# Run linter
cd frontend && npm run lint

# Run tests
cd frontend && npm run test
```

## Next Steps

- Read [DEVELOPMENT.md](DEVELOPMENT.md) for detailed development guide
- Read [frontend/README.md](frontend/README.md) for frontend-specific docs
- Check [specs/003-frontend-react-migration/](specs/003-frontend-react-migration/) for feature specifications
