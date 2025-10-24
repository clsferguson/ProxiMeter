# Tasks: Hardware Accelerated FFmpeg RTSP Processing

**Feature**: 004-hw-ffmpeg-rtsp-processing  
**Branch**: 004-hw-ffmpeg-rtsp-processing  
**Date**: October 23, 2025  
**Source**: Generated from spec.md, plan.md, data-model.md, research.md, quickstart.md, contracts/openapi.yaml  

## Overview

This tasks.md outlines the implementation phases for enabling hardware-accelerated FFmpeg processing for RTSP streams. Tasks are organized by phase, with user stories treated as independent, testable increments. Each phase delivers value incrementally.

**Tech Stack** (from plan.md): Python 3.12, FastAPI, Uvicorn, FFmpeg, opencv-python-headless, Shapely, Pydantic v2 (backend); React 19.2, TypeScript 5+, Vite, Tailwind CSS, shadcn/ui (frontend).  

**User Stories** (from spec.md, prioritized):  
- **US1 (P1)**: Configure and View Accelerated Stream – Core RTSP consumption with hardware accel, MJPEG output.  
- **US2 (P2)**: Monitor Stream Performance – Frontend viewing with real-time scores and metrics.  

**Key Entities** (from data-model.md): Stream (with hw_accel_enabled, ffmpeg_params, target_fps), Zone, Point.  

**Contracts** (from openapi.yaml): /streams CRUD, /streams/{id}/start/stop/mjpeg, /streams/{id}/zones CRUD, /health, /metrics, /streams/{id}/scores (SSE). Endpoints map to US1 (streams/mjpeg) and US2 (scores/metrics).  

**Decisions** (from research.md): Dynamic FFmpeg command building with GPU detection via env var; validation via ffprobe; MJPEG via multipart/x-mixed-replace; UI textarea for params with defaults.  

**MVP Scope**: Complete US1 for basic accelerated stream config and viewing; US2 extends to monitoring.  

## Phases

### Phase 1: Setup (Project Initialization)
Initialize or update project structure, dependencies, and config for FFmpeg integration. No user stories.

- [X] T001 Update requirements.txt to ensure FFmpeg and opencv-python-headless are included in src/requirements.txt
- [X] T002 [P] Update entrypoint.sh to detect GPU backend and set GPU_BACKEND_DETECTED env var (nvidia/amd/intel) in entrypoint.sh
- [X] T003 Update docker-compose.yml to support GPU profiles (--gpus all for NVIDIA) in docker-compose.yml
- [X] T004 Create utils/rtsp.py for FFmpeg command builder in src/app/utils/rtsp.py

### Phase 2: Foundational (Blocking Prerequisites)
Implement core models, services, and middleware shared across stories. No user stories.

- [X] T005 Update Stream Pydantic model to add hw_accel_enabled, ffmpeg_params (list[str]), target_fps (int, default 5) fields with validation in src/app/models/stream.py
- [X] T006 [P] Implement FFmpeg subprocess management in streams_service.py (start/stop, pipe to OpenCV, 5 FPS cap; fail-fast if GPU unavailable per detected backend) in src/app/services/streams_service.py
- [X] T007 Add rate-limiting middleware exemption for /mjpeg and /health endpoints in src/app/middleware/rate_limit.py
- [X] T008 Update config_io.py to load GPU_BACKEND_DETECTED from env and expose to app in src/app/config_io.py

### Phase 3: User Story 1 - Configure and View Accelerated Stream [US1]
As an administrator, configure RTSP stream with hardware accel and view processed MJPEG feed. Independently testable: Add stream via UI, verify MJPEG displays at 5 FPS with low latency.

**Independent Test Criteria**: POST /streams succeeds with valid RTSP URL and params; /streams/{id}/mjpeg returns multipart/x-mixed-replace with JPEG frames; ffprobe validation passes on save; status transitions to 'running'; <200ms latency verifiable via headers.

**Implementation Tasks**:

- [X] T009 [P] [US1] Implement POST /streams with ffprobe validation of URL and constructed FFmpeg params (using GPU flags if detected; reject incompatible flags with 400) in src/app/api/streams.py
- [X] T010 [US1] Add PUT /streams/{id} to update config and re-validate params in src/app/api/streams.py
- [X] T011 [P] [US1] Implement POST /streams/{id}/start to launch FFmpeg subprocess via service, fail-fast with 503 if GPU unavailable, and update status to 'running' in src/app/api/streams.py
- [X] T011.1 [US1] Implement concurrent stream limit (max 4) with locking to prevent race conditions on start, return 409 if over limit in src/app/api/streams.py
- [X] T012 [US1] Implement POST /streams/{id}/stop to terminate subprocess and set status 'stopped' in src/app/api/streams.py
- [X] T013 [P] [US1] Create GET /streams/{id}/mjpeg endpoint for multipart/x-mixed-replace MJPEG output (boundary=--frame, JPEG 640x480 80% quality) from service pipe in src/app/api/streams.py
- [X] T014 [P] [US1] Update StreamForm.tsx to include shadcn/ui Switch for hw_accel_enabled, Textarea for ffmpeg_params (placeholder with defaults + GPU flags fetched from API), Input for target_fps in frontend/src/components/StreamForm.tsx
- [X] T015 [US1] Add API call in useApi.ts to fetch GPU backend for param defaults in frontend/src/hooks/useApi.ts
- [X] T016 [US1] Integrate new StreamForm fields into AddStream.tsx and EditStream.tsx pages in frontend/src/pages/AddStream.tsx and frontend/src/pages/EditStream.tsx
- [X] T016.1 [US1] Update StreamForm.tsx and zone editor to handle normalized coordinates (0-1) for UI consistency in frontend/src/components/StreamForm.tsx

