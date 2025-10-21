# Feature Specification: [FEATURE NAME]

**Feature Branch**: `[###-feature-name]`  
**Created**: [DATE]  
**Status**: Draft  
**Input**: User description: "$ARGUMENTS"

## User Scenarios & Testing *(mandatory)*

<!--
  IMPORTANT: User stories should be PRIORITIZED as user journeys ordered by importance.
  Each user story/journey must be INDEPENDENTLY TESTABLE - meaning if you implement just ONE of them,
  you should still have a viable MVP (Minimum Viable Product) that delivers value.
  
  Assign priorities (P1, P2, P3, etc.) to each story, where P1 is the most critical.
  Think of each story as a standalone slice of functionality that can be:
  - Developed independently
  - Tested independently
  - Deployed independently
  - Demonstrated to users independently
-->

### User Story 1 - [Brief Title] (Priority: P1)

[Describe this user journey in plain language]

**Why this priority**: [Explain the value and why it has this priority level]

**Independent Test**: [Describe how this can be tested independently - e.g., "Can be fully tested by [specific action] and delivers [specific value]"]

**Acceptance Scenarios**:

1. **Given** [initial state], **When** [action], **Then** [expected outcome]
2. **Given** [initial state], **When** [action], **Then** [expected outcome]

---

### User Story 2 - [Brief Title] (Priority: P2)

[Describe this user journey in plain language]

**Why this priority**: [Explain the value and why it has this priority level]

**Independent Test**: [Describe how this can be tested independently]

**Acceptance Scenarios**:

1. **Given** [initial state], **When** [action], **Then** [expected outcome]

---

### User Story 3 - [Brief Title] (Priority: P3)

[Describe this user journey in plain language]

**Why this priority**: [Explain the value and why it has this priority level]

**Independent Test**: [Describe how this can be tested independently]

**Acceptance Scenarios**:

1. **Given** [initial state], **When** [action], **Then** [expected outcome]

---

[Add more user stories as needed, each with an assigned priority]

### Edge Cases

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right edge cases.
-->

- What happens when [boundary condition]?
- How does system handle [error scenario]?

## Requirements *(mandatory)*

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right functional requirements.
-->

### Functional Requirements

- **FR-001**: Run exclusively in Docker on linux/amd64; include HEALTHCHECK /health; multi-stage build with Node.js frontend build and Python backend runtime
- **FR-002**: Load a single YOLO model specified by YOLO_MODEL and IMAGE_SIZE; export to ONNX on startup
- **FR-003**: Manage multiple RTSP streams with CRUD via web UI; validate at save; NO video recording or storage (live frames only)
- **FR-004**: Enforce max 5 FPS per stream using frame skipping/backpressure; use FFmpeg for all RTSP ingestion, decoding, and frame extraction
- **FR-005**: Polygon zone management per stream: CRUD via REST API; visual polygon editor in UI with point array editing; zones stored in config.yml
- **FR-006**: Scoring pipeline: for each detected object in a zone, calculate up to 3 optional metrics: (1) distance from target point, (2) normalized camera coordinates, (3) bounding box size
- **FR-007**: SSE score streaming (MANDATORY): real-time events with schema: timestamp, stream_id, zone_id, object_class, confidence, distance, coordinates, size
- **FR-008**: Optional MQTT publishing of score events using same schema as SSE; configurable QoS/retain
- **FR-009**: Provide FastAPI-based REST API with APIRouter modules; NO server-rendered templates; serve React production build as static assets
- **FR-010**: Frontend MUST be React 19.2 TypeScript 5+ SPA built with Vite that composes shadcn/ui components on Tailwind CSS; optional animation libraries: framer-motion, react-bits, aceternity UI, motion-bits
- **FR-011**: Provide REST endpoints for: stream CRUD, zone CRUD per stream, latest score snapshot per stream/zone, stream status
- **FR-012**: Persist only /app/config/config.yml (streams + zones); no model caches, artifacts, video, or score history
- **FR-013**: GPU backend provisioning via entrypoint.sh; fail fast on errors; print versions (including FFmpeg); support CI dry-run via `CI_DRY_RUN=true` to skip device access on CPU-only runners
- **FR-014**: Structured JSON logging; Prometheus metrics for FPS, latency, queues, GPU utilization, scores published
- **FR-015**: Security controls: non-root, input validation, rate-limits; restrict file I/O; no authentication (LAN-only deployment, MUST NOT be exposed to WAN); warn in README/examples
- **FR-016**: CI builds and publishes linux/amd64 only images using buildx on GitHub CPU-only runners; CI MUST NOT require GPU devices; includes frontend production build
- **FR-017**: Off-CI GPU smoke tests (manual or self-hosted runner) validate device discovery + single-frame inference per supported GPU_BACKEND

*Example of marking unclear requirements:*

- **FR-018**: [NEEDS CLARIFICATION] Exact MQTT QoS/retain defaults and topic schema details
- **FR-019**: [NEEDS CLARIFICATION] Polygon zone point limit (20? 50? unlimited?)
- **FR-020**: [NEEDS CLARIFICATION] Distance calculation method (Euclidean? Manhattan? configurable?)
- **FR-021**: [NEEDS CLARIFICATION] Which animation libraries to include by default vs. optional in frontend

### Key Entities *(include if feature involves data)*

- **Stream**: id, name, rtsp_url, enabled, threshold, zones, last_score
- **ModelConfig**: model_id (YOLO_MODEL), image_size, backend (GPU_BACKEND)
- **Score**: timestamp, stream_id, score, confidence, model_id

## Success Criteria *(mandatory)*

<!--
  ACTION REQUIRED: Define measurable success criteria.
  These must be technology-agnostic and measurable.
-->

### Measurable Outcomes

- **SC-001**: Each stream maintains <= 5 FPS processing with p95 latency <= 200ms per frame using FFmpeg decoding
- **SC-002**: Model switch completes and resumes streams in <= 5s without losing config.yml state (streams + zones)
- **SC-003**: SSE/MQTT score events deliver with < 1s end-to-end delay at p95 under 4 streams with 3 zones each
- **SC-004**: Polygon zone editor supports >= 20 points per zone with real-time visual feedback on live stream overlay
- **SC-005**: Scoring calculations (distance/coordinates/size) complete in < 10ms per detected object
- **SC-006**: CI produces amd64-only image and passes CPU-only dry-run startup (/health) with CI_DRY_RUN=true; includes React 19.2 production build
- **SC-007**: Off-CI GPU smoke test completes device discovery + single-frame inference for selected GPU backend
- **SC-008**: Frontend bundle size <= 500KB gzipped; initial page load <= 2s on 3G connection
- **SC-009**: FFmpeg version and codec support validated and logged at container startup
- **SC-010**: No video files or score history persisted to disk; memory usage stable over 24hr runtime