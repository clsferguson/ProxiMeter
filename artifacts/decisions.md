# ProxiMeter Technical Decisions

## Feature: FastAPI RTSP Streams and Landing UI

**Date**: 2025-10-17  
**Branch**: 002-fastapi-rtsp-streams  
**Spec**: `specs/002-fastapi-rtsp-streams/spec.md`

---

## Architecture Decisions

### ADR-001: FastAPI Migration from Flask

**Status**: Accepted  
**Date**: 2025-10-17

**Context**:
The original Flask-based counter application needed to be replaced with an RTSP stream management system. The new feature requires:
- Server-side RTSP decoding and MJPEG streaming
- Real-time video frame generation (async-friendly)
- Modern API patterns (REST + OpenAPI)
- Better async support for concurrent stream handling

**Decision**:
Migrate from Flask (WSGI) to FastAPI (ASGI) with Uvicorn as the server.

**Rationale**:
1. **Async Support**: FastAPI's native async/await support is ideal for streaming video frames
2. **Performance**: ASGI provides better concurrency for multiple simultaneous stream viewers
3. **OpenAPI**: Built-in OpenAPI schema generation and validation
4. **Modern Patterns**: Pydantic v2 for data validation, dependency injection
5. **Streaming**: Better support for streaming responses (MJPEG multipart)

**Consequences**:
- ✅ Better performance for concurrent playback sessions
- ✅ Automatic API documentation (though disabled for LAN-only deployment)
- ✅ Type-safe request/response handling with Pydantic
- ⚠️ Breaking change: All Flask routes removed
- ⚠️ Requires Uvicorn instead of Gunicorn (or Gunicorn with uvicorn.workers)

**Alternatives Considered**:
- **Flask + Flask-SocketIO**: Rejected due to complexity and WebSocket overhead
- **Django**: Rejected as too heavyweight for this use case
- **Starlette only**: Rejected in favor of FastAPI's higher-level abstractions

---

### ADR-002: MJPEG over HTTP for Video Streaming

**Status**: Accepted  
**Date**: 2025-10-17

**Context**:
Need to stream RTSP video to web browsers. Options include:
- MJPEG over HTTP (multipart/x-mixed-replace)
- HLS (HTTP Live Streaming)
- WebRTC
- Server-Sent Events with base64 frames

**Decision**:
Use MJPEG over HTTP with multipart/x-mixed-replace boundary.

**Rationale**:
1. **Simplicity**: No client-side JavaScript required for playback (native `<img>` tag)
2. **Browser Support**: Universal support in all modern browsers
3. **Low Latency**: Direct frame streaming without segmentation
4. **Server-Side Control**: Easy to enforce ≤5 FPS cap server-side
5. **No Transcoding**: Direct JPEG encoding from OpenCV frames

**Consequences**:
- ✅ Simple implementation (no HLS manifest generation)
- ✅ Low latency (no segment buffering)
- ✅ Easy FPS throttling (time.sleep between frames)
- ⚠️ Higher bandwidth than H.264 (JPEG per frame)
- ⚠️ No audio support (acceptable per spec)

**Alternatives Considered**:
- **HLS**: Rejected due to complexity (manifest generation, segmentation) and higher latency
- **WebRTC**: Rejected due to complexity and signaling requirements
- **Base64 in SSE**: Rejected due to encoding overhead and complexity

---

### ADR-003: YAML File Persistence

**Status**: Accepted  
**Date**: 2025-10-17

**Context**:
Need to persist stream configuration (name, RTSP URL, order). Options:
- YAML file
- JSON file
- SQLite database
- PostgreSQL/MySQL

**Decision**:
Use single YAML file at `/app/config/config.yml` with atomic writes.

**Rationale**:
1. **Simplicity**: No database setup or migrations
2. **Human-Readable**: Easy to inspect and edit manually
3. **Volume Mount**: Simple Docker volume for persistence
4. **Atomic Writes**: Temp file + rename for crash safety
5. **Constitution Compliance**: Matches existing pattern from counter feature

