# Feature Specification: Frontend React Migration

**Feature Branch**: `003-frontend-react-migration`  
**Created**: October 19, 2025  
**Status**: Draft  
**Input**: User description: "I want to change the front end from a static site to react-typescript 19.2."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - View Stream Dashboard (Priority: P1)

As a system administrator, I can view the main dashboard showing all configured RTSP streams and their current status.

**Why this priority**: This is the primary entry point for managing streams and monitoring the system.

**Independent Test**: Can be fully tested by loading the dashboard and verifying stream list display and status indicators.

**Acceptance Scenarios**:

1. **Given** streams are configured in config.yml, **When** I navigate to the root URL, **Then** I see a list of all streams with their names, URLs, and enabled status
2. **Given** a stream is processing frames, **When** I view the dashboard, **Then** I see real-time status indicators (FPS, last activity) updating every 2 seconds with visual feedback (green=active, yellow=degraded, red=failed)
3. **Given** no streams are configured, **When** I view the dashboard, **Then** I see an empty state with centered message "No streams configured" and a prominent "Add First Stream" button

**UI Specifications**:
- Status indicators: Badge with colored dot (green/yellow/red) + text label showing FPS and timestamp
- Stream list: Card layout with stream name (truncated at 40 chars with ellipsis), URL (masked, show last 20 chars), enabled toggle
- Navigation: Top app bar with "ProxiMeter" title and "Add Stream" button (top-right)

---

### User Story 2 - Add New Stream (Priority: P1)

As a system administrator, I can add a new RTSP stream through a form interface.

**Why this priority**: Core functionality for setting up new streams.

**Independent Test**: Can be fully tested by submitting the add stream form and verifying the stream appears in the dashboard.

**Acceptance Scenarios**:

1. **Given** I am on the dashboard, **When** I click "Add Stream", **Then** I see a form with fields for name, RTSP URL, and threshold
2. **Given** I enter valid stream details, **When** I submit the form, **Then** the stream is saved to config.yml and appears in the dashboard
3. **Given** I enter invalid RTSP URL, **When** I submit, **Then** I see validation error "Invalid RTSP URL format. Expected rtsp://..." in red text below the field

**Form Field Specifications**:
- **Name field**: Label "Stream Name", placeholder "e.g., Front Door Camera", max 100 chars, required, error: "Stream name is required"
- **RTSP URL field**: Label "RTSP URL", placeholder "rtsp://username:password@host:port/path", required, pattern validation for rtsp:// prefix, error: "Invalid RTSP URL format. Expected rtsp://..."
- **Threshold field**: Label "Detection Threshold", placeholder "0.5", type number, min 0, max 1, step 0.1, default 0.5, error: "Threshold must be between 0 and 1"
- **Submit button**: Primary blue button labeled "Add Stream", disabled during submission with loading spinner
- **Cancel button**: Secondary gray button labeled "Cancel", returns to dashboard

---

### User Story 3 - Edit Existing Stream (Priority: P2)

As a system administrator, I can modify existing stream configuration.

**Why this priority**: Important for maintaining stream settings.

**Independent Test**: Can be fully tested by editing a stream and verifying changes persist.

**Acceptance Scenarios**:

1. **Given** a stream exists, **When** I select edit from the dashboard, **Then** I see the edit form pre-populated with current values
2. **Given** I modify stream settings, **When** I save changes, **Then** the config.yml is updated and dashboard reflects changes

**Form Field Specifications**:
- Uses same field specifications as Add Stream form (see User Story 2)
- Form pre-populates with existing stream values
- Submit button labeled "Save Changes" instead of "Add Stream"
- Additional "Delete Stream" button in red with confirmation dialog: "Are you sure you want to delete this stream? This action cannot be undone."

---

### User Story 4 - Play Live Stream (Priority: P2)

As a system administrator, I can view a live RTSP stream in the browser.

**Why this priority**: Core functionality for monitoring live video feeds.

**Independent Test**: Can be fully tested by selecting a stream and verifying live video playback.

**Acceptance Scenarios**:

1. **Given** a stream is configured, **When** I select "Play" from dashboard, **Then** I see live video playback in the browser
2. **Given** the RTSP stream is available, **When** I load the play view, **Then** video starts playing automatically
3. **Given** the RTSP stream becomes unavailable, **When** I view the play page, **Then** I see error message "Stream unavailable: Unable to connect to RTSP source. Please check the stream configuration." with red alert icon

**Video Player Specifications**:
- HTML5 video element with controls: play/pause, volume, fullscreen
- Video container: 16:9 aspect ratio, max-width 1280px, centered
- Loading state: Spinner with text "Loading stream..." overlaid on video container
- Error states:
  - Stream unavailable: Red alert box with message and "Back to Dashboard" button
  - Unsupported codec: "Video codec not supported by your browser. Try a different browser or contact administrator."
  - Network error: "Network error: Unable to load stream. Check your connection and try again."
- Auto-play on load with muted audio (unmute via controls)
- Back button: Top-left arrow icon returning to dashboard

---

### Edge Cases

