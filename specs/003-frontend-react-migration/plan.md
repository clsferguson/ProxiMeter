# Implementation Plan: Frontend React Migration

**Branch**: `003-frontend-react-migration` | **Date**: 2025-10-19 | **Spec**: specs/003-frontend-react-migration/spec.md
**Input**: Feature specification from `/specs/003-frontend-react-migration/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Migrate static HTML/CSS/JS frontend to React 19.2 TypeScript SPA with Vite, preserving all existing functionality and UI/UX while implementing modern React component architecture with routing, API integration, and responsive design.

## Technical Context

**Language/Version**: TypeScript 5+, React 19.2, Node.js LTS  
**Primary Dependencies**: React 19.2, TypeScript 5+, Vite, React Router v6, Axios (preferred for interceptors)  
**Storage**: N/A (stateless frontend)  
**Testing**: Vitest with React Testing Library  
**Target Platform**: Modern browsers (Chrome, Firefox, Safari, Edge - latest 2 versions)  
**Project Type**: Web application (React SPA)  
**Performance Goals**: <2s initial dashboard load, <500KB production bundle gzipped, <3s video playback start  
**Constraints**: Strict TypeScript mode, responsive design (768px+ breakpoint, 44x44px touch targets), preserve visual design while modernizing implementation  
**Scale/Scope**: 4 pages (dashboard, add stream, edit stream, play stream), REST API integration (5 endpoints), real-time status updates (every 2s), optional animation libraries

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- Docker-only runtime on linux/amd64; no host execution paths
- Application purpose: object detection scoring for home automation (NOT NVR/recording); no video storage
- Single active YOLO model; multi-RTSP with enforced 5 FPS per stream
- FFmpeg MUST be used for all RTSP stream ingestion, decoding, and frame extraction
- Polygon zone management: per-stream CRUD with visual editor; zones define scoring areas
- Scoring pipeline: calculate distance/coordinates/size for detected objects in zones; real-time only (no storage)
- SSE score streaming is mandatory; MQTT is optional
- Env contract honored: APP_PORT, GPU_BACKEND, YOLO_MODEL, IMAGE_SIZE,
  MQTT_ENABLED, MQTT_HOST, MQTT_PORT, MQTT_TOPIC
- Persist ONLY /app/config/config.yml via volume; no model caches/artifacts or video storage
- GPU backend provisioning is fail-fast (no fallback) and versions emitted
- Frontend MUST be React 19.2 TypeScript SPA with Vite; backend REST API + SSE only (no templates)
- Observability: JSON logs, /health, Prometheus metrics present
- Security: non-root, input validation, rate-limits; file I/O restricted; no authentication (LAN-only; DO NOT expose to WAN)
- CI/build: buildx with --platform=linux/amd64; healthcheck in image; multi-stage build with frontend production bundle
- CI runners: GitHub-hosted CPU-only; pipeline MUST NOT require GPU devices or drivers
- CI dry-run: set CI_DRY_RUN=true to bypass GPU checks while verifying startup and /health
- Tests in CI: CPU-only with synthetic inputs; avoid large model downloads unless cached
- GPU smoke tests: off-CI only (manual or self-hosted GPU runner) and documented runbook
- Tooling evidence: artifacts/versions.md updated (include FFmpeg, React 19.2, TypeScript, Node.js, polygon libs); decisions recorded; entrypoint
  prints runtime stack versions (including FFmpeg)

## API Configuration

**Frontend-Backend Communication**:
- Frontend API base URL is **hardcoded to `/api`** (relative path in `frontend/src/lib/constants.ts`)
- Frontend is served from the backend container on the same port
- No build-time API URL configuration needed (frontend uses relative path)
- API requests are proxied through the backend at `/api/*` endpoints

**Docker Port Configuration**:
- Backend port is configurable via `APP_PORT` environment variable (default: 8000)
- Entrypoint (`entrypoint.sh`) reads `APP_PORT` and starts Uvicorn on that port
- Frontend and backend share the same port (no port conflicts possible)
- Docker Compose example: `APP_PORT=8000` (or any other port)

**Port Conflict Handling**:
- Since frontend is served from backend, both use the same port
- No internal port conflicts possible (frontend at `/`, API at `/api`)
- If user changes `APP_PORT`, both frontend and API automatically use the new port
- Healthcheck uses `${APP_PORT}` environment variable for correct port

## Project Structure

### Documentation (this feature)

```
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```
backend/  # Existing Python FastAPI backend
├── src/
│   ├── models/
│   ├── services/
│   └── api/
└── tests/

frontend/  # New React TypeScript SPA
├── src/
│   ├── components/      # Reusable UI components
│   ├── pages/          # Dashboard, AddStream, EditStream, PlayStream
│   ├── hooks/          # Custom React hooks (useStreams, useApi)
│   ├── services/       # API client (axios instance with interceptors)
│   ├── lib/            # Utilities, types, constants
│   └── App.tsx         # Root component with React Router
├── public/             # Static assets
├── tests/              # Component and integration tests
├── package.json
├── tsconfig.json
├── vite.config.ts
└── index.html
```

**Structure Decision**: Option 1 selected - Web API + Frontend SPA. Backend remains in `src/` (Python FastAPI), new frontend in `frontend/` (React TypeScript). Clean separation with REST API contract (openapi.yaml) as interface between layers.

## Complexity Tracking

*No constitution violations. All requirements align with ProxiMeter architecture:*
- React 19.2 TypeScript SPA ✓
- REST API + SSE only (no templates) ✓  
- Multi-stage build with frontend production bundle ✓
- Preserves existing functionality (stream CRUD + viewing) ✓

## Implementation Phases

### Phase 0: Research & Discovery *(output: research.md)*

**Goals**: Validate feasibility, identify risks, document current state

**Research Tasks**:
1. Review existing static templates (src/templates/*.html) to document current UI structure
2. Analyze current API endpoints (src/app/api/*.py) and verify against openapi.yaml contract
3. Research React 19.2 new features and breaking changes from previous versions
4. Evaluate animation libraries (framer-motion, react-bits, aceternity UI, motion-bits) for optional enhancements
5. Document MJPEG streaming implementation for HTML5 video element integration
6. Identify TypeScript strict mode requirements and potential type safety issues
7. Review Vite build configuration best practices for production optimization

**Risks to Investigate**:
- MJPEG streaming compatibility with React lifecycle and HTML5 video element
- Bundle size targets (<500KB gzipped) with animation libraries
- Real-time status update polling strategy (2-second interval performance)
- Browser compatibility for latest 2 versions (Safari, Firefox, Chrome, Edge)

**Success Criteria**: All research questions answered, risks documented with mitigation strategies

---

### Phase 1: Design & Contracts *(output: data-model.md, quickstart.md, contracts/)*

**Goals**: Define interfaces, data flow, component architecture

**Design Deliverables**:
1. **data-model.md**: TypeScript interfaces for Stream, StreamResponse, ErrorResponse, form state
2. **quickstart.md**: Local development setup, build commands, testing workflow
3. **contracts/openapi.yaml**: Already exists - validate completeness and accuracy

**Component Architecture**:
```
App (Router)
├── Dashboard (GET /streams, status polling)
│   ├── StreamCard (display, edit, delete, play actions)
│   └── EmptyState
├── AddStream (POST /streams)
│   └── StreamForm (validation, error handling)
├── EditStream (PATCH /streams/:id, DELETE /streams/:id)
│   └── StreamForm (reused, pre-populated)
└── PlayStream (GET /streams/play/:id.mjpg)
    ├── VideoPlayer (HTML5 video, error states)
    └── ErrorDisplay
```

**API Service Layer**:
- Axios instance with base URL configuration
- Request/response interceptors for error handling
- Timeout configuration (10 seconds)
- Type-safe methods for each endpoint

**Success Criteria**: All interfaces defined, component tree documented, API service designed

---

### Phase 2: Implementation *(output: tasks.md via /speckit.tasks)*

**Build Order** (detailed tasks generated by `/speckit.tasks`):

1. **Project Setup**
   - Initialize frontend/ directory with Vite + React + TypeScript
   - Configure tsconfig.json (strict mode), vite.config.ts, package.json
   - Install dependencies: react, react-dom, react-router-dom, axios, vitest, @testing-library/react

2. **API Service Layer**
   - Create services/api.ts with axios instance
   - Implement typed methods for all 5 endpoints
   - Add error handling and timeout configuration
   - Write unit tests for API service

3. **Core Components**
   - Implement StreamForm component (shared by Add/Edit)
   - Implement VideoPlayer component with error states
   - Implement StreamCard component with actions
   - Implement EmptyState component

4. **Page Components**
   - Dashboard page with stream list and polling
   - AddStream page with form
   - EditStream page with form (pre-populated)
   - PlayStream page with video player

5. **Routing & Navigation**
   - Configure React Router v6
   - Implement navigation (app bar, back buttons)
   - Handle route parameters (streamId)

6. **Styling & Responsive Design**
   - Port existing CSS from static templates
   - Implement responsive breakpoints (768px+)
   - Ensure touch targets (44x44px minimum)
   - Optional: integrate animation libraries

7. **Testing & Quality**
   - Component tests for all pages
   - Integration tests for API flows
   - E2E tests for critical paths (add, edit, delete, play)
   - TypeScript compilation (zero errors)

8. **Build & Deployment**
   - Configure Vite production build
   - Update Dockerfile multi-stage build
   - Verify bundle size (<500KB gzipped)
   - Update docker-compose.yml

**Success Criteria**: All tests pass, TypeScript compiles, bundle size target met, all user stories functional

---

### Phase 3: Documentation & Handoff

**Deliverables**:
1. Update README.md with frontend development instructions
2. Document component API and props in code comments
3. Update artifacts/versions.md with React 19.2, TypeScript, Node.js, Vite versions
4. Update .github/copilot-instructions.md with frontend tech stack
5. Create migration guide from static templates to React components

**Success Criteria**: Documentation complete, all constitution requirements met