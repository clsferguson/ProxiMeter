# Tasks: FastAPI RTSP Streams and Landing UI

Feature directory: `specs/002-fastapi-rtsp-streams`

This execution plan is organized by phases with strict, LLM-executable tasks. Tasks are grouped by user story phases after foundational setup. Tests are optional per spec; not included unless requested later.

Notes
- Prerequisite script not present; proceeding with FEATURE_DIR=`specs/002-fastapi-rtsp-streams` based on repository context.
- Tech stack: Python 3.12, FastAPI, Uvicorn, Jinja2, Pydantic v2, PyYAML, opencv-python-headless, Starlette, python-multipart.
- Persistence: `config/config.yml` only, atomic writes.

---

## Phase 1: Setup

- [ ] T001 Update dependencies for FastAPI stack in `requirements.txt`
- [ ] T002 Replace Flask app with FastAPI ASGI app in `src/app/wsgi.py`
- [ ] T003 Create API package init `src/app/api/__init__.py`
- [ ] T004 Create REST router for health `src/app/api/health.py`
- [ ] T005 Create REST router for streams `src/app/api/streams.py`
- [ ] T006 Create UI views module for templates `src/app/ui/views.py`
- [ ] T007 Create Stream domain model `src/app/models/stream.py`
- [ ] T008 Create streams service module `src/app/services/streams_service.py`
- [ ] T009 Create RTSP utilities (playback generator helpers) `src/app/utils/rtsp.py`
- [ ] T010 Create API error schema/types `src/app/api/errors.py`
- [ ] T011 Initialize config file with empty list if missing `config/config.yml`
- [ ] T012 [P] Create base layout template with header container `src/app/templates/base.html`
- [ ] T013 [P] Update styles for header animation and equal-width grid `src/app/static/styles.css`
- [ ] T014 [P] Add client JS for animations, reorder, delete confirm `src/app/static/app.js`
- [ ] T015 Update JSON logging wiring for FastAPI requests `src/app/logging_config.py`
- [ ] T016 Configure Uvicorn startup (host/port from APP_PORT) in `Dockerfile`

## Phase 2: Foundational

- [ ] T017 Implement YAML read/write with atomic rename in `src/app/config_io.py`
- [ ] T018 Implement standardized error responses in `src/app/api/errors.py`
- [ ] T019 Add lightweight rate limiting middleware `src/app/middleware/rate_limit.py`
- [ ] T020 Wire FastAPI app with routers/middleware in `src/app/wsgi.py`
- [ ] T021 Implement health endpoint handler in `src/app/api/health.py`
- [ ] T022 Mount static files and Jinja2 templates in `src/app/wsgi.py`
- [ ] T023 Remove legacy Flask routes file `src/app/routes.py`
- [ ] T024 Replace landing template with FastAPI version `src/app/templates/index.html`
- [ ] T025 [P] Add credential masking helper for rtsp_url `src/app/utils/strings.py`
- [ ] T026 [P] Add RTSP URL validation utilities `src/app/utils/validation.py`

## Phase 3: User Story 1 – Add and View a Stream (P1)

Goal: Add a stream (Name + RTSP URL), navigate to playback capped at ≤5 FPS, header animates to top-left.

- [ ] T027 [US1] Define Pydantic models (Stream, NewStream, EditStream) `src/app/models/stream.py`
- [ ] T028 [P] [US1] Implement create stream service with validation + 2s probe `src/app/services/streams_service.py`
- [ ] T029 [P] [US1] Implement `POST /api/streams` route `src/app/api/streams.py`
- [ ] T030 [US1] Implement MJPEG frame generator (≤5 FPS, no audio) `src/app/utils/rtsp.py`
- [ ] T031 [US1] Implement `GET /play/{id}.mjpg` playback route `src/app/api/streams.py`
- [ ] T032 [US1] Implement landing route GET `/` with Add button `src/app/ui/views.py`
- [ ] T033 [US1] Implement Add form routes GET `/streams/new` and POST submit `src/app/ui/views.py`
- [ ] T034 [P] [US1] Rewrite landing template with centered header `src/app/templates/index.html`
- [ ] T035 [P] [US1] Add Add Stream form template `src/app/templates/add_stream.html`
- [ ] T036 [P] [US1] Add playback template with error banner/back link `src/app/templates/play.html`
- [ ] T037 [US1] Wire header animation class toggle on route change `src/app/static/app.js`
- [ ] T038 [US1] Mask rtsp_url in API responses; add Cache-Control headers `src/app/api/streams.py`
- [ ] T039 [US1] Keep metrics stub for playback/creates `src/app/metrics.py`

