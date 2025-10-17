# Feature Specification: FastAPI RTSP Streams and Landing UI

**Feature Branch**: `002-fastapi-rtsp-streams`  
**Created**: 2025-10-17  
**Status**: Draft  
**Input**: User description: "I want to add the rtsp system, Remove the counter app functionality, set up the landing page with a simple \"add stream\" button. change hello to a header that says \"ProxiMeter\"\n\nWhen \"add stream\" is pressed, it opens a form to enter a rtsp stream. Which the user will also name. Then when that is entered, it moves to a page that shows the stream running. capped at 5fps. no audio necessary. The config.yml will store a list of streams now. There should be a way to return to the landing page. Lets add a cool animated proximeter thing, so the ProxiMeter header animates and moves to the top and minimalizes itself a little when a stream is entered.\n\nwhen moving back to the landing page, animate the ProxiMeter back, then it will show a list of availible running streams, with a delete and confirm function. to remove them from the config.yml. Streams should be able to be reordered too. maybe have a draggable hambuger button in line.\n\nall stream buttons should be the same width not nice formatting.\n\n I want to move to fastapi from flask."

## User Scenarios & Testing (mandatory)

### User Story 1 - Add and View a Stream (Priority: P1)

As a user on the landing page, I can press "Add stream", enter a Name and RTSP URL, submit, and be taken to a page where the video stream plays at up to 5 frames per second with no audio. The header text "ProxiMeter" animates to the top and reduces size on entering the stream view.

**Why this priority**: Core value is adding and viewing a stream; everything else depends on this.

**Independent Test**: From a clean state, add one valid RTSP stream and verify playback starts at ≤5 FPS with no audio and header animation occurs.

**Acceptance Scenarios**:

1. Given the landing page, When I click "Add stream" and provide a unique Name and a valid RTSP URL, Then I am navigated to the stream view and see video updating at ≤5 FPS without audio.
2. Given the stream view, When the stream fails mid-playback, Then a user-friendly error banner appears and the page offers a link to return to the landing page.

---

### User Story 2 - Manage Streams on Landing (Priority: P2)

As a user, when I return to the landing page I see a list of saved streams (by Name) as equal-width buttons. I can start any stream by clicking its button, delete a stream with a confirmation step, and reorder streams with a draggable handle. The "ProxiMeter" header animates back to its original centered position on return.

**Why this priority**: Enables ongoing use: selection, organization, and cleanup of streams.

**Independent Test**: With multiple saved streams, verify equal-width layout, drag-and-drop reordering persists, and delete requires explicit confirmation.

**Acceptance Scenarios**:

1. Given multiple saved streams, When I drag a stream using its handle to a new position, Then the new order is saved and reflected after a refresh.
2. Given a saved stream, When I choose delete, Then I must confirm before it is removed and the list updates immediately.

---

### User Story 3 - Replace Legacy Counter App and Update Header (Priority: P3)

As a user, I no longer see the previous counter functionality. The landing page shows only the "Add stream" primary action and the header reads "ProxiMeter" with the described animations.

**Why this priority**: Removes obsolete functionality and unifies the new experience.

**Independent Test**: Verify no counter routes or UI elements are accessible; header text and animations behave as specified.

**Acceptance Scenarios**:

1. Given any prior counter route, When I navigate to it, Then it responds with a not found or redirects to the landing page.
2. Given the landing page, When viewed on desktop and mobile widths, Then the "ProxiMeter" header and equal-width stream buttons render correctly.

---

### Edge Cases

- Invalid RTSP URL format at save time → block save with inline validation message.
- RTSP URL requires credentials → allow username:password in URL; store plaintext in config.yml with a clear security warning in UI and docs.
- Duplicate stream names → disallow and prompt to choose a unique name.
- Unreachable stream on save → validate connectivity on save; if unreachable, allow saving as Inactive with status indicated in list and offer retry.
- Deleting the last stream → landing shows empty state with only "Add stream" button.
- Reordering when only one or zero streams exist → reorder handle disabled.
- Large list (e.g., 100 streams) → landing remains responsive; scrolling allowed; layout stays equal-width.
- Mid-playback failure behavior → backend terminates the MJPEG stream gracefully and updates the stream `status` to `Inactive`; the UI must present a clear error banner with a link back to the landing page. The status change persists to `config.yml` and will be reflected on the landing list. [Coverage]
- Reorder API behavior with ≤1 streams → server accepts reorder requests but performs a no-op and returns success; order remains unchanged. [Coverage]
- Duplicate name normalization → server trims leading/trailing whitespace and compares names case-insensitively when enforcing uniqueness; error copy instructs to choose a unique name. [Clarity]
- Credentials masking → when returning `rtsp_url` in API responses or logs, username/password are masked (e.g., `rtsp://***:***@host/...`). Stored value in `config.yml` remains plaintext as documented. [Security]
- Pagination explicitness → list endpoints return the full set of streams; pagination is out of scope for this feature. [Clarity]

