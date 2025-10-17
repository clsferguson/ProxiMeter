---
description: "Executable task list for Hello Counter MVP"
---

# Tasks: Minimum Working App – Hello Counter MVP

Input: Design documents from `specs/001-flask-hello-counter/`
Prerequisites: `plan.md` (required), `spec.md` (required), optional: `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

Tests: Only include if explicitly requested. This feature relies on a CI smoke test of `/health`; no unit tests required for MVP.

Organization: Tasks are grouped by user story to enable independent implementation and testing of each story.

Format: `[ID] [P?] [Story] Description`
- [P]: Can run in parallel (different files, no dependencies on incomplete tasks)
- [Story]: Which user story this task belongs to (e.g., US1, US2, US3)
- All descriptions include exact file paths

Path Conventions (from plan.md)
- Single backend project under repository root
- Source: `src/app/`
- Config (persisted): `config/config.yml`
- CI: `.github/workflows/`

---

## Phase 1: Setup (Project initialization)

Purpose: Create the repository structure and core scaffolding to enable development.

- [X] T001 Create project directories: `src/app/`, `src/app/templates/`, `src/app/static/`, `config/`, `.github/workflows/`
- [X] T002 Create `requirements.txt` with pinned deps: Flask, PyYAML, Gunicorn at repo root `requirements.txt`
- [X] T003 [P] Create `.dockerignore` at repo root (exclude: `.git`, `__pycache__/`, `.venv/`, `config/*.yml` except mounted volume)
- [X] T004 [P] Create `.gitignore` at repo root (exclude Python artifacts and `config/config.yml`)

---

## Phase 2: Foundational (Blocking prerequisites)

Purpose: Core application scaffolding required before any user story work.

- [X] T005 [P] Implement Flask app factory in `src/app/__init__.py` (function `create_app()`; configure Jinja, static folder)
- [X] T006 [P] Add WSGI entrypoint in `src/app/wsgi.py` exposing `app = create_app()`
- [X] T007 [P] Implement YAML config IO in `src/app/config_io.py` (`load_counter()`, `save_counter(value)`, default 0, max 2147483647, create `config/config.yml` if missing)
- [X] T008 Create routes module scaffold `src/app/routes.py` with a `Blueprint('main', __name__)` and placeholder registration function `register_blueprint(app)`

Checkpoint: Foundation ready – user story implementation can begin.

---

## Phase 3: User Story 1 – See and increment counter (Priority: P1) – MVP

Goal: User sees a hello page with a counter and can increment it; value persists across reloads/restarts.

Independent Test: Load `/`, click "Increment", refresh; the value remains incremented.

Implementation

- [X] T009 [P] [US1] Create dark theme with purple highlights stylesheet `src/app/static/styles.css`
- [X] T010 [US1] Create `src/app/templates/index.html` (hello message, current counter value, increment button, embedded JS `fetch('/api/counter', {method:'POST'})` to update the DOM; show messages for cap reached/write errors). Ensure keyboard accessibility (Enter/Space activates button) and visible 2px focus outline (#7C3AED).
- [X] T011 [US1] Implement routes in `src/app/routes.py`: `GET /` render `index.html` with current value; `GET /api/counter` return JSON `{counter}`; `POST /api/counter` increment with cap, persist via `config_io`
- [X] T012 [P] [US1] Register routes blueprint in app factory (`src/app/__init__.py`): import `register_blueprint` and call from `create_app()`

Checkpoint: User Story 1 is fully functional and testable independently.

---

## Phase 4: User Story 2 – Run the app in a container (Priority: P2)

Goal: Build and run the app in a container; `/health` confirms readiness.

Independent Test: Build the image (linux/amd64), run the container, access `/` and `/health`.

Implementation

- [X] T013 [US2] Implement health endpoint in `src/app/routes.py`: `GET /health` → return 200 "ok"
- [X] T014 [P] [US2] Create `Dockerfile` at repo root: base `python:3.12-slim-trixie`, copy app, `pip install -r requirements.txt`, non-root user, expose 8000, `HEALTHCHECK` hitting `/health`, `CMD ["gunicorn","-w","2","-b","0.0.0.0:8000","src.app.wsgi:app"]`
- [X] T015 [P] [US2] Add CI workflow `.github/workflows/ci.yml` to build linux/amd64 image and smoke-test `/health` by running the container. Export `CI_DRY_RUN=true`; poll `http://localhost:8000/health` for up to 30s (1s interval) and fail if not `200 ok`. Optionally validate `GET /metrics` returns 200.

Checkpoint: User Story 2 is independently verifiable via container build/run and health check.

---

## Phase 5: User Story 3 – Repository housekeeping (Priority: P3)

Goal: Provide README with usage instructions and MIT license.

Independent Test: README explains build/run with volume for `config.yml`; LICENSE contains correct MIT text and copyright.

Implementation

 - [X] T016 [P] [US3] Create `README.md` at repo root with project description, docker build/run commands, and persistence notes (map host `./config` to `/app/config`). The README must include, at minimum, a friendly LAN-only/no-auth safety note and brief mentions of `/health` and `/metrics` endpoints per constitution, while keeping tone friendly.
 - [X] T017 [P] [US3] Create `LICENSE` at repo root with MIT License (© 2025 clsferguson)

Checkpoint: User Story 3 is complete.

---

## Phase N: Polish & Cross-Cutting Concerns

Purpose: Improvements that affect multiple user stories.

- [ ] T018 Run `specs/001-flask-hello-counter/quickstart.md` commands to validate and update as needed if port/paths differ
- [ ] T019 [P] Add JSON logging configuration controlled by `LOG_LEVEL` env (default INFO); emit newline-delimited JSON.
- [ ] T020 [P] Add `/metrics` endpoint using `prometheus_client`: include gauge for current counter value and a simple HTTP request counter; expose process metrics.
- [ ] T021 [P] Implement `CI_DRY_RUN` behavior: in dry-run, use in-memory counter and avoid disk writes; still serve `/health` and `/metrics`.

---

## Dependencies & Execution Order

Phase Dependencies
- Setup (Phase 1): No dependencies – start immediately
- Foundational (Phase 2): Depends on Setup completion – BLOCKS all user stories
- User Stories (Phase 3+): Depend on Foundational completion
  - User stories can proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- Polish (Final): After desired user stories

User Story Dependencies
- User Story 1 (P1): Starts after Foundational – independent of other stories
- User Story 2 (P2): Starts after Foundational – independent of US1 for build/health, but benefits from US1 for full demo
- User Story 3 (P3): Independent – can be done anytime after Setup

Within Each User Story
- Implement endpoints/UI as described; ensure persistence via `config_io`
- Validate story works independently before moving on

---

## Parallel Opportunities

- Setup: T003, T004 can run in parallel with T001–T002
- Foundational: T005–T007 can run in parallel (different files); T008 can follow
- User Story 1: T009 can run in parallel with T010–T012 (distinct files). Note: T010 and T011 touch different files; T012 touches `__init__.py`
- User Story 2: T014 and T015 can run in parallel; T013 is independent but typically quick
- User Story 3: T016 and T017 can run in parallel

---

## Parallel Execution Examples

User Story 1
- Parallel set A: T009 (styles.css)
- Parallel set B: T010 (index.html) and T012 (app factory registration)
- Then: T011 (routes)

User Story 2
- Parallel: T014 (Dockerfile) and T015 (CI workflow)
- Then: T013 (/health route)

User Story 3
- Parallel: T016 (README.md) and T017 (LICENSE)

---

## Implementation Strategy

MVP First (User Story 1 only)
1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1
4. Stop and validate: Manually test `/` and counter persistence

Incremental Delivery
1. Add User Story 2 → Validate container build/run and `/health`
2. Add User Story 3 → Documentation and licensing ready

Parallel Team Strategy
- Once Foundational completes:
  - Dev A: US1 UI + routes
  - Dev B: Dockerfile + CI (US2)
  - Dev C: README + LICENSE (US3)

---

## Notes

- [P] tasks: different files with no blocking dependencies
- [Story] labels: only in user story phases
- Ensure `config/config.yml` is persisted via a host volume in container runs
- Keep UI neutral and accessible; dark theme with purple highlights as requested
- CI must target linux/amd64 hosted runners and smoke-test `/health`
