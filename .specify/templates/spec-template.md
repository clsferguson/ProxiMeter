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

- **FR-001**: Run exclusively in Docker on linux/amd64; include HEALTHCHECK /health
- **FR-002**: Load a single YOLO model specified by YOLO_MODEL and IMAGE_SIZE; export to ONNX on startup
- **FR-003**: Manage multiple RTSP streams with CRUD via web UI; validate at save
- **FR-004**: Enforce max 5 FPS per stream using frame skipping/backpressure
- **FR-005**: Provide Flask-based UI (app factory) and REST APIs via Blueprints
- **FR-006**: Optional MQTT publishing of per-stream scores with required schema
- **FR-007**: Optional HTTP score streaming (SSE or WebSocket) at HTTP_STREAM_PATH
- **FR-008**: Provide GET endpoint for latest score snapshot per stream
- **FR-009**: Persist only /app/config/config.yml; no model caches or artifacts persisted
- **FR-010**: GPU backend provisioning via entrypoint.sh; fail fast on errors; print versions; support CI dry-run via `CI_DRY_RUN=true` to skip device access on CPU-only runners
- **FR-011**: Structured JSON logging; Prometheus metrics for FPS, latency, queues, GPU utilization
- **FR-012**: Security controls: non-root, input validation, rate-limits; restrict file I/O; no authentication (LAN-only deployment, MUST NOT be exposed to WAN); warn in README/examples
- **FR-013**: CI builds and publishes linux/amd64 only images using buildx on GitHub CPU-only runners; CI MUST NOT require GPU devices
- **FR-016**: Off-CI GPU smoke tests (manual or self-hosted runner) validate device discovery + single-frame inference per supported GPU_BACKEND

*Example of marking unclear requirements:*

- **FR-014**: [NEEDS CLARIFICATION] Exact MQTT QoS/retain defaults and topic schema details
- **FR-015**: [NEEDS CLARIFICATION] SSE vs WebSocket transport selection criteria and reconnection behavior

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

- **SC-001**: Each stream maintains <= 5 FPS processing with p95 latency <= 200ms per frame
- **SC-002**: Model switch completes and resumes streams in <= 5s without losing config.yml state
- **SC-003**: MQTT/HTTP outputs deliver scores with < 1s end-to-end delay at p95 under 4 streams
- **SC-004**: CI produces amd64-only image and passes CPU-only dry-run startup (/health) with CI_DRY_RUN=true
- **SC-005**: Off-CI GPU smoke test completes device discovery + single-frame inference for selected GPU backend