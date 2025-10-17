# UX/UI Requirements Quality Checklist

Purpose: Validate quality of UX/UI requirements for feature `002-fastapi-rtsp-streams` (Unit Tests for English)
Created: 2025-10-17
Focus: UX/UI; Risk emphasis: RTSP validation and failure UX; FPS cap clarity
Depth: Lightweight pre-commit sanity list

## Requirement Completeness
- [x] CHK001 Are landing page elements fully enumerated (header "ProxiMeter", primary "Add stream" button, stream list area, empty state)? [Completeness, Spec §FR-001 §FR-005, Edge Cases]
- [x] CHK002 Is the Add/Edit form specified with fields, labels, constraints, error message placement, and submit/cancel controls? [Completeness, Spec §FR-002 §FR-015 §FR-010, UX Design Details §Forms]
- [x] CHK003 Is a consistent Back/Return control defined in the stream view, including its placement and label? [Completeness, Spec §FR-004, UX Design Details §Back/Return control]
- [x] CHK004 Are list item controls (drag handle, edit pencil, delete with confirm) and their visibility states specified? [Completeness, Spec §FR-006 §FR-007 §FR-015 §FR-016]

## Requirement Clarity
- [x] CHK005 Is the header animation precisely defined (start/end positions, size change 30–50%, duration 400–700 ms, easing), including landing vs playing states? [Clarity, Spec §FR-003 §FR-004 §SC-007]
- [x] CHK006 Are equal-width button requirements quantified (same row widths within ±2 px; responsive grid behavior) with breakpoints? [Clarity, Spec §FR-005 §SC-006]
- [x] CHK007 Is “no audio” explicitly stated for playback UI and not implied? [Clarity, Spec §FR-002]
- [x] CHK008 Are validation error messages for name/URL specified with clear copy and placement near fields? [Clarity, Spec §FR-010, UX Design Details §Forms]

## Requirement Consistency
- [x] CHK009 Is the product name "ProxiMeter" consistently capitalized across all UI text and documentation? [Consistency, Spec §FR-014]
- [x] CHK010 Do button/handle/icon conventions remain consistent across list items and forms (labels, icons, affordances)? [Consistency, Spec §FR-016]
- [x] CHK011 Do mobile and desktop layout requirements avoid conflicts (e.g., grid behavior vs equal width constraints)? [Consistency, Spec §FR-005 §SC-006]

## Acceptance Criteria Quality
- [x] CHK012 Are UI timing targets mapped to measurable acceptance (e.g., animation completes ≤700 ms; landing updates ≤1s; first frame ≤3s)? [Acceptance Criteria, Spec §SC-001 §SC-003 §SC-007]
- [x] CHK013 Can “equal-width buttons” be objectively verified (tolerance stated, measurement guidance)? [Acceptance Criteria, Spec §SC-006]

## Scenario Coverage
- [x] CHK014 Are empty-state requirements defined (no streams → show only "Add stream" and guidance)? [Coverage, Spec §Edge Cases]
- [x] CHK015 Are large list scenarios (e.g., 100 streams) addressed for responsiveness and scroll behavior? [Coverage, Spec §Edge Cases]
- [x] CHK016 Is the failure UX defined for mid-playback errors (banner style, messaging, link back to landing)? [Coverage, Spec §FR-012 §FR-018, Edge Cases]
- [x] CHK017 Are edit flows included (change name/URL with validations, immediate persistence, delete within edit)? [Coverage, Spec §FR-015]

## Edge Case Coverage
- [x] CHK018 Are duplicate names and invalid URLs covered with explicit UX copy and non-blocking guidance? [Edge Case, Spec §FR-010, Edge Cases]
- [x] CHK019 Is reordering disabled or clearly no-op when ≤1 stream exists, with UX treatment specified? [Edge Case, Spec §FR-019, Edge Cases]
- [x] CHK020 Is delete confirmation interaction detailed (modal/dialog copy, confirm/cancel, focus behavior)? [Edge Case, Spec §FR-007]

## Non-Functional Requirements
- [x] CHK021 Are accessibility considerations defined (keyboard focus order, draggable handle keyboard alternative, contrast, ARIA roles)? [Non-Functional, Spec §UX Design Details §Accessibility]
- [x] CHK022 Are performance considerations for UI specified (no jank during animations; list rendering performance for large sets)? [Non-Functional, Spec §SC-006 §SC-007]

## Dependencies & Assumptions
- [x] CHK023 Are assumptions about browser support (CSS grid, transitions) documented or scoped? [Assumption, Research §Header animation, Research §Equal-width stream buttons]
- [x] CHK024 Is the LAN-only/no-auth posture reflected in UX (e.g., security warning about plaintext credentials)? [Assumption, Spec §UX Design Details §Forms, Quickstart Notes]

## Ambiguities & Conflicts
- [x] CHK025 Is the navigation behavior for legacy routes (redirect vs 404) reflected in UI copy and consistent across pages? [Ambiguity, Spec §FR-008, UX Design Details §Back/Return control]
- [x] CHK026 Are icon choices (hamburger handle, pencil) standardized to avoid confusion and documented? [Ambiguity, Spec §FR-016]