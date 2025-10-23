<!--
Sync Impact Report
- Version change: 2.3.0 → 2.4.0
- Modified sections:
  - Core Principles: Added Principle VIII mandating shadcn/ui adoption and clarified frontend requirements
  - Architecture & Execution Constraints: Required shadcn/ui with Tailwind integration for the SPA
  - Tooling & Evidence Requirements: Added shadcn/ui documentation sourcing requirement
  - Governance › Compliance review: Added shadcn/ui compliance checkpoint
- Added sections:
  - Principle VIII: Frontend UI Consistency with shadcn/ui
- Removed sections: None
- Templates requiring updates:
	- .specify/templates/spec-template.md ✅ updated (frontend requirement includes shadcn/ui adoption)
	- .specify/templates/plan-template.md ✅ updated (Constitution Check references shadcn/ui component mandate)
	- .specify/templates/tasks-template.md ✅ updated (frontend tasks include shadcn/ui implementation)
	- README.md ⚠ pending (document shadcn/ui component requirement and Tailwind usage)
	- artifacts/versions.md ⚠ pending (record shadcn/ui and Tailwind versions/links)
	- artifacts/decisions.md ⚠ pending (capture shadcn/ui adoption rationale and migration plan)
- Follow-up TODOs:
	- Define Tailwind + shadcn/ui theming tokens and dark-mode strategy
	- Inventory existing UI for migration to shadcn/ui primitives
-->

# ProxiMeter: RTSP Object Detection Scoring for Home Automation (Docker-only, amd64) Constitution

## Core Principles

### I. Container-Only, Reproducible Runtime (NON-NEGOTIABLE)
The application MUST run exclusively in Docker on linux/amd64. Images are
multi-stage with a pinned base (python:3.12-slim-trixie for backend), minimal OS
packages, and a non-root user in the final image. Frontend MUST be built using
Node.js LTS in a separate build stage and served as static assets from the
backend. Containers are stateless: the ONLY persisted file is
`/app/config/config.yml`. No model caches or artifacts are persisted between
runs. A HEALTHCHECK MUST probe `/health`.

Rationale: Determinism, portability, and secure-by-default execution.

### II. Real-Time Object Detection with Polygon Zone Scoring
Exactly one YOLO model is active at any time across multiple RTSP streams. Each
stream is capped at 5 FPS (decode+inference) using frame skipping/backpressure to
maintain real-time behavior. FFmpeg MUST be used for all RTSP stream ingestion,
decoding, and frame extraction. Users MUST be able to define multiple polygon
zones per stream via the UI. For each detected object within a zone, the system
MUST calculate up to three optional scoring metrics: (1) distance from a target
point, (2) normalized camera coordinates (x, y), and (3) bounding box size
(width × height). Scores MUST be published in real-time to SSE and optionally to
MQTT. The application is NOT a video recorder or NVR; no video storage or
playback history is required beyond live viewing.

Rationale: Focus on real-time scoring for home automation triggers, not archival
video management. Polygon zones enable precise spatial filtering. Multiple
scoring criteria provide flexibility for diverse automation scenarios.

### III. Explicit GPU Backend Contract and Fail-Fast Provisioning
GPU backend is selected via `GPU_BACKEND ∈ {nvidia, amd, intel}`. `entrypoint.sh`
MUST detect the backend, enable the minimal runtime stack (e.g., CUDA/TensorRT,
ROCm/MIVisionX, OpenVINO), verify device access and print versions on startup.
If unavailable or misconfigured, the container MUST exit with a clear, actionable
error. No automatic backend fallback is permitted.

Rationale: Clear failure modes and auditability of the execution environment.

### IV. Observability, Security, and Reliability by Default
Structured JSON logging with configurable levels via env is REQUIRED. The app
MUST expose health and Prometheus metrics, including per-stream FPS, latency,
queue depth, and GPU utilization when available. Implement graceful shutdown,
decoder/GPU cleanup, and a watchdog for stuck streams with exponential backoff.
Security controls include: non-root execution, strict input validation,
rate-limiting on sensitive routes, and file I/O restricted to `config.yml` in a
dedicated volume. This application is intended for trusted LAN environments and
MUST NOT require authentication (no-auth by design); it MUST NOT be exposed to
the public WAN. Document this posture prominently in README and example
compose files.

