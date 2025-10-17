# Implementation Plan: FastAPI RTSP Streams and Landing UI

Branch: `002-fastapi-rtsp-streams` | Date: 2025-10-17 | Spec: `C:\Save\Code Projects\ProxiMeter\specs\002-fastapi-rtsp-streams\spec.md`
Input: Feature specification from `/specs/002-fastapi-rtsp-streams/spec.md`

Note: Generated via speckit plan workflow. Stops after Phase 2 planning per instructions.

## Summary

Replace legacy Flask counter with a FastAPI app providing:
- Landing page with "Add stream" and equal-width buttons for saved RTSP streams.
- Add/Edit/Delete/Reorder streams persisted to `config/config.yml` (ordered list).
- Stream playback view rendering RTSP at ≤5 FPS, no audio, with header animation.

Technical approach (from research): FastAPI + Uvicorn (ASGI). RTSP decoding via OpenCV/FFmpeg on the server, throttled to ≤5 FPS, streamed to browser as MJPEG over HTTP (multipart/x-mixed-replace). Configuration stored in YAML; validation with Pydantic. Drag-and-drop ordering persisted via `order` field. Health endpoint and JSON logging maintained to satisfy constitution.

## Technical Context

**Language/Version**: Python 3.12 (container base: python:3.12-slim-trixie)
**Primary Dependencies**: FastAPI, Uvicorn, Jinja2, Pydantic v2, PyYAML, opencv-python-headless, starlette, python-multipart (forms)
**Storage**: YAML file at `/app/config/config.yml` mounted as a volume (ordered list of streams)
**Testing**: pytest for unit/integration; synthetic RTSP inputs (e.g., sample files/streams) in CI
**Target Platform**: Docker-only, linux/amd64, ASGI server (Uvicorn)
**Project Type**: Single web application (server-rendered templates + REST endpoints)
**Performance Goals**: ≤5 FPS visible updates per stream; p95 add-to-first-frame ≤3s; landing list update ≤1s
**Constraints**: LAN-only; no auth; JSON logging; health + metrics endpoints; non-root container; file I/O restricted to config.yml
**Scale/Scope**: Dozens to ~100 streams listed; playback 1 active stream per UI session; multi-stream decode capacity depends on future model work (out of scope here)

Unknowns resolved in Phase 0 research:
- Browser playback transport: MJPEG over HTTP vs. HLS/WebRTC → DECIDED (see research.md)
- RTSP validation method and connectivity probe → DECIDED
- Reorder persistence API shape → DECIDED

## Scenario Coverage and API Contract Details

This plan incorporates additional scenarios clarified in the spec (FR-018..FR-026) and non-functional requirements (NFR-001..NFR-002).

Planned API/behavior details
- Playback endpoint (FR-023): Serve multipart MJPEG with `Content-Type: multipart/x-mixed-replace; boundary=frame`; each part has `Content-Type: image/jpeg`. Add `Cache-Control: no-store`. Throttle server-side to ≤5 FPS (time-gated yields). On error/stop, end stream gracefully.
- Unreachable RTSP (FR-022): On create/edit, validate format; probe a frame (2s timeout). If probe fails, persist with `status=Inactive`; include advisory in response `details`. UI banner handled by templates; API stays consistent.
- Runtime failures (FR-018): If generator detects failure mid-playback, close stream and set `status=Inactive` persisted to YAML; landing reflects state on next fetch.
- Edit semantics (FR-024): Use `PATCH /api/streams/{id}`; accept partial `name`, `rtsp_url`. Validation order: normalize input (trim, CI compare) → validate formats/uniqueness → optional probe → persist → return updated resource.
- Reorder semantics (FR-019): Endpoint `POST /api/streams/reorder` with body `{ order: [uuid, ...] }`; idempotent; if identical order or ≤1 streams, no-op and 200. Reject missing/duplicate IDs with error.
- Error schema (FR-020): Standard JSON `{ code: string, message: string, details?: object }` with domain codes: `INVALID_RTSP_URL`, `DUPLICATE_NAME`, `INVALID_ORDER`, `NOT_FOUND`.
- Health (FR-021): `GET /health` returns 200 and `{ status: "ok" }`.
- Credentials masking (FR-026): When returning stream objects, mask credentials in `rtsp_url` (e.g., `rtsp://***:***@host/...`). Persist plaintext in YAML as per security posture.
- Examples (FR-025): Provide example requests/responses (success and error) for List, Create, Edit, Delete, Reorder, Playback in the OpenAPI document.

Non-functional implementation
- Rate limiting (NFR-001): Apply lightweight per-client limits to mutating routes (e.g., 5 rps, burst 10) using a middleware.
- YAML atomic writes (NFR-002): Write updates to a temp file and atomic rename; normalize `order` field and ensure contiguous ordering.

OpenAPI/Contracts updates required
- Define standard error schema and reference it across responses.
- Specify health response body `{ status: "ok" }`.
- Document playback endpoint headers/boundary and behavior.
- Clarify PATCH schema and examples; add request/response examples across endpoints.
- Document reorder constraints (no-op conditions, invalid order errors).
- Note credential masking in response examples.

## Constitution Check (Pre-Design Gate)

- Docker-only amd64 runtime: kept; Dockerfile/compose will run Uvicorn ASGI and expose health.
- Single model, multi-RTSP, 5 FPS cap: Model control not in-scope for this feature; 5 FPS cap enforced at decode/serve. No change to single-model policy.
- Env contract: Will honor APP_PORT; GPU_BACKEND/YOLO_MODEL/etc. unaffected here; no model load in this feature. No new envs introduced that conflict.
- Persistence: ONLY `/app/config/config.yml` used.
- GPU backend fail-fast and versions: Unchanged; to be emitted by entrypoint. No GPU usage in this feature.
- Observability: Maintain JSON logs and `/health`; basic Prometheus metrics stub to remain present.
- Security: Non-root, strict input validation, rate limits on mutating routes; no auth; LAN-only posture documented.
- CI/build: buildx linux/amd64; image HEALTHCHECK on `/health`.
- CI runners: CPU-only; tests use synthetic inputs; CI_DRY_RUN remains supported.
- Tooling evidence: Plan to update `artifacts/versions.md` and `artifacts/decisions.md` during implementation.

Gate verdict: PASS (no violations introduced; model-related constraints unaffected by this UI/API feature).

## Project Structure

### Documentation (this feature)

```
specs/002-fastapi-rtsp-streams/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
└── contracts/
    └── openapi.yaml
```

### Source Code (repository root)

```
src/
├── app/
│   ├── __init__.py
│   ├── wsgi.py                 # to be migrated to ASGI entry
│   ├── routes.py               # to be replaced with FastAPI routers
│   ├── config_io.py            # YAML read/write utilities
│   ├── templates/              # Jinja2
│   └── static/
└── tests/
    ├── unit/
    └── integration/
```

Structure Decision: Single web application under `src/app` using FastAPI with APIRouter modules for UI (templates) and REST (streams CRUD, reorder, playback, health).

## Complexity Tracking

No constitution violations at this time.

## Constitution Check (Post-Design Gate)

Re-evaluated after Phase 1 design artifacts (research, data model, contracts, quickstart):

- Docker-only amd64, ASGI/Uvicorn: unchanged and compliant.
- 5 FPS cap: explicitly enforced in playback generator design.
- Persistence limited to `/app/config/config.yml`: confirmed in data model and quickstart.
- Observability and security posture: unchanged; to be preserved during implementation.
- CI CPU-only policy and dry-run: unaffected by this feature; implementation will not introduce GPU dependencies.

Verdict: PASS. No violations introduced; ready for Phase 2 task planning.