**Consequences**:
- ✅ Simple deployment (no database container)
- ✅ Easy backup (single file)
- ✅ Human-readable configuration
- ⚠️ Not suitable for high-concurrency writes (acceptable for LAN-only)
- ⚠️ No query optimization (acceptable for ~100 streams)

**Implementation Details**:
- Atomic write pattern: write to temp file, then rename
- Normalize `order` field to be contiguous (0, 1, 2, ...)
- Thread lock for concurrent access safety
- CI_DRY_RUN mode uses in-memory storage

**Alternatives Considered**:
- **SQLite**: Rejected as overkill for simple list storage
- **JSON**: Rejected in favor of YAML's readability
- **PostgreSQL**: Rejected as too heavyweight for LAN-only deployment

---

### ADR-004: Server-Side RTSP Decoding with OpenCV

**Status**: Accepted  
**Date**: 2025-10-17

**Context**:
Need to decode RTSP streams and serve to browsers. Options:
- Server-side decode (OpenCV + FFmpeg)
- Client-side decode (WebRTC, HLS.js)
- Proxy RTSP directly to browser

**Decision**:
Decode RTSP server-side using OpenCV (opencv-python-headless) with FFmpeg backend.

**Rationale**:
1. **Browser Compatibility**: Browsers don't support RTSP natively
2. **FPS Control**: Easy to enforce ≤5 FPS cap server-side
3. **Format Conversion**: Convert RTSP to browser-friendly MJPEG
4. **Centralized Processing**: Single decode per stream (multiple viewers share)
5. **No Client Dependencies**: No JavaScript libraries required

**Consequences**:
- ✅ Universal browser support (no plugins)
- ✅ Server-side FPS throttling
- ✅ No client-side decoding overhead
- ⚠️ Server CPU usage scales with active streams
- ⚠️ Requires FFmpeg in container

**Implementation Details**:
- Use `cv2.VideoCapture(rtsp_url)` for decoding
- Throttle to ≤5 FPS with `time.sleep(0.2)` between frames
- Encode frames as JPEG with `cv2.imencode('.jpg', frame)`
- Stream as multipart/x-mixed-replace

**Alternatives Considered**:
- **Client-side HLS.js**: Rejected due to transcoding complexity
- **WebRTC**: Rejected due to signaling complexity
- **Direct RTSP proxy**: Rejected due to lack of browser support

---

### ADR-005: Pydantic v2 for Data Validation

**Status**: Accepted  
**Date**: 2025-10-17

**Context**:
Need to validate stream data (name, RTSP URL) and API requests.

**Decision**:
Use Pydantic v2 for all data models and validation.

**Rationale**:
1. **FastAPI Integration**: Native support in FastAPI
2. **Type Safety**: Runtime validation with Python type hints
3. **Performance**: Pydantic v2 is significantly faster than v1
4. **Error Messages**: Clear validation error messages
5. **Serialization**: Automatic JSON serialization/deserialization

**Consequences**:
- ✅ Type-safe API contracts
- ✅ Automatic request validation
- ✅ Clear error messages for invalid input
- ✅ OpenAPI schema generation

**Models Defined**:
- `Stream`: Full stream object (id, name, rtsp_url, created_at, order, status)
- `NewStream`: Create request (name, rtsp_url)
- `EditStream`: Update request (optional name, rtsp_url)

---

### ADR-006: Rate Limiting Middleware

**Status**: Accepted  
**Date**: 2025-10-17

**Context**:
LAN-only deployment with no authentication. Need basic abuse protection.

**Decision**:
Implement lightweight rate limiting middleware (5 req/s, burst 10) on mutating routes.

