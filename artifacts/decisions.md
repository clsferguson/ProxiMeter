# ProxiMeter Technical Decisions

## Feature: FastAPI RTSP Streams and Landing UI

**Date**: 2025-10-17  
**Branch**: 002-fastapi-rtsp-streams  
**Spec**: `specs/002-fastapi-rtsp-streams/spec.md`

---

## Architecture Decisions

### ADR-011: Adopt Tailwind CSS + shadcn/ui Design System

**Status**: Accepted  
**Date**: 2025-10-21  
**Branch**: 003-frontend-react-migration  
**Spec**: `specs/003-frontend-react-migration/spec.md`

**Context**:
The React frontend migrated from server-rendered templates to a TypeScript SPA. Existing CSS was ad-hoc and difficult to scale across new polygon editor and scoring workflows. The constitution v2.4.0 mandates a standardized component system to maintain accessibility, responsiveness, and consistent styling.

**Decision**:
Adopt Tailwind CSS as the utility foundation and shadcn/ui (Tailwind + Radix UI primitives) as the component library for all React UI work.

**Rationale**:
1. **Consistency**: shadcn/ui enforces unified spacing, typography, and state styling across the SPA.
2. **Accessibility**: Components ship with ARIA, keyboard navigation, and color contrast defaults.
3. **Velocity**: CLI-driven component scaffolding accelerates feature delivery.
4. **Composition**: Tailwind utilities plus `class-variance-authority` allow custom variants without bespoke CSS files.
5. **Governance Alignment**: Satisfies Constitution Principle VIII and compliance checklist.

**Consequences**:
- ✅ Shared design tokens defined in `tailwind.config.ts` replace scattered CSS.
- ✅ New UI components live under `frontend/src/components/ui/` generated via `npx shadcn add`.
- ✅ Global theming delivered by the shadcn/ui `ThemeProvider` with dark/light modes.
- ⚠️ Requires Tailwind build tooling in Vite and Docker image.
- ⚠️ Existing legacy styles must be migrated or removed to avoid conflicts.

**Implementation Notes**:
- Tailwind/Tailwind Merge/Class Variance Authority configured during project initialization.
- `lucide-react` provides iconography referenced by shadcn/ui components.
- React Hook Form + Zod integrated with shadcn/ui form primitives for validation UX.
- README documents setup and contribution guidelines; tasks.md updated with migration work items.

**Alternatives Considered**:
- **Plain Tailwind + custom components**: Rejected due to higher maintenance burden and inconsistent accessibility.
- **Material UI / Chakra UI**: Rejected to avoid heavy runtime styling systems and to stay aligned with Tailwind utility-first approach.
- **Continue legacy CSS**: Rejected due to Constitution compliance requirements and scalability concerns.

---

## Design System Reference

### Tailwind Design Tokens

All design tokens are centralized in `frontend/tailwind.config.ts` and `frontend/src/styles/tailwind.css`. This ensures consistency across the application.

#### Color Palette

**Primary Colors** (from shadcn/ui defaults):
- `primary`: `hsl(222.2 47.6% 11.2%)` - Dark blue (default theme)
- `primary-foreground`: `hsl(210 40% 98%)` - Light text on primary
- `secondary`: `hsl(210 40% 96%)` - Light gray
- `secondary-foreground`: `hsl(222.2 47.6% 11.2%)` - Dark text on secondary

**Semantic Colors**:
- `destructive`: `hsl(0 84.2% 60.2%)` - Red for delete/error actions
- `destructive-foreground`: `hsl(210 40% 98%)` - Light text on destructive
- `success`: `hsl(142.3 71.8% 29.2%)` - Green for success states
- `warning`: `hsl(38.6 92.1% 50.2%)` - Amber for warnings
- `info`: `hsl(217.2 91.2% 59.8%)` - Blue for informational messages