Rationale: Operability and safety in unattended deployments.

### V. Testing and CI/CD Integrity
Unit tests MUST cover model management, RTSP validation, and MQTT/HTTP score
publishing. Integration tests MUST include synthetic streams that do not require
GPU hardware. GPU-dependent tests MUST NOT be required by CI or normal project
workflows; if a GPU-capable environment is available out-of-band, optional
backend smoke tests MAY verify device discovery and a single-frame inference for
each supported `GPU_BACKEND` on amd64. CI builds MUST target linux/amd64 only,
run on GitHub-hosted CPU-only runners, and publish amd64 manifests. CI MUST NOT
require GPU devices or driver availability to succeed.
 
Rationale: Confidence in correctness across critical surfaces and platforms.
### VI. CPU-only CI Policy (GitHub Runners)
All automated builds and unit/integration tests run on GitHub-hosted CPU-only
runners. The pipeline MUST:

- Avoid any steps that require GPU devices, kernel drivers, or device-specific
	compilation.
- Provide a CI dry-run mode via `CI_DRY_RUN=true` causing `entrypoint.sh` to
	skip device access and emit version information only; application MUST start
	sufficiently to serve `/health` and basic metrics in stub mode.
- Use synthetic inputs for tests; do not download large model weights during CI
	unless cached and strictly necessary.
- Clearly mark GPU smoke tests as "off-CI" and document a manual or self-hosted
	GPU runner process; failures MUST NOT block CPU-only CI but MUST be tracked in
	`artifacts/decisions.md`.

Rationale: Ensure reliable CI on standard runners while preserving production
GPU guarantees through documented, off-CI validation.

### VII. Scoring and Home Automation Integration
The application's PRIMARY PURPOSE is real-time object detection scoring to
trigger home automation workflows. Scores MUST be published via SSE (mandatory)
and optionally via MQTT. Each score event MUST include: timestamp, stream_id,
zone_id (if applicable), object_class, confidence, and up to three optional
scoring values (distance, coordinates, size). Users define scoring behavior
per-zone via the UI: which metrics to calculate, target points for distance
calculation, and thresholds. The system MUST NOT store video recordings, frame
history, or score archives beyond in-memory queues for real-time delivery. UI
MUST provide tools to define/edit/delete polygon zones with visual overlays on
live stream previews.

Rationale: Clear product focus prevents scope creep into video storage/NVR
functionality. SSE provides low-latency, browser-compatible streaming; MQTT
enables integration with external automation platforms (Home Assistant, Node-RED,
etc.). Polygon zones and flexible scoring criteria support diverse use cases
(person detection at doorways, object tracking in driveways, etc.).

### VIII. Frontend UI Consistency with shadcn/ui
The React SPA MUST adopt shadcn/ui component primitives backed by Tailwind CSS
configuration checked into the repo. All new UI MUST compose shadcn/ui
components (extending via the `cn` utility when custom styling is required) and
adhere to a shared design token set for spacing, typography, and state visuals.
If an existing interface cannot migrate immediately, the plan MUST document a
timeline and debt owner. Custom components MUST be built on top of shadcn/ui and
respect accessible semantics (ARIA roles, keyboard navigation, color contrast).
Global theming (light/dark) MUST be controlled through Tailwind tokens exposed by
the shadcn/ui config.

Rationale: shadcn/ui provides a consistent, accessible base for the SPA while
aligning with Tailwind-powered styling. Mandating the design system prevents UI
fragmentation, accelerates development, and enforces accessibility guardrails.

## Architecture & Execution Constraints

- Container-only runtime on linux/amd64; no direct host execution.
- Configuration contract via environment variables (e.g., `APP_PORT`,
	`GPU_BACKEND`, `YOLO_MODEL`, `IMAGE_SIZE`, `MQTT_ENABLED`, `MQTT_HOST`,
	`MQTT_PORT`, `MQTT_TOPIC`, `HTTP_STREAM_ENABLED`, `HTTP_STREAM_PATH`).
- Streams and tunables are managed via the web UI and persisted to a single
	`config.yml` mounted as a Docker volume.
