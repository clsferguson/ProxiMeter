# Data Model: Hardware Accelerated FFmpeg RTSP Processing

**Date**: October 23, 2025  
**Feature**: 004-hw-ffmpeg-rtsp-processing  

## Entities

### Stream
**Description**: Configuration for an RTSP stream with hardware acceleration and custom FFmpeg parameters.

**Fields**:
- id: str (UUID)
- name: str (required, max 100 chars)
- url: str (RTSP URL, validated with ffprobe)
- enabled: bool (default: false)
- hw_accel_enabled: bool (default: true)
- ffmpeg_params: list[str] (optional, default: [&quot;-hide_banner&quot;, &quot;-loglevel&quot;, &quot;warning&quot;, &quot;-threads&quot;, &quot;2&quot;, &quot;-rtsp_transport&quot;, &quot;tcp&quot;, &quot;-timeout&quot;, &quot;10000000&quot;] + GPU-specific flags)
- target_fps: int (default: 5, min 1, max 30)
- zones: list[Zone] (optional)

**Validation Rules**:
- URL must be valid RTSP (rtsp://...)
- ffmpeg_params: Whitelist safe flags; no shell metachars
- On save: Probe URL with constructed FFmpeg command to validate

**Relationships**:
- One-to-many with Zone

### Zone
**Description**: Polygon zone for scoring within a stream.

**Fields**:
- id: str (UUID)
- stream_id: str (foreign key)
- name: str
- points: list[Point] (polygon vertices, min 3)
- enabled_metrics: list[str] (from [&quot;distance&quot;, &quot;coordinates&quot;, &quot;size&quot;])
- target_point: Point (optional, for distance metric)
- active: bool (default: true)

### Point
**Description**: 2D coordinate for polygons.

**Fields**:
- x: float (0-1 normalized)
- y: float (0-1 normalized)

### ProcessedFrame (Internal, Ephemeral)
**Description**: In-memory frame for processing.

**Fields**:
- stream_id: str
- timestamp: datetime
- frame: bytes (MJPEG) or np.array (for inference)
- metadata: dict (fps, latency)

**State Transitions**:
- Stream: disabled → enabled (start FFmpeg subprocess) → processing → error/disconnected → disabled

No persistent storage beyond config.yml serialization.