**Neutral Colors**:
- `background`: `hsl(0 0% 100%)` - White (light mode)
- `foreground`: `hsl(222.2 84% 5%)` - Near-black text
- `muted`: `hsl(210 40% 96%)` - Disabled/secondary text
- `muted-foreground`: `hsl(215.4 16.3% 46.9%)` - Muted text color
- `border`: `hsl(214.3 31.8% 91.4%)` - Border color
- `input`: `hsl(214.3 31.8% 91.4%)` - Input field background
- `ring`: `hsl(222.2 84% 5%)` - Focus ring color

**Dark Mode**:
- Automatically inverted via `next-themes` ThemeProvider
- All colors have dark mode equivalents in `tailwind.config.ts`

#### Spacing Scale

Tailwind's default spacing scale (4px base unit):
- `0` = 0px
- `1` = 4px
- `2` = 8px
- `3` = 12px
- `4` = 16px
- `6` = 24px
- `8` = 32px
- `12` = 48px
- `16` = 64px

**Touch Target Minimum**: All interactive elements use minimum `h-10 w-10` (40px) for mobile accessibility.

#### Typography

**Font Family**:
- `font-sans`: System font stack (Segoe UI, Roboto, etc.)
- `font-mono`: Monospace for code (Monaco, Courier New, etc.)

**Font Sizes**:
- `text-xs`: 12px (captions, badges)
- `text-sm`: 14px (secondary text, form labels)
- `text-base`: 16px (body text, default)
- `text-lg`: 18px (section headings)
- `text-xl`: 20px (page headings)
- `text-2xl`: 24px (major headings)

**Font Weights**:
- `font-normal`: 400 (body text)
- `font-medium`: 500 (labels, emphasis)
- `font-semibold`: 600 (headings)
- `font-bold`: 700 (strong emphasis)

#### Border Radius

- `rounded-none`: 0px
- `rounded-sm`: 2px (subtle)
- `rounded-md`: 6px (default for buttons/cards)
- `rounded-lg`: 8px (larger components)
- `rounded-full`: 9999px (pills, avatars)

#### Shadows

- `shadow-sm`: Subtle elevation
- `shadow-md`: Default elevation (cards, modals)
- `shadow-lg`: Strong elevation (dropdowns, tooltips)
- `shadow-xl`: Maximum elevation (modals, popovers)

### Component Mapping

#### Form Components

| Component | Location | Tailwind Tokens | Notes |
|-----------|----------|-----------------|-------|
| `Button` | `ui/button.tsx` | `bg-primary`, `text-primary-foreground`, `h-10 px-4` | Variants: default, secondary, destructive, outline, ghost |
| `Input` | `ui/input.tsx` | `border`, `bg-background`, `text-foreground` | Inherits Tailwind form styling |
| `Label` | `ui/label.tsx` | `text-sm font-medium` | Associated with form inputs via `htmlFor` |
| `Select` | `ui/select.tsx` | `border`, `bg-background` | Radix UI primitive with Tailwind styling |
| `Textarea` | `ui/textarea.tsx` | `border`, `bg-background`, `text-foreground` | Resizable text input |
| `Checkbox` | `ui/checkbox.tsx` | `border`, `bg-primary` | Radix UI primitive |
| `Radio Group` | `ui/radio-group.tsx` | `border`, `bg-primary` | Radix UI primitive |

#### Layout Components

| Component | Location | Tailwind Tokens | Notes |
|-----------|----------|-----------------|-------|
| `Card` | `ui/card.tsx` | `bg-background`, `border`, `rounded-lg`, `shadow-md` | Container for grouped content |
| `Dialog` | `ui/dialog.tsx` | `bg-background`, `shadow-xl` | Modal overlay with Radix UI |
| `Alert Dialog` | `ui/alert-dialog.tsx` | `bg-background`, `shadow-xl` | Confirmation dialogs |
| `Tabs` | `ui/tabs.tsx` | `border-b`, `text-muted-foreground` | Tabbed content navigation |
| `Accordion` | `ui/accordion.tsx` | `border`, `text-foreground` | Collapsible sections |