- **RTSP stream unreachable during playback**: Display error message as specified in User Story 4 video player specs
- **Very long stream names or URLs**: Truncate stream names at 40 chars with ellipsis tooltip on hover; URLs masked to show last 20 chars
- **Multiple concurrent users**: No special handling required (stateless frontend, backend handles concurrency)
- **Backend restart or network issues**: Show loading spinner during reconnection attempts; after 10 seconds show error: "Unable to connect to server. Please check your connection and refresh the page."
- **Unsupported video codec**: Display codec error message as specified in User Story 4 video player specs
- **Backend unreachable on initial load**: Display centered error message: "Cannot connect to ProxiMeter backend. Please ensure the service is running." with "Retry" button

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Replace static HTML/CSS/JS frontend with React 19.2 TypeScript 5+ SPA built with Vite
- **FR-002**: Migrate all existing pages (index, add_stream, edit_stream, play) to React components with routing
- **FR-003**: Preserve existing visual design and layout from src/templates/*.html while modernizing implementation with React component architecture, TypeScript patterns, and optional animation libraries
- **FR-004**: Implement REST API integration for stream CRUD operations using fetch or axios (axios preferred for interceptors and error handling)
- **FR-005**: Use TypeScript strict mode for all components and utilities
**FR-016**: Handle API timeouts with 10-second limit before showing error message
**FR-017**: Implement consistent error response handling across all API calls (parse detail field from ErrorResponse schema)
**FR-006**: Configure Vite for production builds with proper asset handling, including Tailwind CSS 4.1 integration via `@tailwindcss/vite`
**FR-007**: Optionally integrate animation libraries (framer-motion, react-bits, aceternity UI, motion-bits) for enhanced UX
**FR-008**: Ensure responsive design works on desktop and mobile devices with touch-friendly controls (minimum 44x44px touch targets)
**FR-009**: Implement proper error handling and loading states for all API calls (see user stories for specific error messages)
**FR-010**: Add form validation for stream configuration inputs (see User Story 2 for validation rules)
**FR-011**: Support live video streaming display using HTML5 video element with standard controls
**FR-012**: Display real-time stream status and metrics in the UI (update every 2 seconds)
**FR-013**: Implement consistent navigation patterns across all views (app bar with back navigation where appropriate)
**FR-014**: Ensure consistent button styling and interaction patterns using Tailwind CSS utility classes and shadcn/ui component variants (primary actions, secondary, destructive)
**FR-015**: Handle all error scenarios with user-friendly messages (see specific error messages in user stories)

### Key Entities *(include if feature involves data)*

- **Stream**: id, name, rtsp_url, enabled, threshold

### API Integration Requirements

**Contract Reference**: specs/003-frontend-react-migration/contracts/openapi.yaml

**Endpoints**:
- `GET /api/streams` - List all streams (returns StreamResponse[])
- `POST /api/streams` - Create stream (request: NewStreamRequest, response: StreamResponse)
- `PATCH /api/streams/{streamId}` - Update stream (request: EditStreamRequest, response: StreamResponse)
- `DELETE /api/streams/{streamId}` - Delete stream (response: 204 No Content)
- `GET /api/streams/play/{streamId}.mjpg` - MJPEG stream playback (response: multipart/x-mixed-replace)

**Error Handling**:
- All errors return ErrorResponse with `detail` field containing message
- HTTP 400: Validation errors (display detail to user in red text)
- HTTP 404: Resource not found (redirect to dashboard with toast notification)
- HTTP 500: Server errors (display generic "Server error occurred" message)
- Network errors: Display "Unable to connect to server" with Retry button

**Request/Response Patterns**:
- All JSON requests use `Content-Type: application/json`
- All responses (except MJPEG) return `Content-Type: application/json`
- Stream credentials are masked in all responses
- Loading states shown during all API calls
- Form submissions disable button and show spinner until response

**Retry & Timeout**:
- API timeout: 10 seconds for all requests except MJPEG playback
- No automatic retry (user must click Retry button)
- MJPEG stream has no timeout (continuous streaming)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Frontend loads initial dashboard in under 2 seconds on standard broadband connection
- **SC-002**: All existing static page functionality is preserved in React components (dashboard, add/edit/play views)
- **SC-003**: Production build bundle size is under 500KB gzipped
- **SC-004**: TypeScript compilation passes with strict mode enabled and zero type errors
- **SC-005**: Form validation prevents invalid RTSP URLs and required field omissions
- **SC-006**: Video playback starts within 3 seconds of loading play page
- **SC-007**: Responsive design works correctly on screens 768px and wider
- **SC-008**: No JavaScript console errors in production build during normal operation

## Assumptions

- Existing backend API endpoints remain unchanged (validated: endpoints documented in specs/002-fastapi-rtsp-streams/contracts/openapi.yaml)
- UI/UX design should match current static site appearance (see src/templates/*.html for reference) while adopting Tailwind CSS 4 + shadcn/ui primitives
- All current functionality must be preserved (stream CRUD and live viewing only)
- Zones and scoring features are future enhancements, not part of this migration
- Animation libraries are optional enhancements, not requirements
- Target browsers: modern Chrome, Firefox, Safari, Edge (latest 2 versions)
- Application runs in trusted LAN environment (no additional authentication required beyond current implementation)
- Multiple concurrent users are supported by backend; frontend is stateless with no shared session state

## Dependencies

- Backend REST API must be available for stream CRUD operations
- Config.yml persistence for streams