## Requirements (mandatory)

### Functional Requirements

- FR-001: Provide a landing page with a prominent "Add stream" button and a "ProxiMeter" header positioned in the upper portion of the viewport (above the vertical midpoint).
- FR-002: On submitting the Add Stream form (fields: Name, RTSP URL), navigate to the stream view and begin playback of the specified stream with a hard cap of 5 frames per second; audio must be disabled.
- FR-003: The header "ProxiMeter" animates on entering the stream view: moves to the top-left and reduces size by ~30–50%, completing within 400–700 ms using an ease transition.
- FR-004: Provide a visible control to return from the stream view to the landing page; when returning, animate the header back toward its higher landing-page position and original size within 400–700 ms.
- FR-005: The landing page lists all saved streams as equal-width buttons in a responsive grid or list; buttons in the same row must have equal widths within ±2 px.
- FR-006: Each listed stream has a drag handle (hamburger) to reorder; drag-and-drop reordering updates the stored order and persists across reloads and restarts.
- FR-007: Each listed stream has a Delete action that requires explicit confirmation before removal; upon confirm, remove from storage and update the list immediately.
- FR-008: Remove all legacy counter app functionality entirely from the UI and routes; legacy routes must return not found or redirect to the landing page. The feature was a placeholder only.
- FR-009: Store streams in a configuration file at `config/config.yml` containing an ordered list of streams with fields: `id` (UUID), `name` (unique, 1–50 chars), `rtsp_url` (validated), `created_at` (ISO8601), `order` (integer for sorting), and `status` (Active | Inactive).
- FR-010: RTSP URL validation must, at minimum, enforce `rtsp://` scheme and non-empty host; names must be unique case-insensitively; show inline error messages on invalid input.
- FR-011: Playback must not exceed 5 FPS per stream; if source is higher FPS, frames are skipped or throttled so that visible updates do not exceed 5 per second.
- FR-012: When a stream cannot be played (initially or during playback), display a clear error state with guidance to retry or return to the landing page; errors must not crash the application.
- FR-013: Migrate from Flask to FastAPI; the application must run on FastAPI supporting the specified UX flows.
- FR-014: All UI text uses the product name "ProxiMeter" exactly as capitalized here.
- FR-015: Provide an Edit Stream function accessible via an edit (pencil) control on each stream list item. The edit form allows changing Name and RTSP URL with the same validations; it also provides Delete with confirmation. Changes persist immediately and update the list.
- FR-016: Stream list items display primarily the stream Name, with an inline move (hamburger) handle and an edit pencil control; visual layout keeps action targets accessible and consistent.
- FR-017: Update the README to reflect current functionality (RTSP streams, landing UI, removal of counter), basic usage, and security warning about plaintext credentials in config.
- FR-018: On runtime playback failures, the system updates the affected stream's `status` to `Inactive` and ensures the UI can detect the failure within the session (e.g., via stream termination and error banner) without crashing the application. The status update is persisted. [Extends FR-012]
- FR-019: The reorder operation is idempotent and safe when the submitted order is identical or when there are ≤1 streams; the API returns success and makes no changes. Invalid orders (missing/duplicate IDs) are rejected with a clear validation error. [Clarifies FR-006]
- FR-020: Standardize error responses across endpoints with JSON shape `{ code: string, message: string, details?: object }`; use domain codes such as `INVALID_RTSP_URL`, `DUPLICATE_NAME`, `INVALID_ORDER`, `NOT_FOUND`. Include examples in API docs.
- FR-021: Health endpoint responds `200` with JSON body `{ status: "ok" }` and no dynamic fields; used for container HEALTHCHECK.
- FR-022: Create/Edit semantics when RTSP is unreachable: the resource is saved with `status=Inactive`; response body includes the current `status` and an advisory message in `details` explaining connectivity could not be confirmed.
- FR-023: Playback endpoint guarantees server-side visual update rate ≤5 FPS. Response uses `Content-Type: multipart/x-mixed-replace; boundary=frame` with each part `Content-Type: image/jpeg`. Connection ends gracefully on error or stop; appropriate cache-control headers are sent.
- FR-024: Edit uses `PATCH /api/streams/{id}` with partial fields `name`, `rtsp_url`; unchanged fields are not required and remain intact. Response returns the updated resource. Validation order: input → uniqueness/format → optional probe → persist.
- FR-025: Provide request/response examples in the API documentation for Create, Edit, Delete, Reorder, List, and Playback endpoints, including error examples for common failures.
- FR-026: In API responses, any `rtsp_url` values must mask embedded credentials (username/password) while preserving host/path for operability documentation.