#### Feedback Components

| Component | Location | Tailwind Tokens | Notes |
|-----------|----------|-----------------|-------|
| `Alert` | `ui/alert.tsx` | `bg-secondary`, `border-l-4`, `text-foreground` | Variants: default, destructive, success, warning |
| `Badge` | `ui/badge.tsx` | `bg-primary`, `text-primary-foreground`, `text-xs` | Status indicators |
| `Toast` | `sonner` | `bg-background`, `border`, `shadow-lg` | Notifications via Sonner library |

#### Navigation Components

| Component | Location | Tailwind Tokens | Notes |
|-----------|----------|-----------------|-------|
| `Dropdown Menu` | `ui/dropdown-menu.tsx` | `bg-background`, `border`, `shadow-md` | Radix UI primitive |
| `Navigation Menu` | `ui/navigation-menu.tsx` | `border-b`, `text-foreground` | Horizontal navigation |

### Custom Component Patterns

When creating new components, follow these patterns:

#### Using Class Variance Authority (CVA)

```typescript
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

const componentVariants = cva(
  // Base classes applied to all variants
  'inline-flex items-center justify-center rounded-md font-medium transition-colors',
  {
    variants: {
      variant: {
        default: 'bg-primary text-primary-foreground hover:bg-primary/90',
        secondary: 'bg-secondary text-secondary-foreground hover:bg-secondary/80',
        destructive: 'bg-destructive text-destructive-foreground hover:bg-destructive/90',
        outline: 'border border-input bg-background hover:bg-accent',
        ghost: 'hover:bg-accent hover:text-accent-foreground',
      },
      size: {
        sm: 'h-8 px-3 text-xs',
        md: 'h-10 px-4 text-sm',
        lg: 'h-12 px-6 text-base',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'md',
    },
  }
)

interface ComponentProps extends VariantProps<typeof componentVariants> {
  children: React.ReactNode
}

export function Component({ variant, size, children }: ComponentProps) {
  return <div className={componentVariants({ variant, size })}>{children}</div>
}
```

#### Responsive Design

Use Tailwind's responsive prefixes for mobile-first design:

```typescript
// Mobile-first: base styles apply to all sizes
// Then override for larger screens
<div className="text-sm md:text-base lg:text-lg">
  Responsive text
</div>

// Responsive spacing
<div className="p-4 md:p-6 lg:p-8">
  Responsive padding
</div>

// Responsive grid
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
  Grid items
</div>
```

#### Dark Mode Support

All components automatically support dark mode via `next-themes`:

```typescript
// Colors automatically invert in dark mode
<div className="bg-background text-foreground">
  Works in both light and dark modes
</div>

// Explicit dark mode classes if needed
<div className="bg-white dark:bg-slate-950">
  Explicit dark mode override
</div>
```

### Adding New Components

To add a new shadcn/ui component:

```bash
npx shadcn@latest add <component-name>
```

This will:
1. Download the component source from the shadcn/ui registry
2. Place it in `frontend/src/components/ui/<component-name>.tsx`
3. Update `package.json` dependencies if needed
4. Automatically use the configured Tailwind tokens

**Common Components**:
- `npx shadcn@latest add tooltip` - Hover tooltips
- `npx shadcn@latest add popover` - Floating popovers
- `npx shadcn@latest add sheet` - Side drawer
- `npx shadcn@latest add command` - Command palette
- `npx shadcn@latest add calendar` - Date picker
- `npx shadcn@latest add slider` - Range slider

### Theming

The application uses `next-themes` for light/dark mode switching:

```typescript
// In App.tsx
import { ThemeProvider } from '@/components/theme-provider'

export function App() {
  return (
    <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
      {/* App content */}
    </ThemeProvider>
  )
}

// In components
import { useTheme } from 'next-themes'

export function ThemeToggle() {
  const { theme, setTheme } = useTheme()
  return (
    <button onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}>
      Toggle theme
    </button>
  )
}
```

---

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
