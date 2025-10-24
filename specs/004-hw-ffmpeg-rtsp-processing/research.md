# Research: Hardware Accelerated FFmpeg RTSP Processing with User-Specified Parameters

**Date**: October 23, 2025  
**Feature**: 004-hw-ffmpeg-rtsp-processing  

## Research Tasks

### 1. Integration of User-Specified FFmpeg Parameters with GPU Detection
**Context**: Users need to specify custom FFmpeg flags for RTSP decoding, with defaults including &quot;-hide_banner&quot;, &quot;-loglevel&quot;, &quot;warning&quot;, &quot;-threads&quot;, &quot;2&quot;, &quot;-rtsp_transport&quot;, &quot;tcp&quot;, and timeout. Defaults must incorporate GPU-specific flags based on entrypoint.sh detection (NVIDIA, AMD, Intel).

**Findings**:
- FFmpeg supports hardware acceleration via specific decoders: h264_cuvid/nvdec (NVIDIA CUDA), h264_amf (AMD), h264_qsv (Intel Quick Sync).
- entrypoint.sh can set an environment variable like GPU_BACKEND_DETECTED (e.g., &quot;nvidia&quot;, &quot;amd&quot;, &quot;intel&quot;).
- In the backend, construct FFmpeg command dynamically: base user params + GPU-specific decoder flags if GPU_BACKEND_DETECTED is set.
- Validation: Use subprocess to test FFmpeg command with a short probe before full stream activation; catch errors and report to UI.
- Defaults: For NVIDIA: add &quot;-hwaccel cuda -hwaccel_output_format cuda&quot;; AMD: &quot;-hwaccel amf&quot;; Intel: &quot;-hwaccel qsv&quot;. Always include user-provided flags, overriding defaults if specified.
- Timeout: Use &quot;-timeout 10000000&quot; (10s in microseconds) for RTSP connection.

**Decision**: Dynamically build FFmpeg args list in streams_service.py using os.environ.get('GPU_BACKEND_DETECTED') to append hardware flags. Store user params as list[str] in Stream model. Validate by running 'ffprobe' on URL with constructed args on stream save.

**Rationale**: Ensures flexibility for advanced users while auto-configuring hardware acceleration. Fail-fast validation prevents runtime errors.

**Alternatives Considered**:
- Hardcode all flags: Rejected, as it limits user customization.
- No validation: Rejected, risks stream failures; probe ensures compatibility.

### 2. Best Practices for FFmpeg in FastAPI with Hardware Acceleration
**Context**: Ensure efficient, real-time RTSP processing at 5 FPS cap.

**Findings**:
- Use subprocess.Popen for non-blocking FFmpeg pipe to read frames.
- For MJPEG output: &quot;-f mjpeg -q:v 2 -r 5 pipe:1&quot;.
- Hardware decoding: Specify decoder (e.g., &quot;-c:v h264_cuvid&quot;) after connection flags.
- Threading: Limit to 2-4 threads; use &quot;-threads 2&quot; as default.
- Error handling: Monitor subprocess return code and stderr; reconnect on EOF or timeout.
- Integration with OpenCV: Read from pipe as cv2.VideoCapture(fd).

**Decision**: Implement in streams_service.py: Start FFmpeg subprocess per stream, pipe to OpenCV for frame extraction at 5 FPS, then process with YOLO.

**Rationale**: Balances performance and reliability; hardware accel reduces CPU load.

**Alternatives Considered**:
- OpenCV RTSP direct: Limited hardware support; FFmpeg more flexible.
- GStreamer: More complex setup; FFmpeg sufficient for this scope.

### 3. UI for FFmpeg Parameters in React with shadcn/ui
**Context**: Input box with placeholder for defaults.

**Findings**:
- Use shadcn/ui Input component with placeholder showing default flags as space-separated string.
- On save, split by space and validate (no shell injection; whitelist common flags).
- Display detected GPU in UI via API endpoint exposing GPU_BACKEND_DETECTED.

**Decision**: Add Textarea in StreamForm.tsx for ffmpeg_params, placeholder with computed defaults (fetch from API).

**Rationale**: User-friendly; prevents invalid inputs.

**Alternatives Considered**:
- Dropdown for presets: Too rigid; free-form with validation better.

All NEEDS CLARIFICATION resolved.