### UX Design Details

- Forms (Add/Edit)
	- Fields: "Name" (required, 1–50 chars) and "RTSP URL" (required, must start with rtsp:// and include non-empty host)
	- Labels: Visible labels above inputs; required fields marked with an asterisk
	- Error messages: Inline, placed directly beneath the field in error, concise copy: 
		- Name: "Enter 1–50 characters."; on duplicate (case-insensitive, trimmed): "Choose a unique name."
		- RTSP URL: "Enter a valid RTSP URL (rtsp://host/...)."
	- Controls: Primary "Save" (Add: "Add stream"; Edit: "Save changes"), secondary "Cancel" returning to landing without saving
	- Security notice: Below RTSP URL input, display: "Security note: RTSP URLs with credentials are stored in plaintext in config/config.yml. Use on trusted LAN only. Do not expose to WAN."

- Back/Return control (Stream view)
	- Placement: Top-left persistent button labeled "Back to streams"
	- Behavior: Always visible; returns to landing; keyboard accessible (Tab focusable)

- Delete confirmation (List/Edit)
	- Modal dialog with title "Delete stream?"
	- Body: "Are you sure you want to delete ‘<Name>’? This cannot be undone."
	- Buttons: Destructive primary "Delete", secondary "Cancel"
	- Focus: Dialog traps focus; Esc cancels; on close, focus returns to the Delete trigger; Enter confirms only when the Delete button is focused

- Accessibility
	- Focus order: Header → primary action → stream list → footer; visible focus outlines
	- Reorder via keyboard: Drag handle supports keyboard — Space to pick up, Arrow Up/Down to move, Enter to drop; announce new position via ARIA live region (e.g., "Moved ProxiCam to position 2")
	- Roles/labels: List has role="list"; items role="listitem"; drag handle aria-label="Drag to reorder"; icons have aria-labels
	- Contrast: Meet WCAG 2.1 AA for text and interactive elements

- Failure banner (Playback)
	- Display a top-of-content error banner with message and a link "Back to streams"; banner does not block navigation

### Key Entities (include if feature involves data)

- Stream: id (UUID), name (string), rtsp_url (string), created_at (datetime), order (int), status (Active | Inactive)

## Success Criteria (mandatory)

### Measurable Outcomes

- SC-001: A user can add a valid stream and see video start within 3 seconds (p95) from submitting the form.
- SC-002: During playback, visual updates do not exceed 5 frames per second; p95 inter-frame interval is ≥180 ms.
- SC-003: Returning to the landing page shows the updated stream list in under 1 second (p95) with the current order persisted.
- SC-004: Deleting a stream always requires a confirmation interaction and removes it from the list and storage within 1 second (p95).
- SC-005: Reordering by drag-and-drop updates the order and persists across page reloads and application restarts.
- SC-006: On desktop widths ≥1024 px, stream buttons in the same row differ in width by no more than 2 pixels.
- SC-007: Header animations complete within 700 ms and do not block user input.
- SC-008: Editing a stream’s details updates storage and the landing list within 1 second (p95), with validations enforced and confirmation required for delete.

## Non-Functional Requirements

- NFR-001: Apply lightweight rate limiting to mutating routes (e.g., per-client 5 requests/second burst 10) to guard against accidental abuse on LAN.
- NFR-002: YAML persistence uses atomic writes (write to temp file then rename) to avoid partial writes and ensures ordering is preserved across crashes.