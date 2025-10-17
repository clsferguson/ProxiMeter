# Implementation Plan: Minimum Working App – Hello Counter MVP

**Branch**: `001-flask-hello-counter` | **Date**: 2025-10-17 | **Spec**: C:\Save\Code Projects\ProxiMeter\specs\001-flask-hello-counter\spec.md
**Input**: Feature specification from `/specs/001-flask-hello-counter/spec.md`

## Summary

Deliver an operational containerized web application that:
- Serves a dark-themed landing page with purple highlights and a "Hello" message
- Displays a persistent counter loaded from and saved to `config.yml`
- Provides an increment button that updates the counter immediately and persists it
- Exposes `/health` for readiness
- Includes a placeholder README and an MIT license
- Provides CI (GitHub Actions) to build the linux/amd64 image and smoke-test `/health`

Primary approach: Flask application packaged in a Docker image based on a slim Python base; YAML file persistence for the counter; very small HTML/CSS with inline or static assets; CI runs build and a container smoke test on hosted runners.

## Technical Context

**Language/Version**: Python 3.12  
**Primary Dependencies**: Flask (UI/routing), Jinja2 (templating), PyYAML (YAML persistence), Gunicorn (WSGI server), prometheus-client (metrics)  
**Storage**: YAML file `config.yml` persisted on a bound volume  
**Testing**: pytest for unit tests of config load/save and route handlers  
**Target Platform**: Docker linux/amd64 (container-only)  
**Project Type**: Single web backend (server-rendered HTML with minimal JS)  
**Performance Goals**: Page loads and button actions complete within 2 seconds on a local machine; health responds <200 ms when ready; metrics endpoint responds within typical request latencies  
**Constraints**: No GPUs or external services required; no auth (LAN-only posture documented); persist only `config.yml`; provide `/metrics` and JSON logs; support `CI_DRY_RUN=true`  
**Scale/Scope**: Single landing page, one counter entity, minimal routes

## Constitution Check

Gate evaluation for this MVP:
- Docker-only runtime on linux/amd64; no host execution paths → PASS (Dockerfile + CI enforce amd64)
- Persist ONLY `/app/config/config.yml` via volume; no model caches/artifacts → PASS (counter only)
- Observability: JSON logs, /health, Prometheus metrics present → ALIGN (health and metrics endpoints provided for MVP; lightweight JSON logging enabled)
- Security: non-root, input validation, rate-limits; restricted file I/O; LAN-only, no-auth → PASS (non-root image, restricted config path; document LAN-only posture; rate-limit not critical for MVP but requests are minimal)
- CI/build: buildx with `--platform=linux/amd64`; healthcheck in image; CPU-only runners → PASS (CI workflow builds amd64 and runs smoke test on hosted runners)
- CI dry-run, GPU constraints, YOLO/RTSP model constraints → OUT-OF-SCOPE FOR THIS FEATURE (no models/RTSP in MVP; does not conflict with constitution; to be added in later features)

Conclusion: Non-negotiable container/runtime/CI constraints are met. Items specific to models/RTSP/GPUs are intentionally out-of-scope for this MVP and do not impede future compliance.

## Project Structure

### Documentation (this feature)

```
specs/001-flask-hello-counter/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
└── contracts/
```

### Source Code (repository root)

```
src/
└── app/
    ├── __init__.py          # Flask app factory, routes registration
    ├── routes.py            # UI routes and API endpoint for increment
    ├── config_io.py         # Load/save YAML counter with basic locking
    ├── static/
    │   └── styles.css       # Dark theme with purple highlights
    └── templates/
        └── index.html       # Hello page with counter and button

config/
└── config.yml               # Persisted via volume; created at first run

Dockerfile
docker-compose.yaml (optional developer aid)
.github/workflows/ci.yml     # Build & smoke test CI
LICENSE (MIT)
README.md
```

**Structure Decision**: Single backend Flask app under `src/app` with a simple templated UI and small API endpoints; YAML persisted under `/app/config/config.yml` in the container; expose `/health` and `/metrics`; configure JSON logging via env.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Minimal Prometheus metrics included | Meet constitution while keeping footprint small | Full suite deferred; minimal gauges/counters suffice for MVP |
| GPU/model/RTSP requirements out-of-scope | This feature is a bootstrap skeleton; no inference/model use | Forcing model/RTSP scaffolding now would increase scope and delay MVP without benefits |