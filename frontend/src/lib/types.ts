/**
 * TypeScript interfaces for ProxiMeter API contracts
 * Based on specs/003-frontend-react-migration/contracts/openapi.yaml
 */

/**
 * Stream response from API with masked credentials
 */
export interface StreamResponse {
  id: string;
  name: string;
  rtsp_url: string;
  created_at: string;
  order: number;
  status: 'Active' | 'Inactive';
}

/**
 * Request payload for creating a new stream
 */
export interface NewStreamRequest {
  name: string;
  rtsp_url: string;
}

/**
 * Request payload for editing an existing stream
 * At least one field must be provided
 */
export interface EditStreamRequest {
  name?: string;
  rtsp_url?: string;
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
