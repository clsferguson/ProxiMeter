# ProxiMeter Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-10-21

## Application Purpose
Object detection scoring for home automation (NOT NVR/recording). Real-time scoring only; no video storage.

## Active Technologies
- TypeScript 5+, React 19.2, Node.js LTS + Vite, Tailwind CSS, shadcn/ui, React Router, Axios/fetch (003-frontend-react-migration)
- N/A (stateless frontend) (003-frontend-react-migration)

### Backend (Mandatory)
- Python 3.12 (container base: python:3.12-slim-trixie)
- FastAPI, Uvicorn (ASGI server), Pydantic v2, PyYAML
- FFmpeg (mandatory for RTSP stream processing)
- Shapely (polygon geometry for point-in-polygon checks)
- opencv-python-headless, starlette, python-multipart

### Frontend (Mandatory)
- React 19.2, TypeScript 5+, Vite (bundler)
- Tailwind CSS with shadcn/ui component system (Radix UI primitives)
- Node.js LTS (build stage)

### Frontend Animation (Optional)
- framer-motion, react-bits, aceternity UI, motion-bits

## Project Structure
```
backend/
  src/app/
  tests/
frontend/
  src/
    components/
    pages/
    hooks/
    services/
    lib/
  tests/
  package.json
  tsconfig.json
  vite.config.ts
config/
```

## Commands

### Backend
```bash
cd backend; pytest; ruff check src/
```

### Frontend
```bash
cd frontend; npm run build; npm run test; npm run lint
```

### Development
```bash
# Backend: see Makefile targets
# Frontend dev server: cd frontend; npm run dev
```

## Code Style

### Backend
- Python 3.12: Follow PEP8, use ruff/black, mypy strict mode
- FastAPI: REST API + SSE only, no server-rendered templates
- FFmpeg: Use for all RTSP ingestion and decoding
- Polygon zones: Use Shapely for point-in-polygon checks
- Scoring: Calculate distance (from target point), coordinates (normalized), size (bounding box)
- NO video storage: Live frames only for inference; no recording, no history

### Frontend
- TypeScript: Strict mode enabled
- React 19.2: Functional components with hooks
- Tailwind CSS + shadcn/ui: All UI MUST compose shadcn/ui primitives and shared Tailwind tokens; customize via `class-variance-authority` utilities
- Polygon editor: Canvas overlay on live stream with draggable points using shadcn/ui layout primitives for panels/tooling
- ESLint + Prettier for formatting (include tailwindcss and accessibility plugins)
- Use `npx shadcn@latest add` for generating new UI components; do not hand-roll base components outside `/components/ui`

## Recent Changes
- 003-frontend-react-migration: Frontend now mandates Tailwind CSS + shadcn/ui with strict TypeScript and Vite dev server
- 2025-10-21: Constitution v2.4.0 - Added Principle VIII enforcing shadcn/ui adoption; updated plan/spec/tasks templates and documentation accordingly
- 2025-10-19: Constitution v2.3.0 - Clarified application purpose (object detection scoring for home automation, NOT NVR); added polygon zone management and scoring pipeline (distance/coordinates/size); made SSE mandatory, MQTT optional; updated React to 19.2
- 2025-10-19: Constitution v2.2.0 - Added mandatory FFmpeg for RTSP processing; migrated to React TypeScript SPA with Vite; removed Jinja2 templates; backend now REST API only

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