**Rationale**:
1. **Constitution Requirement**: NFR-001 requires rate limiting
2. **Abuse Prevention**: Prevent accidental or malicious spam
3. **Simplicity**: In-memory token bucket (no Redis)
4. **LAN-Appropriate**: Lenient limits for trusted network

**Consequences**:
- ✅ Basic protection against abuse
- ✅ No external dependencies (in-memory)
- ⚠️ Limits reset on container restart
- ⚠️ Per-client tracking by IP (not suitable for NAT)

**Implementation**:
- Token bucket algorithm
- 5 requests/second sustained rate
- Burst capacity of 10 requests
- Applied to POST/PATCH/DELETE routes

---

### ADR-007: Credential Masking in Responses

**Status**: Accepted  
**Date**: 2025-10-17

**Context**:
RTSP URLs often contain credentials (e.g., `rtsp://user:pass@host/path`). Need to prevent credential leakage in API responses and logs.

**Decision**:
Mask credentials in all API responses and log messages.

**Rationale**:
1. **Security**: Prevent credential exposure in browser dev tools
2. **Logging**: Prevent credentials in log aggregation systems
3. **Spec Requirement**: FR-026 requires credential masking

**Consequences**:
- ✅ Credentials not visible in API responses
- ✅ Credentials redacted from logs
- ⚠️ Stored in plaintext in YAML (acceptable per LAN-only posture)

**Implementation**:
- Regex pattern: `rtsp://([^:]+):([^@]+)@` → `rtsp://***:***@`
- Applied in API serialization and logging formatter
- Plaintext storage in config.yml (LAN-only, no encryption)

---

### ADR-008: Prometheus Metrics Exposition

**Status**: Accepted  
**Date**: 2025-10-17

**Context**:
Need observability for stream operations and playback performance.

**Decision**:
Expose Prometheus metrics at `/metrics` endpoint.

**Rationale**:
1. **Constitution Requirement**: Observability required
2. **Standard Format**: Prometheus is industry standard
3. **Grafana Integration**: Easy to visualize in Grafana
4. **Low Overhead**: Minimal performance impact

**Metrics Exposed**:
- `http_requests_total`: HTTP request counter (method, endpoint, status)
- `streams_created_total`: Stream creation counter
- `streams_deleted_total`: Stream deletion counter
- `streams_reordered_total`: Reorder operation counter
- `active_playback_sessions`: Active MJPEG session gauge
- `playback_frames_total`: Frame counter (stream_id label)
- `playback_fps_current`: Current FPS gauge (stream_id label)

**Consequences**:
- ✅ Operational visibility
- ✅ Performance monitoring
- ✅ Grafana dashboard support
- ⚠️ Metrics endpoint publicly accessible (LAN-only acceptable)

---

### ADR-009: Non-Root Container User

**Status**: Accepted  
**Date**: 2025-10-17

**Context**:
Security best practice to avoid running containers as root.

**Decision**:
Run container as non-root user `appuser` (UID 10001).

**Rationale**:
1. **Security**: Limit blast radius of container escape
2. **Best Practice**: Industry standard for production containers
3. **Constitution Requirement**: Security posture

**Consequences**:
- ✅ Improved security posture
- ✅ Compliance with security best practices
- ⚠️ File permissions must be set correctly

**Implementation**:
- Create user in Dockerfile: `useradd -m -u 10001 appuser`
- Set ownership: `chown -R appuser:appuser /app`
- Switch user: `USER appuser`

---

### ADR-010: Entrypoint Script for Version Emission

**Status**: Accepted  
**Date**: 2025-10-17

**Context**:
Need to emit version information on startup and support CI_DRY_RUN mode.

**Decision**:
Use shell script entrypoint (`entrypoint.sh`) to emit versions and conditionally start server.

**Rationale**:
1. **Constitution Requirement**: Version emission required
2. **CI Support**: CI_DRY_RUN mode for build verification
3. **Debugging**: Version info helps troubleshoot issues
4. **Flexibility**: Easy to add startup checks

