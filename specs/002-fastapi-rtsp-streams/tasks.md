# Tasks: FastAPI RTSP Streams and Landing UI

Feature directory: `specs/002-fastapi-rtsp-streams`

This execution plan is organized by phases with strict, LLM-executable tasks. Tasks are grouped by user story phases after foundational setup. Tests are optional per spec; not included unless requested later.

Notes
- Prerequisite script not present; proceeding with FEATURE_DIR=`specs/002-fastapi-rtsp-streams` based on repository context.
- Tech stack: Python 3.12, FastAPI, Uvicorn, Jinja2, Pydantic v2, PyYAML, opencv-python-headless, Starlette, python-multipart.
- Persistence: `config/config.yml` only, atomic writes.

---

## Phase 1: Setup

- [X] T001 Update dependencies for FastAPI stack in `requirements.txt` (add fastapi, uvicorn, starlette, pydantic>=2, opencv-python-headless, python-multipart; keep prometheus-client; remove Flask; if keeping Gunicorn, use uvicorn.workers.UvicornWorker)
- [X] T002 Create FastAPI ASGI app skeleton in `src/app/wsgi.py` (instantiate FastAPI app; placeholder routers; WSGI Flask removed)
- [X] T003 Create API package init `src/app/api/__init__.py`
- [X] T004 Create REST router for health `src/app/api/health.py`
- [X] T005 Create REST router for streams `src/app/api/streams.py`
- [X] T006 Create UI views module for templates `src/app/ui/views.py`
- [X] T007 Create Stream domain model `src/app/models/stream.py`
- [X] T008 Create streams service module `src/app/services/streams_service.py`
- [X] T009 Create RTSP utilities (playback generator helpers) `src/app/utils/rtsp.py`
- [X] T010 Create API error schema/types `src/app/api/errors.py`
- [X] T011 Initialize config file with empty list if missing `config/config.yml`
- [X] T012 [P] Create base layout template with header container `src/app/templates/base.html`
- [X] T013 [P] Update styles for header animation and equal-width grid `src/app/static/styles.css`
- [X] T014 [P] Add client JS for animations, reorder, delete confirm `src/app/static/app.js`
- [X] T015 Update JSON logging wiring for FastAPI requests `src/app/logging_config.py` (one-line JSON: time, level, msg, request_id, method, path, status, duration_ms, client_ip, user_agent)
- [X] T016 Configure ASGI startup (host/port via `APP_PORT`, default 8000) in `Dockerfile` (bind 0.0.0.0:APP_PORT; log effective port)

## Phase 2: Foundational

- [ ] T017 Implement YAML read/write with atomic rename in `src/app/config_io.py`
- [ ] T018 Implement standardized error responses in `src/app/api/errors.py`
- [ ] T019 Add lightweight rate limiting middleware `src/app/middleware/rate_limit.py`
- [ ] T020 Wire FastAPI app with routers/middleware in `src/app/wsgi.py` (mount `api/streams`, `api/health`, and UI views; add rate-limit, logging, request-id, and error handlers)
- [ ] T021 Implement health endpoint handler in `src/app/api/health.py` (return `{ "status": "ok" }`; used by container HEALTHCHECK)
- [ ] T022 Mount static files and Jinja2 templates in `src/app/wsgi.py`
- [ ] T023 Remove legacy Flask routes file `src/app/routes.py`
- [ ] T024 Scaffold landing template (FastAPI version) `src/app/templates/index.html` (basic layout blocks; no grid/animations yet)
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
- [ ] T034 [P] [US1] Finalize landing template with centered header, equal-width grid scaffolding `src/app/templates/index.html`
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
- [ ] T055 [P] Respect `APP_PORT` in startup and compose `docker-compose.yml` (default 8000; parameterize port mapping)
- [ ] T056 [P] Ensure JSON logging for requests/errors is consistent `src/app/logging_config.py` (fields: time, level, msg, request_id, method, path, status, duration_ms)
- [ ] T057 [P] Update Quickstart/README for new run instructions `README.md`

### Observability, Reliability, and Compliance (Constitution)

- [ ] T058 [P] Expose Prometheus metrics endpoint at `/metrics` in `src/app/wsgi.py`
- [ ] T059 [P] Implement metrics (fps gauge, playback frame counter, request latency histogram, create/delete/reorder counters) in `src/app/metrics.py`
- [ ] T060 Add `entrypoint.sh` to emit versions (Python, FastAPI, Uvicorn, OpenCV); honor `CI_DRY_RUN=true`; start server
- [ ] T061 Update `Dockerfile` to use `entrypoint.sh` and ASGI server (Uvicorn or Gunicorn with `uvicorn.workers.UvicornWorker`); keep HEALTHCHECK `/health`
- [ ] T062 [P] Update `docker-compose.yml` (rename image/container, set `platform: linux/amd64`, mount `./config:/app/config`, expose `${APP_PORT:-8000}`)
- [ ] T063 [P] Persist runtime playback failures: on generator error set `status=Inactive` and atomic-write YAML in `src/app/utils/rtsp.py`
- [ ] T064 [P] Implement CSRF protection for HTML form POSTs in `src/app/ui/views.py` and templates (cookie token + hidden input validation)
- [ ] T065 [P] Add graceful shutdown/watchdog with exponential backoff for RTSP reconnects in `src/app/utils/rtsp.py`
- [ ] T066 [P] Add tests: YAML IO, validation, credential masking, `/health`, `/metrics`, `CI_DRY_RUN` startup in `tests/`
- [ ] T067 [P] Create `artifacts/versions.md` and `artifacts/decisions.md` documenting FastAPI/ASGI and metrics exposure
- [ ] T068 [P] Add `Makefile` with buildx (linux/amd64) build/run/test/push targets honoring `APP_PORT` and `CI_DRY_RUN`
- [ ] T069 [P] Redact credentials from any log lines containing `rtsp_url` in `src/app/logging_config.py`
- [ ] T070 [P] Add request ID middleware and propagate to logs and error responses in `src/app/wsgi.py`
- [ ] T071 [P] Update README with LAN-only posture, WAN warning, metrics endpoint, entrypoint behavior, and `APP_PORT`
- [ ] T072 [P] Implement accessibility specifics: focus outlines, dialog focus trap/return, ARIA live announcements for reorder, keyboard bindings in `src/app/templates/` and `src/app/static/app.js`

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
- Total tasks: 72
- Tasks per user story: US1=13, US2=9, US3=3
- Parallel opportunities identified: 35 tasks marked [P]
- Independent test criteria: Included per story phases above
- Suggested MVP scope: User Story 1 (US1)
