<!--
Sync Impact Report
- Version change: 1.1.0 → 2.0.0
- Modified principles:
  - IV. Observability, Security, and Reliability by Default → IV. Observability, Security, and Reliability by Default (no-auth, LAN-only; removed CSRF requirement)
  - V. Testing and CI/CD Integrity → V. Testing and CI/CD Integrity (clarified GPU limits; CI dry-run)
- Added sections:
  - VI. CPU-only CI Policy (GitHub Runners)
- Removed sections: None
- Templates requiring updates:
	- .specify/templates/plan-template.md ✅ updated (CI on CPU-only runners; optional off-CI GPU tests)
	- .specify/templates/spec-template.md ✅ updated (FR/SC reflect CI dry-run; GPU tests optional/off-CI; no-auth LAN-only)
	- .specify/templates/tasks-template.md ✅ updated (CI dry-run validation task)
	- .specify/templates/commands/* ⚠ pending (directory absent)
	- README.md ⚠ pending (document CI_DRY_RUN env, GPU test policy, and LAN-only/no-auth posture)
	- artifacts/versions.md ⚠ pending (create and keep current)
	- artifacts/decisions.md ⚠ pending (create and record trade-offs, include GPU test policy/limitations)
- Follow-up TODOs:
	- Create artifacts/versions.md and artifacts/decisions.md per Tooling policy
	- Add README with env var matrix, backend support table, MQTT/SSE examples, CI_DRY_RUN usage, and LAN-only/no-auth warning
	- Add docker-compose example with platform: linux/amd64 and GPU device exposure
	- If desired later, define an optional off-CI/manual GPU test runbook or configure a self-hosted GPU runner
-->

# Multi-RTSP Person Detection (Docker-only, amd64) Constitution

## Core Principles

### I. Container-Only, Reproducible Runtime (NON-NEGOTIABLE)
The application MUST run exclusively in Docker on linux/amd64. Images are
multi-stage with a pinned base (python:3.12-slim-trixie), minimal OS packages,
and a non-root user in the final image. Containers are stateless: the ONLY
persisted file is `/app/config/config.yml`. No model caches or artifacts are
persisted between runs. A HEALTHCHECK MUST probe `/health`.

Rationale: Determinism, portability, and secure-by-default execution.

### II. Single Model, Many Streams with Backpressure Discipline
Exactly one YOLO model is active at any time across multiple RTSP streams. Any
model switch MUST gracefully restart inference workers without losing UI
configuration in `config.yml`. Each stream is capped at 5 FPS (decode+inference)
using frame skipping/backpressure to maintain real-time behavior.

Rationale: Predictable latency and resource fairness under load.

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
- Streams: RTSP CRUD via UI, validated at save; per-stream enable/disable and
	optional thresholds/zones if provided. Enforce 5 FPS cap with backpressure.
- Web UI: Flask app factory with Blueprints for UI, REST, stream control,
	health, and metrics. Dark, responsive UI optimized for mobile/touch.
- APIs & outputs:
	- MQTT (optional): If `MQTT_ENABLED=true`, publish numeric score per stream to
		`MQTT_HOST:MQTT_PORT` under `MQTT_TOPIC` with sensible QoS/retain and
		metadata: `timestamp, stream_id, score, confidence, model_id`.
	- HTTP score streaming (optional): If `HTTP_STREAM_ENABLED=true`, serve a
		real-time endpoint at `HTTP_STREAM_PATH` using SSE or WebSocket. Message
		schema MUST include `timestamp, stream_id, score, confidence, model_id`.
	- Provide a GET endpoint to fetch the latest score snapshot per stream.
- Base image policy: Use `python:3.12-slim-trixie` for amd64; multi-stage builds
	compile wheels in a builder stage; final stage contains no compilers.
- Dockerfile standards: Non-root user, minimal OS packages, pinned base and
	dependency versions, HEALTHCHECK for `/health`. Do not encode platform policy
	in the Dockerfile (platform is enforced by build commands and CI).
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
	for Flask server; document HTTP streaming path and any additional ports used.
- Developer experience: Provide a Makefile for build, run, test, push; enforce
	linux/amd64 flags and consistent tagging; include env var matrix and backend
	support table in README plus Home Assistant examples.

## Tooling & Evidence Requirements

- During planning/implementation, agents MUST use SearXNG web search to resolve 
    latest stable versions and installation guidance for CUDA/TensorRT (NVIDIA),
	ROCm/MIVisionX (AMD), OpenVINO (Intel), ONNX Runtime, PyTorch/TorchAudio/
	TorchVision (if used), FFmpeg/GStreamer components, Flask/Docker, or any 
    other not mentioned packages best practices.
- Agents MUST ingest and reference official documentation pages before pinning
	versions or commands, use the Context7 tool to look up documentation.
- Agents MUST record resolved versions and documentation URLs in
	`artifacts/versions.md` and implement `--version` checks in `entrypoint.sh` to
	emit versions at startup.
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
	- GPU backend fail-fast behavior and no fallback are preserved.
	- Observability (JSON logs, metrics, health) and security controls (rate-limit,
		input validation, non-root) are intact; no-auth and LAN-only posture is
		documented; no WAN exposure examples are introduced.
	- CI enforces linux/amd64-only builds; Dockerfile standards are met.
	- Tests are updated and passing on CPU-only CI. If optional GPU smoke tests are
		performed out-of-band, record outcomes; if not available, record the
		limitation in `artifacts/decisions.md`.
	- Tooling & Evidence artifacts (`artifacts/versions.md`, `decisions.md`) are
		maintained and `entrypoint.sh` emits versions.

**Version**: 2.0.0 | **Ratified**: 2025-10-17 | **Last Amended**: 2025-10-17