# Feature Specification: Hardware Accelerated FFmpeg RTSP Processing

**Feature Branch**: `004-hw-ffmpeg-rtsp-processing`  
**Created**: October 23, 2025  
**Status**: Draft  
**Input**: User description: "I want to change the backend so the rtsp streams are consumed and processed by hardware accelerated ffmpeg. then fed to the front end after being processed."

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

### User Story 1 - Configure and View Accelerated Stream (Priority: P1)

As an administrator, I want to add an RTSP stream configuration so that the backend consumes the stream using hardware acceleration, processes it efficiently, and feeds the processed video to the frontend for real-time viewing and analysis.

**Why this priority**: This is the core functionality enabling efficient stream processing, directly impacting system performance and user experience with live feeds.

**Independent Test**: Can be fully tested by adding a stream via the UI, verifying that the video displays smoothly in the frontend without lag, and confirming processing efficiency through reduced CPU usage or faster frame delivery.

**Acceptance Scenarios**:

1. **Given** a valid RTSP stream URL is provided in the UI, **When** the stream is saved and activated, **Then** the backend begins consuming the stream via RTSP, performs hardware-accelerated decoding with FFmpeg, encodes to MJPEG, serves via HTTP multipart/x-mixed-replace endpoint, and the frontend displays the feed in real-time using an <img> tag.
2. **Given** hardware acceleration is available, **When** the stream is processing, **Then** the system utilizes hardware resources for decoding, resulting in lower latency, with MJPEG frames delivered efficiently to the frontend.

---

### User Story 2 - Monitor Stream Performance (Priority: P2)

As a user, I want to view the live processed stream in the frontend so that I can monitor the video feed with object detection scoring applied, ensuring smooth playback and accurate real-time analysis.

**Why this priority**: Provides immediate value for monitoring and verification of the acceleration benefits, building on the core stream consumption.

**Independent Test**: Can be tested by accessing the stream view in the UI and confirming that frames are delivered at the target FPS with no stuttering, and scores are updated in real-time.

**Acceptance Scenarios**:

1. **Given** an active accelerated stream, **When** I navigate to the stream view page, **Then** the frontend displays the processed MJPEG video feed seamlessly via the multipart endpoint and <img> tag, with overlaid detection scores visible.
2. **Given** multiple streams are active, **When** switching between them, **Then** each stream's HTTP endpoint loads quickly without interruption to others, maintaining MJPEG frame delivery.

---

### Edge Cases

Error Responses: 400 for invalid input (e.g., bad FFmpeg params, invalid URL); 404 for non-existent stream_id; 503 for processing failures (e.g., GPU unavailable); all include JSON body `{error: "message", code: "ERR_INVALID_PARAMS"}`.
For invalid RTSP URL: Return 400 with `{error: "Invalid URL format", details: "Must be rtsp://..."}`; test via POST with malformed URL.
For MJPEG disconnection: Endpoint returns 503 after 5s timeout; client polls `/streams/{id}` for status update to 'disconnected'.
- What happens when hardware acceleration is unavailable (e.g., no compatible GPU)? The container must fail-fast with an error exit, logging the issue and returning 503 via /health.
- How does the system handle high-latency RTSP sources? It should maintain target FPS through frame skipping or buffering, ensuring the frontend receives consistent processed output.
- What if the RTSP stream disconnects mid-processing? The backend should detect the failure, stop processing, and update the stream status in the frontend.
- What if MJPEG encoding fails due to resource constraints? The system should return 503 error and stop the stream, notifying via status updates.
- What happens if user-specified FFmpeg parameters are invalid or incompatible with the detected GPU? The system should validate parameters on stream save, provide clear error messages in the UI, and reject the config without fallback.

## Requirements *(mandatory)*

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right functional requirements.
-->

### Functional Requirements

- **FR-001**: The backend must consume RTSP streams using hardware-accelerated processing to decode and prepare frames for analysis, ensuring efficient resource utilization.
  Successful POST `/streams` returns 201 with body: `{"id": "uuid", "name": "Stream1", "status": "stopped", "zones": []}`.