Independent test criteria
- Add valid RTSP stream; playback starts within 3s (p95) at ≤5 FPS; header animates to top-left; Back returns to landing.

## Phase 4: User Story 2 – Manage Streams on Landing (P2)

Goal: List saved streams as equal-width buttons; reorder via drag handle; delete with confirm; edit stream; header animates back on return.

- [ ] T040 [US2] Implement `GET /api/streams` list with masked URLs `src/app/api/streams.py`
- [ ] T041 [P] [US2] Implement `DELETE /api/streams/{id}` with renumber `src/app/api/streams.py`
- [ ] T042 [P] [US2] Implement `PATCH /api/streams/{id}` partial edit `src/app/api/streams.py`
- [ ] T043 [P] [US2] Implement `POST /api/streams/reorder` idempotent `src/app/api/streams.py`
- [ ] T044 [US2] Render list grid with equal-width buttons + actions `src/app/templates/index.html`
- [ ] T045 [P] [US2] Add delete confirmation modal behavior `src/app/static/app.js`
- [ ] T046 [P] [US2] Add drag-and-drop reorder and POST to API `src/app/static/app.js`
- [ ] T047 [P] [US2] Add Edit Stream form + routes `src/app/templates/edit_stream.html`
- [ ] T048 [US2] Animate header back on landing return `src/app/static/app.js`

Independent test criteria
- With multiple streams, drag to reorder persists across reloads; Delete requires confirm and updates immediately; equal-width layout within ±2px.

## Phase 5: User Story 3 – Remove Legacy Counter & Update Header (P3)

Goal: Legacy counter removed; only Add stream primary action; header says “ProxiMeter” with animations.

- [ ] T049 [US3] Ensure counter routes return 404 or redirect; remove Flask references `src/app/wsgi.py`
- [ ] T050 [P] [US3] Remove counter UI/assets from templates/static `src/app/templates/`
- [ ] T051 [US3] Update product docs with new flows and warnings `README.md`

Independent test criteria
- No counter routes or UI; header text is “ProxiMeter”; desktop/mobile render correctly.

## Final Phase: Polish & Cross-Cutting

- [ ] T052 Update OpenAPI docs with error schema and examples `specs/002-fastapi-rtsp-streams/contracts/openapi.yaml`
- [ ] T053 [P] Add ARIA/keyboard reordering and focus management `src/app/templates/index.html`
- [ ] T054 [P] Add container HEALTHCHECK for `/health` `Dockerfile`
- [ ] T055 [P] Respect `APP_PORT` in startup and compose `docker-compose.yml`
- [ ] T056 [P] Ensure JSON logging for requests/errors is consistent `src/app/logging_config.py`
- [ ] T057 [P] Update Quickstart/README for new run instructions `README.md`

---

## Dependencies and Story Order

Story order: US1 → US2 → US3

Blocking prerequisites
- Complete Phase 1 (T001–T016) before any story work.
- Complete Phase 2 (T017–T026) before US1 endpoints/UI.

Key dependencies
- T028 depends on T017, T026.
- T029 depends on T027–T028, T018.
- T031 depends on T030 and data from T028.
- T044 depends on T040–T043.
- US3 depends on US1 removal/migration tasks in T002, T023–T024.

## Parallel Execution Examples

US1 parallelizable tasks
- T028, T029, T034, T035, T036 can proceed in parallel after T017–T027.

US2 parallelizable tasks
- T041, T042, T043, T045, T046, T047 can proceed in parallel after T040.

Polish parallelizable tasks
- T053–T057 can proceed in parallel after respective feature completion.

## Implementation Strategy (MVP-first)

1) MVP: Complete US1 end-to-end (create + playback + minimal landing + back button + header animation). Ensure ≤5 FPS and masked URLs.
2) Add US2 management (list, delete confirm, reorder, edit) with equal-width grid and basic a11y.
3) Remove legacy counter (US3); update docs and polish; finalize OpenAPI examples.

---

## Format Validation

All tasks follow required checklist format: “- [ ] T### [P] [US#] Description with file path”. Setup/Foundational/Polish phases omit story labels by rule. Parallelizable tasks include [P]. File paths are explicit.

---

## Report

Generated file: `specs/002-fastapi-rtsp-streams/tasks.md`

Summary
- Total tasks: 57
- Tasks per user story: US1=13, US2=9, US3=3
- Parallel opportunities identified: 22 tasks marked [P]
- Independent test criteria: Included per story phases above
- Suggested MVP scope: User Story 1 (US1)
