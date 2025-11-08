/**
 * TypeScript interfaces for ProxiMeter API contracts
 * Based on specs/003-frontend-react-migration/contracts/openapi.yaml
 * 
 * Updated: Added auto_start field to stream interfaces for automatic
 * stream startup functionality.
 */

/**
 * Stream response from API with masked credentials
 */
export interface StreamResponse {
  id: string;
  name: string;
  rtsp_url: string;
  ffmpeg_params: string[];
  created_at: string;
  order: number;
  status: 'Active' | 'Inactive' | 'running' | 'stopped' | 'error' | 'starting' | 'disconnected';
}

/**
 * Request payload for creating a new stream
 */
export interface NewStreamRequest {
  name: string;
  rtsp_url: string;
  ffmpeg_params?: string[];
  auto_start?: boolean;  // NEW: Auto-start on creation/reboot (default: true)
}

/**
 * Request payload for editing an existing stream
 * At least one field must be provided
 */
export interface EditStreamRequest {
  name?: string;
  rtsp_url?: string;
  ffmpeg_params?: string[];
}

/**
 * Request payload for reordering streams
 */
export interface ReorderRequest {
  order: string[];
}

/**
 * Standard error response from API
 */
export interface ErrorResponse {
  detail: string;
}

/**
 * API response wrapper for successful operations
 */
export interface ApiResponse<T> {
  data: T;
  status: number;
}

/**
 * API error wrapper
 */
export interface ApiError {
  message: string;
  status?: number | undefined;
  detail?: string | undefined;
}

/**
 * Form state for stream creation/editing
 */
export interface StreamFormData {
  name: string;
  rtsp_url: string;
}

/**
 * Form validation errors
 */
export interface FormErrors {
  name?: string;
  rtsp_url?: string;
}

/**
 * Loading state for async operations
 */
export interface LoadingState {
  isLoading: boolean;
  error: string | null;
}

/**
 * Stream list state
 */
export interface StreamsState extends LoadingState {
  streams: StreamResponse[];
  lastUpdated: number | null;
}

/**
 * FFmpeg defaults response from API
 */
export interface FfmpegDefaultsResponse {
  gpu_backend: string;
  base_params: string[];
  gpu_params: string[];
  combined_params: string;
  combined_params_array: string[];
}

// ============================================================================
// Motion Detection and Object Tracking Types (Feature 006)
// ============================================================================

/**
 * Object lifecycle states for tracking
 */
export enum ObjectState {
  TENTATIVE = 'tentative',    // Initial detection, not yet confirmed
  ACTIVE = 'active',           // Confirmed and actively moving
  STATIONARY = 'stationary',   // Stopped moving (50 frame threshold)
  LOST = 'lost'                // No detection match (prediction only)
}

/**
 * Motion region detected in frame
 */
export interface MotionRegion {
  bounding_box: [number, number, number, number];  // [x, y, width, height]
  area: number;
  timestamp: number;
  merged_count: number;
}

/**
 * Tracked object with Kalman filter state
 */
export interface TrackedObject {
  id: string;                                       // UUID
  class_name: string;                               // YOLO class (e.g., 'person', 'car')
  confidence: number;                               // 0.0-1.0
  bounding_box: [number, number, number, number];   // [x, y, width, height]
  bounding_box_history: Array<[number, number, number, number]>;
  velocity: [number, number];                       // [vx, vy] in pixels per frame
  state: ObjectState;
  last_seen_frame: number;
  frames_since_detection: number;
  frames_stationary: number;
  detection_interval: number;                       // Run detection every N frames
  hits: number;                                     // Total successful detection matches
  age: number;                                      // Total frames since track creation
}

/**
 * Per-stream motion detection metrics
 */
export interface MotionDetectionMetrics {
  stream_id: string;
  motion_regions_count: number;
  tracked_objects_count: number;                    // ACTIVE + TENTATIVE only
  stationary_objects_count: number;
  lost_objects_count: number;
  gpu_utilization_percent: number | null;
  motion_detection_ms: number;                      // CPU time for motion detection
  yolo_inference_ms: number;                        // GPU time for YOLO inference
  tracking_ms: number;                              // CPU time for Kalman filter
  total_frame_time_ms: number;                      // Total frame processing time
  timestamp: number;                                // Unix seconds
}

/**
 * Motion visualization settings (session-only, not persisted)
 */
export interface MotionVisualizationSettings {
  showMotionBoxes: boolean;
  showTrackingBoxes: boolean;
  showStationaryObjects: boolean;
}