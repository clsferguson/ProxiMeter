# Implementation Plan: [FEATURE]

**Branch**: `004-hw-ffmpeg-rtsp-processing` | **Date**: October 23, 2025 | **Spec**: [specs/004-hw-ffmpeg-rtsp-processing/spec.md](file:///c:/Save/Code%20Projects/ProxiMeter/specs/004-hw-ffmpeg-rtsp-processing/spec.md)
**Input**: Feature specification from `/specs/[###-feature-name]/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Primary Requirement: Enable hardware-accelerated FFmpeg processing for RTSP streams, with user-configurable FFmpeg parameters integrated with GPU detection.

Technical Approach: Dynamically construct FFmpeg commands in backend using detected GPU backend from entrypoint.sh and user params. Validate on save with ffprobe. Frontend UI uses shadcn/ui Input for params with placeholder defaults. Output MJPEG via HTTP for real-time display and scoring.

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: Python 3.12  
**Primary Dependencies**: FastAPI, Uvicorn, FFmpeg, opencv-python-headless, Shapely, Pydantic v2  
**Storage**: N/A (only config.yml persisted via Docker volume)  
**Testing**: pytest, ruff check  
**Target Platform**: Linux/amd64 in Docker container  
**Project Type**: Web application (FastAPI backend + React 19.2 TypeScript frontend with Vite)  
**Performance Goals**: 5 FPS per stream with hardware-accelerated decoding, low latency (<200ms end-to-end)  
**Constraints**: Real-time processing only, no video storage, GPU backend fail-fast with no fallback (container exit on unavailability), LAN-only deployment  
**Scale/Scope**: Up to 4 concurrent RTSP streams, single YOLO model, polygon zone management per stream

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

✅ Docker-only runtime on linux/amd64; no host execution paths  
✅ Application purpose: object detection scoring for home automation (NOT NVR/recording); no video storage  
✅ Single active YOLO model; multi-RTSP with enforced 5 FPS per stream  
✅ FFmpeg MUST be used for all RTSP stream ingestion, decoding, and frame extraction  
✅ Polygon zone management: per-stream CRUD with visual editor; zones define scoring areas  
✅ Scoring pipeline: calculate distance/coordinates/size for detected objects in zones; real-time only (no storage)  
✅ SSE score streaming is mandatory; MQTT is optional  
✅ Env contract honored: APP_PORT, GPU_BACKEND, YOLO_MODEL, IMAGE_SIZE, MQTT_ENABLED, MQTT_HOST, MQTT_PORT, MQTT_TOPIC  
✅ Persist ONLY /app/config/config.yml via volume; no model caches/artifacts or video storage  
✅ GPU backend provisioning is fail-fast (no fallback) and versions emitted  
✅ Frontend MUST be React 19.2 TypeScript SPA with Vite that composes shadcn/ui components on Tailwind CSS; backend REST API + SSE only (no templates)  
✅ Observability: JSON logs, /health, Prometheus metrics present  
✅ Security: non-root, input validation, rate-limits; file I/O restricted; no authentication (LAN-only; DO NOT expose to WAN)  
✅ CI/build: buildx with --platform=linux/amd64; healthcheck in image; multi-stage build with frontend production bundle  
✅ CI runners: GitHub-hosted CPU-only; pipeline MUST NOT require GPU devices or drivers  
✅ CI dry-run: set CI_DRY_RUN=true to bypass GPU checks while verifying startup and /health  
✅ Tests in CI: CPU-only with synthetic inputs; avoid large model downloads unless cached  
✅ GPU smoke tests: off-CI only (manual or self-hosted GPU runner) and documented runbook  
✅ Tooling evidence: artifacts/versions.md updated (include FFmpeg, React 19.2, TypeScript, Node.js, polygon libs); decisions recorded; entrypoint prints runtime stack versions (including FFmpeg)  

*No violations identified. Proceeding to Phase 0.*

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
<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete layout
  for this feature. Delete unused options and expand the chosen structure with
  real paths (e.g., apps/admin, packages/something). The delivered plan must
  not include Option labels.
-->

```
src/ (backend)
├── app/
│   ├── models/
│   │   └── stream.py
│   ├── services/
│   │   └── streams_service.py  # FFmpeg subprocess management
│   ├── api/
│   │   ├── streams.py  # CRUD with validation
│   │   └── zones.py
│   └── utils/
│       └── rtsp.py  # FFmpeg command builder

frontend/
├── src/
│   ├── components/
│   │   ├── StreamForm.tsx  # UI for FFmpeg params
│   │   └── ui/  # shadcn/ui components
│   ├── pages/
│   │   ├── AddStream.tsx
│   │   └── EditStream.tsx
│   ├── hooks/
│   │   └── useStreams.ts
│   └── services/
│       └── api.ts  # Fetch GPU info for defaults
├── tests/
├── package.json
├── tsconfig.json
├── vite.config.ts
└── index.html

tests/ (backend)
├── unit/
└── integration/
```

**Structure Decision**: Web application structure with FastAPI backend in src/app and React frontend. New files: streams_service.py for FFmpeg integration, StreamForm.tsx for UI params input. Leverage existing models/stream.py for ffmpeg_params field.

## Complexity Tracking

*No violations; all gates passed.*