- Models: Select via `YOLO_MODEL` (e.g., `yolo11n`) and `IMAGE_SIZE` (e.g., 320).
	Weights are fetched at container start and exported to ONNX inside the
	container to unify execution on amd64 across backends. Only one model is ever
	loaded at a time.
- Streams: RTSP CRUD via UI, validated at save; per-stream enable/disable.
	Enforce 5 FPS cap with backpressure. FFmpeg MUST handle all RTSP ingestion,
	decoding, and frame extraction. NO video recording or storage beyond live frames
	for inference.
- Polygon Zones: Per-stream zone management (CRUD) via UI with visual polygon
	editor overlays on live stream preview. Each zone stores: name, point array
	(polygon vertices), enabled scoring metrics (distance/coordinates/size), target
	point (if distance scoring enabled), and active/inactive state. Zones persisted
	in config.yml per stream.
- Scoring Pipeline: For each inference frame, detect objects, filter by polygon
	zones, calculate enabled scoring metrics per detected object, and emit score
	events to SSE and optionally MQTT. No persistent score storage (real-time only).
- Web API/UI: FastAPI backend application with APIRouter modules for REST API,
	stream control, zone management, score streaming (SSE), health, and metrics.
	Frontend MUST be a React TypeScript SPA with mandatory React 19.2, TypeScript
	5+, and Vite for bundling. The component system MUST be implemented with
	shadcn/ui on top of Tailwind CSS; custom elements MUST extend shadcn/ui tokens
	and utilities (e.g., `cn`). Optional animation libraries MAY include
	framer-motion, react-bits, aceternity UI, and motion-bits for enhanced UX.
	Backend serves REST API only (no server-rendered templates). Frontend
	communicates via REST/SSE. Dark, responsive UI optimized for mobile/touch with
	polygon zone editor and shadcn/ui-consistent styling.
- APIs & outputs:
	- SSE score streaming (mandatory): Serve real-time score events at a dedicated
		SSE endpoint. Message schema MUST include: `timestamp, stream_id, zone_id (or
		null), object_class, confidence, distance (optional), coordinates (optional),
		size (optional)`.
	- MQTT (optional): If `MQTT_ENABLED=true`, publish score events to
		`MQTT_HOST:MQTT_PORT` under `MQTT_TOPIC` with sensible QoS/retain. Use same
		schema as SSE.
	- Provide REST endpoints for: stream CRUD, zone CRUD per stream, latest score
		snapshot per stream/zone, stream status.
- Base image policy: Use `python:3.12-slim-trixie` for backend amd64; use
	`node:lts-slim` for frontend build stage; multi-stage builds compile wheels and
	frontend assets in builder stages; final stage contains no compilers and serves
	frontend static assets alongside backend API. FFmpeg MUST be installed in the
	final runtime image.
- Dockerfile standards: Non-root user, minimal OS packages, pinned base and
	dependency versions, HEALTHCHECK for `/health`. Do not encode platform policy
	in the Dockerfile (platform is enforced by build commands and CI). Frontend
	build stage MUST produce optimized production bundle.
- Observability & reliability: JSON logs, health, Prometheus metrics, graceful
	shutdown, watchdog auto-reconnect with exponential backoff.
- Security & hardening: Non-root, input validation, CSRF, rate-limit sensitive
	routes, restrict file I/O to `config.yml`, disallow arbitrary shell execution.
	No authentication is provided or required; deployment is LAN-only and MUST NOT
	be exposed to WAN. Provide README warnings and example compose using
	LAN-scoped exposure.
- Docker & CI: Build with buildx and `--platform=linux/amd64`; publish ONLY
	amd64 images/tags. Provide a docker-compose example with `platform:
	linux/amd64` and GPU device exposure per backend on amd64 hosts.
- CI runners: Assume GitHub-hosted CPU-only runners. The image and tests MUST
	succeed without GPU devices present. Support `CI_DRY_RUN=true` to bypass GPU
	checks while still validating startup, `/health`, configuration loading, and
	logging/metrics wiring.
- Testing: Unit, integration with synthetic streams. Optional off-CI GPU smoke
	tests MAY be run (if hardware available) to validate device discovery and a
	single-frame inference per `GPU_BACKEND`.
