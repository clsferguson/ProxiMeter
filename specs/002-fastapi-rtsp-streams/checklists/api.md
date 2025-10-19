# API & Contracts Requirements Quality Checklist

Purpose: Validate quality of API/contract requirements for feature `002-fastapi-rtsp-streams` (Unit Tests for English)
Created: 2025-10-17
Focus: API & Contracts; Risk emphasis: RTSP validation & failure modes
Depth: Lightweight pre-commit sanity list

## Requirement Completeness
- [x] CHK001 Are CRUD operations for streams fully specified with methods, paths, required fields, and response codes? [Completeness, Spec §FR-015, Contract §/api/streams, §/api/streams/{id}]
- [x] CHK002 Is the reorder endpoint contract complete, including request body shape, idempotency expectations, and error cases for duplicates/missing IDs? [Completeness, Spec §FR-006 §FR-019, Contract §/api/streams/reorder (Gap)]
- [x] CHK003 Is the playback endpoint documented with content type, boundary format, and stream lifetime semantics for MJPEG? [Completeness, Spec §FR-002 §FR-011 §FR-023]
- [x] CHK004 Are error response bodies standardized (schema, fields, example) across endpoints for validation and not-found errors? [Completeness, Spec §FR-020]
- [x] CHK005 Is the health endpoint response shape (status/body) defined beyond status code? [Completeness, Spec §FR-021]
- [x] CHK006 Are validation rules for `name` (1–50 chars, unique CI) and `rtsp_url` (rtsp://, non-empty host) explicitly captured in request schema constraints and error semantics? [Completeness, Spec §FR-009 §FR-010 §FR-020, Edge Cases §Duplicate name normalization]

## Requirement Clarity
- [x] CHK007 Are all Stream fields defined with precise types and formats (e.g., `created_at` ISO8601 with timezone; `status` enum values and casing)? [Clarity, Spec §FR-009, DataModel, Contract §components/schemas/Stream]
- [x] CHK008 Is the behavior on unreachable RTSP at create/edit clearly described (save as `Inactive`, include warning indicator), including how the API surfaces this state? [Clarity, Spec §FR-022 §FR-012, DataModel]
- [x] CHK009 Is the ≤5 FPS cap defined as a server-side guarantee of visual update rate, and is its impact on the playback contract clarified? [Clarity, Spec §FR-011 §FR-023]
- [x] CHK010 Are PATCH vs PUT semantics for edit precisely defined (partial update fields, validation order, response body)? [Clarity, Spec §FR-024]
- [x] CHK011 Are request/response examples provided for key endpoints to remove ambiguity? [Clarity, Spec §FR-025]

## Requirement Consistency
- [x] CHK012 Do OpenAPI schemas align with the data model for required fields, formats, and enum values (no mismatches or missing fields)? [Consistency, DataModel vs Contract §components/schemas/Stream]
- [x] CHK013 Are status codes consistent across endpoints (e.g., 201 on create, 200 on update, 204 on delete, 404 for unknown id)? [Consistency, Contract §/api/streams §/api/streams/{id}]
- [x] CHK014 Do endpoint names and HTTP verbs align with standard REST conventions for list/create/update/delete/reorder? [Consistency, Contract]

## Acceptance Criteria Quality
- [x] CHK015 Are measurable performance targets (e.g., p95 create-to-first-frame ≤3s; list update ≤1s) mapped to API contracts or operational requirements? [Acceptance Criteria, Spec §SC-001 §SC-003]
- [x] CHK016 Can validation failures (duplicate name, bad URL) be objectively verified via defined error codes/fields/messages? [Acceptance Criteria, Spec §FR-010 §FR-020]

## Scenario Coverage
- [x] CHK017 Does the API define behavior when a stream becomes unreachable during playback (e.g., error event, status update), and how the UI discovers this? [Coverage, Spec §FR-018 §FR-012]
- [x] CHK018 Is reorder behavior defined when there are 0 or 1 streams (no-op, clear response)? [Coverage, Spec §FR-019, Edge Cases §Reorder no-op]
- [x] CHK019 Are delete semantics defined for idempotency and missing resources (e.g., 204 vs 404) independent of UI confirmation? [Coverage, Contract §/api/streams/{id}]

## Edge Case Coverage
- [x] CHK020 Are rules for duplicate names, case-insensitive comparison, and trimming specified, including error feedback structure? [Edge Case, Spec §FR-010, Edge Cases §Duplicate name normalization]
- [x] CHK021 Are credentials-in-URL handling rules and masking in responses/logs documented in the contract or requirements? [Edge Case, Spec §FR-026, Edge Cases §Credentials masking]
- [x] CHK022 Is pagination or result size behavior defined for large lists (e.g., 100 streams), or is it explicitly out of scope? [Edge Case, Edge Cases §Pagination explicitness]

## Non-Functional Requirements
- [x] CHK023 Are rate limiting or basic abuse controls for mutating routes specified (even if minimal for LAN-only)? [Non-Functional, Spec §NFR-001]
- [x] CHK024 Are reliability/atomicity expectations for YAML persistence (write ordering, crash safety) documented as requirements? [Non-Functional, Spec §NFR-002]

## Dependencies & Assumptions
- [x] CHK025 Are dependencies like FFmpeg availability and OpenCV backend assumptions captured as explicit requirements/operational preconditions? [Dependency, Plan §Technical Context]
- [x] CHK026 Is the single-file YAML storage constraint and mount path (`/app/config/config.yml`) treated as a requirement with traceability? [Dependency, Spec §FR-009, Plan §Storage]

## Ambiguities & Conflicts
- [x] CHK027 Is the delete response body defined (empty vs problem), consistent with 204 semantics? [Ambiguity, Contract §/api/streams/{id}]
- [x] CHK028 Is API versioning strategy documented or explicitly deferred out of scope to avoid future conflicts? [Ambiguity, (Gap)]
