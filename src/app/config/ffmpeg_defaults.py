"""FFmpeg default parameter configuration.

Single source of truth for FFmpeg parameters used across the application.
Parameters are GPU-backend specific and exposed via API for frontend display.

Constitution Compliance:
    Principle II: FFmpeg handles ALL RTSP processing
    Principle III: GPU backend contract enforcement
"""
from typing import Final

# ============================================================================
# Base FFmpeg Parameters
# ============================================================================

BASE_FFMPEG_PARAMS: Final[list[str]] = [
    '-hide_banner',
    '-loglevel', 'warning',
    '-threads', '2',
    '-rtsp_transport', 'tcp',
    '-rtsp_flags', 'prefer_tcp',
    '-max_delay', '500000',
    '-analyzeduration', '1000000',
    '-probesize', '1000000',
    '-fflags', 'nobuffer',
    '-flags', 'low_delay',
]
"""Base FFmpeg parameters applied to all streams regardless of GPU backend."""

# ============================================================================
# GPU-Specific Parameters
# ============================================================================

GPU_FFMPEG_PARAMS: Final[dict[str, list[str]]] = {
    'nvidia': [
        '-hwaccel', 'cuda',
        '-hwaccel_output_format', 'cuda',
    ],
    'amd': [
        '-hwaccel', 'vaapi',
        '-hwaccel_device', '/dev/dri/renderD128',
    ],
    'intel': [
        '-hwaccel', 'qsv',
        '-hwaccel_device', '/dev/dri/renderD128',
    ],
    'none': [],
}
"""GPU-specific hardware acceleration parameters by backend."""

# ============================================================================
# Helper Functions
# ============================================================================

def get_default_ffmpeg_params(gpu_backend: str) -> list[str]:
    """Get complete default FFmpeg parameters for a GPU backend.
    
    Args:
        gpu_backend: GPU backend (nvidia/amd/intel/none)
        
    Returns:
        Complete list of FFmpeg parameters (base + GPU-specific)
    """
    gpu_params = GPU_FFMPEG_PARAMS.get(gpu_backend, [])
    return list(BASE_FFMPEG_PARAMS) + gpu_params


def get_default_ffmpeg_params_string(gpu_backend: str) -> str:
    """Get default FFmpeg parameters as space-separated string.
    
    Args:
        gpu_backend: GPU backend (nvidia/amd/intel/none)
        
    Returns:
        Space-separated FFmpeg parameter string for display
    """
    return ' '.join(get_default_ffmpeg_params(gpu_backend))