- Persistence & ports: Persist ONLY `/app/config/config.yml`; expose `APP_PORT`
	for the ASGI server (Uvicorn/Gunicorn); document HTTP streaming path and any
	additional ports used.
- Developer experience: Provide a Makefile for build, run, test, push; enforce
	linux/amd64 flags and consistent tagging; include env var matrix and backend
	support table in README plus Home Assistant examples. Support local frontend
	development with hot-reload (Vite dev server proxying to backend). Document
	frontend build process and technology stack (React, TypeScript, shadcn/ui,
	Tailwind, optional animation libraries).

## Tooling & Evidence Requirements

- During planning/implementation, agents MUST use SearXNG web search to resolve 
    latest stable versions and installation guidance for:
	* Backend: CUDA/TensorRT (NVIDIA), ROCm/MIVisionX (AMD), OpenVINO (Intel), ONNX
	  Runtime, PyTorch/TorchAudio/TorchVision (if used), **FFmpeg** (mandatory),
	  FastAPI/ASGI, Python packages
	* Frontend: **React 19.2** (mandatory), TypeScript 5+, Vite, Node.js LTS,
	  shadcn/ui (mandatory), Tailwind CSS, framer-motion (optional), react-bits
	  (optional), aceternity UI (optional), motion-bits (optional)
	* Infrastructure: Docker, docker-compose best practices
	* Polygon/geometry libraries: Shapely (Python) or equivalent for point-in-polygon
	  checks and geometric calculations
- Agents MUST ingest and reference official documentation pages before pinning
	versions or commands, use the Context7 tool to look up documentation.
- Agents MUST record resolved versions and documentation URLs in
	`artifacts/versions.md` and implement `--version` checks in `entrypoint.sh` to
	emit versions at startup (backend: Python, FastAPI, FFmpeg, GPU runtimes;
	frontend: Node, React, TypeScript versions logged during build).
- If conflicts or deprecations are discovered, agents MUST prefer the most
	recent stable docs and explicitly document trade-offs in
	`artifacts/decisions.md`.

## Governance

- This Constitution supersedes ad-hoc practices for this project. All changes to
	architecture, CI, security posture, or runtime behavior MUST comply.
- Amendments require a PR that:
	1) proposes redlines, 2) explains bump type (MAJOR/MINOR/PATCH), 3) updates
	dependent templates/docs as needed, 4) sets `Last Amended` to the PR date.
- Versioning policy (semantic):
	- MAJOR: Backward-incompatible governance/principle removals or redefinitions.
	- MINOR: New principle/section added or materially expanded guidance.
	- PATCH: Clarifications, wording, typo fixes, non-semantic refinements.
- Compliance review: Every PR MUST include a "Constitution Check" confirming:
	- Docker-only amd64, single-model/multi-stream at 5 FPS cap, and env/config
		contract are preserved.
	- Application purpose is object detection scoring for home automation (NOT NVR/
		recording); no video storage beyond live inference frames.
	- FFmpeg is used for all RTSP stream processing; version is validated and logged.
	- GPU backend fail-fast behavior and no fallback are preserved.
	- Frontend is React 19.2 TypeScript SPA with Vite and composes shadcn/ui
		components on Tailwind CSS; backend is REST API + SSE only (no server-rendered
		templates).
	- Polygon zone management (CRUD, visual editor) and scoring pipeline (distance,
		coordinates, size) are functional.
	- SSE score streaming is mandatory; MQTT is optional; both use consistent schema.
	- Observability (JSON logs, metrics, health) and security controls (rate-limit,
		input validation, non-root) are intact; no-auth and LAN-only posture is
		documented; no WAN exposure examples are introduced.
	- CI enforces linux/amd64-only builds; Dockerfile standards are met; multi-stage
		build includes frontend production bundle.
	- Tests are updated and passing on CPU-only CI. If optional GPU smoke tests are
		performed out-of-band, record outcomes; if not available, record the
		limitation in `artifacts/decisions.md`.
	- Tooling & Evidence artifacts (`artifacts/versions.md`, `decisions.md`) are
		maintained and `entrypoint.sh` emits versions (including FFmpeg).

**Version**: 2.4.0 | **Ratified**: 2025-10-17 | **Last Amended**: 2025-10-21