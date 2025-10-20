---
description: "Task list template for feature implementation"
---

# Tasks: [FEATURE NAME]

**Input**: Design documents from `/specs/[###-feature-name]/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: The examples below include test tasks. Tests are OPTIONAL - only include them if explicitly requested in the feature specification.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions
- **Single project**: `src/`, `tests/` at repository root
- **Web app**: `backend/src/`, `frontend/src/`
- **Mobile**: `api/src/`, `ios/src/` or `android/src/`
- Paths shown below assume single project - adjust based on plan.md structure

<!-- 
  ============================================================================
  IMPORTANT: The tasks below are SAMPLE TASKS for illustration purposes only.
  
  The /speckit.tasks command MUST replace these with actual tasks based on:
  - User stories from spec.md (with their priorities P1, P2, P3...)
  - Feature requirements from plan.md
  - Entities from data-model.md
  - Endpoints from contracts/
  
  Tasks MUST be organized by user story so each story can be:
  - Implemented independently
  - Tested independently
  - Delivered as an MVP increment
  
  DO NOT keep these sample tasks in the generated tasks.md file.
  ============================================================================
-->

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [ ] T001 Create project structure per implementation plan (backend/, frontend/, Makefile)
- [ ] T002 Initialize Python 3.12 backend project; add FastAPI, Uvicorn, Prometheus, MQTT, ONNX Runtime, FFmpeg Python bindings
- [ ] T003 [P] Initialize React TypeScript frontend with Vite; add React 18+, TypeScript 5+, optional animation libs (framer-motion, react-bits, aceternity UI, motion-bits)
- [ ] T004 [P] Configure backend: ruff/black, mypy; PEP8; pre-commit hooks
- [ ] T005 [P] Configure frontend: ESLint, Prettier, TypeScript strict mode
- [ ] T006 Create Dockerfile (multi-stage: Node.js frontend build → Python backend with FFmpeg, non-root, HEALTHCHECK)
- [ ] T007 Create docker-compose example with platform: linux/amd64 and GPU device exposure
- [ ] T008 Create Makefile with amd64-enforcing targets (build, run, test, push, frontend-dev)
- [ ] T009 Create artifacts/versions.md and artifacts/decisions.md placeholders; document FFmpeg and React TypeScript adoption

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

Examples of foundational tasks (adjust based on your project):

- [ ] T010 [P] Implement FastAPI app; register APIRouter modules (api, streams, zones, scores/SSE, health, metrics); NO UI routes (React SPA handles UI)
- [ ] T011 [P] Implement structured JSON logging and error handling
- [ ] T012 [P] Implement config.yml loader/saver with schema validation (streams + polygon zones)
- [ ] T013 [P] Implement RTSP validator utility with FFmpeg probe and unit tests
- [ ] T014 [P] Implement polygon zone models: point array, target point, enabled metrics (distance/coords/size)
- [ ] T015 [P] Implement point-in-polygon utility using Shapely or equivalent; unit tests
- [ ] T016 [P] Implement scoring calculator: distance from target, normalized coordinates, bounding box size
- [ ] T017 [P] Implement metrics (Prometheus): per-stream FPS, latency, queue depth, GPU utilization, scores published
- [ ] T018 [P] Implement entrypoint.sh provisioning for GPU_BACKEND with version checks (include FFmpeg version) and fail-fast
- [ ] T019 [P] Implement ONNX export pipeline for YOLO_MODEL on startup; single-model manager
- [ ] T020 [P] Implement inference worker scaffolding with FFmpeg frame extraction, queue, and 5 FPS cap
- [ ] T021 [P] Implement scoring pipeline: detect objects, filter by zones, calculate metrics, emit to SSE + optional MQTT
- [ ] T022 [P] Implement SSE endpoint for real-time score streaming with schema validation
- [ ] T023 [P] Implement optional MQTT publisher for score events (same schema as SSE)
- [ ] T024 [P] Implement security middleware: rate-limit sensitive routes, input validation; document LAN-only/no-auth posture; NO video storage
- [ ] T025 [P] Implement static file serving for React production build in FastAPI
- [ ] T026 [P] Create frontend project structure (React 19.2): components/, pages/, hooks/, services/, lib/
- [ ] T027 [P] Implement frontend API client service for backend REST endpoints (streams, zones, scores)
- [ ] T028 [P] Implement polygon zone editor component with canvas overlay on live stream preview
- [ ] T029 [P] CI workflow to build amd64-only images via buildx (frontend build → backend runtime) and publish tags (GitHub runners)
- [ ] T030 [P] Add CI_DRY_RUN=true path to start app without GPU and validate /health on CPU-only CI

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - [Title] (Priority: P1) 🎯 MVP

**Goal**: [Brief description of what this story delivers]

**Independent Test**: [How to verify this story works on its own]

### Tests for User Story 1 (OPTIONAL - only if tests requested) ⚠️

**NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T018 [P] [US1] Contract test for HTTP score snapshot endpoint
- [ ] T019 [P] [US1] Integration test using synthetic RTSP stream

### Implementation for User Story 1

- [ ] T020 [P] [US1] Implement latest score snapshot GET endpoint
- [ ] T021 [P] [US1] Implement SSE/WebSocket streaming endpoint (transport TBD)
- [ ] T022 [US1] Wire inference worker output to score store feeding endpoints
- [ ] T023 [US1] Add logging, validation, and metrics for endpoints

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - [Title] (Priority: P2)

**Goal**: [Brief description of what this story delivers]

**Independent Test**: [How to verify this story works on its own]

### Tests for User Story 2 (OPTIONAL - only if tests requested) ⚠️

- [ ] T024 [P] [US2] Contract test for RTSP CRUD API
- [ ] T025 [P] [US2] Integration test validating 5 FPS cap under load

### Implementation for User Story 2

- [ ] T026 [P] [US2] Implement UI CRUD for RTSP streams mapped to config.yml
- [ ] T027 [US2] Enforce per-stream enable/disable and thresholds/zones persistence
- [ ] T028 [US2] Validate RTSP URLs on save; error surfacing in UI
- [ ] T029 [US2] Integrate CRUD with inference worker lifecycle

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - [Title] (Priority: P3)

**Goal**: [Brief description of what this story delivers]

**Independent Test**: [How to verify this story works on its own]

### Tests for User Story 3 (OPTIONAL - only if tests requested) ⚠️

- [ ] T030 [P] [US3] Contract test for MQTT publishing (schema, QoS/retain)
- [ ] T031 [P] [US3] Integration test asserting <1s end-to-end delay

### Implementation for User Story 3

- [ ] T032 [P] [US3] Implement MQTT publisher with structured payload
- [ ] T033 [US3] Configurable QoS/retain defaults; topic naming under MQTT_TOPIC
- [ ] T034 [US3] Telemetry and error handling for broker disconnects

**Checkpoint**: All user stories should now be independently functional

---

[Add more user story phases as needed, following the same pattern]

---

## Phase N: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] TXXX [P] Documentation updates in docs/
- [ ] TXXX Code cleanup and refactoring
- [ ] TXXX Performance optimization across all stories
- [ ] TXXX [P] Additional unit tests (if requested) in tests/unit/
- [ ] TXXX Security hardening
- [ ] TXXX Run quickstart.md validation

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - May integrate with US1 but should be independently testable
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - May integrate with US1/US2 but should be independently testable

### Within Each User Story

- Tests (if included) MUST be written and FAIL before implementation
- Models before services
- Services before endpoints
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel (within Phase 2)
- Once Foundational phase completes, all user stories can start in parallel (if team capacity allows)
- All tests for a user story marked [P] can run in parallel
- Models within a story marked [P] can run in parallel
- Different user stories can be worked on in parallel by different team members

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together (if tests requested):
Task: "Contract test for [endpoint] in tests/contract/test_[name].py"
Task: "Integration test for [user journey] in tests/integration/test_[name].py"

# Launch all models for User Story 1 together:
Task: "Create [Entity1] model in src/models/[entity1].py"
Task: "Create [Entity2] model in src/models/[entity2].py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test User Story 1 independently
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Test independently → Deploy/Demo
4. Add User Story 3 → Test independently → Deploy/Demo
5. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1
   - Developer B: User Story 2
   - Developer C: User Story 3
3. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence