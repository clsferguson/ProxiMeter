# Research for 002-fastapi-rtsp-streams

All unknowns in Technical Context resolved here. Each item includes decision, rationale, and alternatives.

## Browser playback transport
- Decision: MJPEG over HTTP (multipart/x-mixed-replace) served by FastAPI; client renders via <img> tag
- Rationale: No audio needed; easy to cap at ≤5 FPS; minimal dependencies; works with standard browsers; avoids complex signaling/servers
- Alternatives considered: WebRTC (lower latency but significantly higher complexity and infra); HLS/DASH (segmenting, higher latency, audio not needed); MSE (needs encoding pipeline)

## RTSP validation and connectivity on save
- Decision: Validate schema (rtsp://, host) synchronously; attempt a single-frame probe with OpenCV/FFmpeg with 2s timeout; if probe fails, save as status=Inactive and surface warning
- Rationale: Avoids blocking UI excessively while ensuring obvious misconfigs are flagged; fulfills spec allowing Inactive save with status indicator
- Alternatives considered: Full playback attempt on save (too slow and fragile); no connectivity check (poor UX)

## FPS enforcement method
- Decision: Throttle server-side generator to produce ≤5 frames/sec using time-based gating; drop/skips frames between yields
- Rationale: Reliable cap independent of source FPS; simpler than adaptive sampling and avoids buffering
- Alternatives considered: Client-side throttling (browser still receives all frames); decode rate limiting (may cause RTSP jitter)

## Reorder persistence API
- Decision: POST /streams/reorder with body: { order: ["<uuid>", ...] }; server updates each stream.order atomically and persists
- Rationale: Simple, idempotent; easy to implement with drag-and-drop UI
- Alternatives considered: PATCH per-item (chatty); implicit index via PUT list (risk of concurrency issues)

## YAML config schema and storage
- Decision: Single file at /app/config/config.yml with array field streams[]; each item has: id (UUIDv4), name (1–50 chars, unique CI), rtsp_url (string), created_at (ISO8601), order (int), status (Active|Inactive)
- Rationale: Matches spec FR-009 and governance; preserves order
- Alternatives considered: SQLite (more complex than required), multiple files (harder to manage atomically)

## Header animation approach
- Decision: CSS transitions on a header element with two states: landing (centered, larger) and playing (top-left, smaller). Transition 400–700ms ease.
- Rationale: Pure CSS for smoothness and simplicity; JS only toggles classes on route change
- Alternatives considered: JS animation libraries (overkill), keyframes (harder to coordinate across routes)

## Equal-width stream buttons
- Decision: CSS grid with grid-auto-flow: row; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); buttons styled to fill 100% column width; ensure same-row width equality
- Rationale: Ensures equal width in a row within ±2px; responsive without JS
- Alternatives considered: Flexbox with flex-basis (grid simpler for equal widths per row)

## Error handling for playback failures
- Decision: On generator errors/timeouts, send error state to template via SSE channel update or fallback to redirect with flash-like banner; provide prominent link back to landing
- Rationale: Keeps UI responsive; avoids crashes
- Alternatives considered: Silent fail (bad UX)

## Credentials in RTSP URLs
- Decision: Allow username:password@host in rtsp_url as provided; store plaintext with UI and README warnings; avoid masking in config.yml but mask in logs/UI
- Rationale: Meets spec; operationally simple; security posture is LAN-only
- Alternatives considered: Separate credential store (out of scope and adds complexity)

## Testing strategy
- Decision: Unit tests for validation and YAML IO; integration tests with synthetic RTSP source (e.g., sample file via FFmpeg as RTSP or cv2.VideoCapture to a test file) gated in CI
- Rationale: CI is CPU-only; avoids real cameras; deterministic
- Alternatives considered: Live camera tests (not feasible in CI)

## ASGI server and health/metrics
- Decision: Uvicorn in Docker; expose /health; keep Prometheus metrics stub in place (to be extended in later features)
- Rationale: Aligns with constitution; minimal to satisfy operability
- Alternatives considered: Gunicorn+Uvicorn workers (can be added later if needed)