### Phase 4: User Story 2 - Monitor Stream Performance [US2]
As a user, view live processed stream with scores overlaid, ensuring smooth playback and metrics visibility. Builds on US1; independently testable by viewing active stream.

**Independent Test Criteria**: Navigate to stream view; MJPEG loads in <img> without stutter at target FPS; SSE scores update real-time; /metrics shows FPS/latency; switch between streams maintains performance.

**Implementation Tasks**:

- [X] T017 [P] [US2] Update VideoPlayer.tsx to use <img src={`/streams/${streamId}/mjpeg`} /> for MJPEG display in frontend/src/components/VideoPlayer.tsx
- [X] T018 [US2] Enhance StreamCard.tsx to overlay SSE scores (distance, coordinates, size) on video using absolute positioning in frontend/src/components/StreamCard.tsx
- [X] T019 [P] [US2] Implement GET /streams/{id}/scores SSE endpoint to stream JSON scores at 5 FPS (using existing scoring pipeline) in src/app/api/streams.py
- [X] T020 [US2] Update useStreams.ts hook to subscribe to SSE scores and update UI state in frontend/src/hooks/useStreams.ts
- [X] T021 [P] [US2] Add metrics display (FPS, latency) in Dashboard.tsx by fetching /metrics in frontend/src/pages/Dashboard.tsx
- [X] T022 [US2] Update PlayStream.tsx to render VideoPlayer with scores overlay for single stream view in frontend/src/pages/PlayStream.tsx

### Phase 5: Polish & Cross-Cutting Concerns
Integration, error handling, docs, and observability. No user stories.

- [X] T023 Update /health to include stream statuses and accel mode (cuda/software) in src/app/api/health.py
- [X] T024 [P] Implement /metrics Prometheus endpoint with stream_fps, latency, error_rate gauges in src/app/metrics.py
- [X] T025 Add error responses (400/404/503 with JSON {error, code}) to all endpoints per openapi in src/app/api/errors.py
- [X] T026 [P] Update zones endpoints to handle normalized points (0-1) scaling in backend during processing in src/app/api/zones.py
- [X] T027 Enhance logging for FFmpeg stderr and subprocess errors in src/app/logging_config.py
- [X] T028 Update README.md and QUICK_START.md with FFmpeg config instructions in root README.md and QUICK_START.md
- [X] T029 Validate openapi.yaml against implemented endpoints using existing tools

## Dependencies

**User Story Graph**:  
- US1 → US2 (US2 requires active streams from US1 for viewing)  
- Foundational blocks all US (models/services)  
- Setup blocks Foundational (env/config)  
- Polish depends on all (integration)  

Linear order: Phase 1 → 2 → 3 (US1) → 4 (US2) → 5  
No cross-story dependencies beyond foundational.

## Parallel Execution Opportunities

**Per Phase Examples**:  
- **Phase 1**: T002 (entrypoint) and T004 (utils/rtsp.py) independent.  
- **Phase 2**: T006 (service) after T005 (model); T007 (middleware) parallel to T006.  
- **Phase 3 (US1)**: Backend tasks (T009-T013) parallel to frontend UI (T014-T016) after foundational. T011/T012 parallel after T009.  
- **Phase 4 (US2)**: Frontend viewing (T017/T018/T022) parallel to backend SSE/metrics (T019/T021) after US1.  
- **Phase 5**: T023/T024/T029 parallel after all; T025/T026 after APIs; T027/T028 independent.  

**Strategy**: Implement MVP (US1) first: Backend processing + basic UI config. Then US2 for monitoring. Use [P] markers for concurrent dev (e.g., frontend/backend splits).

## Implementation Strategy

**MVP First**: Deliver US1 as core increment – configurable accelerated streams with MJPEG output. Test via UI add/view, ffprobe validation, subprocess logs.  
**Incremental Delivery**: After US1, add US2 for full monitoring. Polish last for robustness.  
**Validation**: Each phase ends with independent tests (e.g., curl /mjpeg for US1; UI playback for US2). Total tasks: 29. Per story: US1 (8), US2 (6). Parallel: 12 opportunities identified. Suggested MVP: Phases 1-3 (US1).

**Format Validation**: All tasks follow checklist: checkbox, ID, [P?], [Story?], description with file path.