- **FR-002**: Processed video frames must be fed to the frontend via an HTTP multipart/x-mixed-replace endpoint using MJPEG encoding after hardware-accelerated decoding with FFmpeg, maintaining at least 5 FPS per stream for display via <img> tag and scoring overlay.
  The MJPEG endpoint uses `boundary=--myboundary` (configurable via env var MJPEG_BOUNDARY, default 'frame') and `Content-Type: image/jpeg` per frame for <img> compatibility.
  'Processed frames' in MJPEG: JPEG images (640x480, 80% quality) with embedded metadata (EXIF: timestamp, stream_id); no separate API response.
  target_fps: Integer, default 5, min 1, max 30; values outside range return 400 error.
- **FR-003**: The system must detect and utilize available hardware acceleration capabilities automatically; if hardware is unavailable, the container must fail-fast with an error exit, preventing software fallback.
  On failure, `/health` returns 503 with details: `{error: "Hardware acceleration unavailable", code: "ERR_GPU_UNAVAILABLE"}`.
- **FR-004**: Stream configurations must include options to enable hardware acceleration, validated upon saving to ensure compatibility.
- **FR-005**: Processing must include frame extraction and preparation suitable for object detection, with metrics like latency and FPS exposed via API for monitoring.
The `/metrics` endpoint must expose Prometheus-formatted metrics including stream FPS, latency, and error rates (e.g., `stream_fps{stream_id="1"} 5.2`).
- **FR-006**: Users must be able to specify custom FFmpeg parameters for RTSP decoding in the stream configuration UI. The input field should display default parameters as a placeholder, including flags like "-hide_banner", "-loglevel", "warning", "-threads", "2", "-rtsp_transport", "tcp", and a timeout parameter set to "10000000". Additionally, the defaults must incorporate GPU-specific flags based on the detected GPU backend (e.g., NVIDIA CUDA, AMD ROCm, Intel Quick Sync) as determined by entrypoint.sh.
Validation: Array must not exceed 20 strings; reject invalid flags (e.g., non-GPU if hw_accel_enabled=true) with 400 error. Defaults: `["-hide_banner", "-loglevel", "warning", "-threads", "2", "-rtsp_transport", "tcp", "-timeout", "10000000"]` plus GPU flags.
- **FR-007**: An SSE endpoint (`/streams/{stream_id}/scores`) must stream real-time detection scores (JSON: `{timestamp, scores: [{object_id, distance, coordinates, size}]}`) at 5 FPS, optional if MQTT is enabled.
- **FR-008**: Apply rate-limiting (100 req/min per IP) to non-MJPEG endpoints via middleware; exempt `/health` and `/mjpeg`.

### Success Criteria

- Users can configure and activate an RTSP stream, with the frontend displaying processed video in under 5 seconds from activation.
- Stream processing achieves at least 20% reduction in latency or CPU usage compared to non-accelerated processing, verifiable through system metrics.
- 95% of frames are processed and delivered to the frontend without errors or drops during continuous 1-hour operation.
API responses include headers (e.g., `X-Processing-Latency: 150ms`) for measuring frame delivery; `/metrics` must support querying 95% success rate over 1-hour windows.
API must handle concurrent starts (up to 4) without race conditions; use locking in backend, return 409 if over limit.
API NFRs: Health <100ms, CRUD <500ms, MJPEG frame latency <200ms; measured via response times.
- The system handles up to 4 concurrent streams with hardware acceleration, maintaining smooth frontend playback for all.

### Assumptions

- Hardware acceleration refers to GPU-based decoding (e.g., via NVIDIA or similar), but the system auto-detects and configures appropriately.
- Processing includes hardware decoding with FFmpeg, MJPEG encoding for compatibility with <img> tag via multipart/x-mixed-replace, but no changes to the inference pipeline itself.
- Frontend remains unchanged except for receiving processed streams; existing SSE for scores is leveraged.

### Key Entities *(include if feature involves data)*

Shared Status Enum: `stopped`, `starting`, `running`, `error`, `disconnected` – used across Stream responses, health details, and metrics labels.

- **Stream**: Configuration including RTSP URL, hardware acceleration flag, processing parameters (e.g., FPS limit).
- **Processed Frame**: Decoded and prepared video frame with metadata (timestamp, stream ID) for frontend delivery and scoring.
Zone points: Normalized (0-1) relative to stream resolution (e.g., x=0.5 is center); backend scales on processing. Conflict: If absolute pixels assumed, specify fallback to normalized.

## Clarifications

### Session 2025-10-23

- Q: What should the RTSP processing pipeline look like for feeding processed video to the frontend? → A: RTSP → FFmpeg hardware decode → MJPEG encode → HTTP multipart/x-mixed-replace endpoint → <img>