**Consequences**:
- ✅ Version info visible in container logs
- ✅ CI can verify build without running server
- ✅ Easy to extend with health checks
- ⚠️ Adds shell script to maintain

**Emitted Versions**:
- Python version
- FastAPI version
- Uvicorn version
- OpenCV version
- Pydantic version

---

## Security Decisions

### SEC-001: LAN-Only Deployment Posture

**Status**: Accepted  
**Date**: 2025-10-17

**Context**:
Application stores RTSP credentials in plaintext and has no authentication.

**Decision**:
Explicitly document LAN-only deployment posture with prominent warnings.

**Rationale**:
1. **Use Case**: Home/office LAN camera monitoring
2. **Simplicity**: No auth complexity for trusted network
3. **Transparency**: Clear warnings about limitations

**Consequences**:
- ✅ Simple deployment for intended use case
- ⚠️ NOT suitable for internet exposure
- ⚠️ Credentials stored in plaintext

**Warnings Added**:
- README.md security section
- OpenAPI description
- Quickstart documentation

---

### SEC-002: No CSRF Protection (Deferred)

**Status**: Deferred  
**Date**: 2025-10-17

**Context**:
HTML forms submit to API without CSRF tokens.

**Decision**:
Defer CSRF protection to future iteration (T064 marked optional).

**Rationale**:
1. **LAN-Only**: CSRF risk minimal on trusted network
2. **Complexity**: Adds cookie management and token validation
3. **Priority**: Core functionality first

**Consequences**:
- ⚠️ Vulnerable to CSRF if exposed to internet
- ⚠️ Should be added before any WAN deployment

**Future Work**:
- Implement cookie-based CSRF tokens
- Add hidden input validation
- Update forms and API handlers

---

## Performance Decisions

### PERF-001: 5 FPS Playback Cap

**Status**: Accepted  
**Date**: 2025-10-17

**Context**:
Need to balance video quality with bandwidth and CPU usage.

**Decision**:
Cap playback at ≤5 FPS server-side.

**Rationale**:
1. **Spec Requirement**: FR-011 specifies ≤5 FPS
2. **Bandwidth**: Reduce network usage for multiple viewers
3. **CPU**: Reduce server-side decoding load
4. **Use Case**: Monitoring doesn't require high FPS

**Consequences**:
- ✅ Lower bandwidth usage
- ✅ Lower CPU usage
- ⚠️ Not suitable for high-motion scenarios

**Implementation**:
- `time.sleep(0.2)` between frames (5 FPS)
- Server-side throttling (not client-side)

---

## Future Considerations

### FUTURE-001: Multi-Stream Concurrent Playback

**Status**: Out of Scope  
**Date**: 2025-10-17

**Context**:
Current implementation supports one active playback per UI session.

**Decision**:
Defer multi-stream grid view to future iteration.

**Rationale**:
- Spec focuses on single-stream playback
- Complexity of grid layout and bandwidth management
- MVP prioritizes core functionality

---

### FUTURE-002: HTTPS/TLS Support

**Status**: Out of Scope  
**Date**: 2025-10-17

**Context**:
Application serves HTTP only.

**Decision**:
Defer TLS to future iteration or reverse proxy.

**Rationale**:
- LAN-only deployment doesn't require TLS
- Can be added via reverse proxy (nginx, Traefik)
- Simplifies initial deployment

**Recommendation**:
Use reverse proxy (nginx, Caddy) for TLS if needed.

---

### FUTURE-003: Authentication/Authorization

**Status**: Out of Scope  
**Date**: 2025-10-17

**Context**:
No authentication or authorization implemented.

**Decision**:
Defer to future iteration if WAN deployment needed.

**Rationale**:
- LAN-only deployment on trusted network
- Adds complexity (user management, sessions)
- Not required for MVP

**Recommendation**:
Consider OAuth2, basic auth with TLS, or API keys for WAN deployment.
