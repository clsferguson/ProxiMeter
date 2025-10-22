/**
 * API service layer for ProxiMeter backend communication
 * Uses native Fetch API with error handling, timeouts, and type safety
 */

import { API_BASE_URL } from '../lib/constants';
import type {
  StreamResponse,
  NewStreamRequest,
  EditStreamRequest,
  ReorderRequest,
  ErrorResponse,
  ApiError,
} from '../lib/types';

/**
 * Default timeout for API requests (10 seconds per spec)
 */
const DEFAULT_TIMEOUT = 10000;

/**
 * Custom error class for API errors
 */
export class ApiRequestError extends Error implements ApiError {
  status?: number | undefined;
  detail?: string | undefined;

  constructor(message: string, status?: number, detail?: string) {
    super(message);
    this.name = 'ApiRequestError';
    this.status = status ?? undefined;
    this.detail = detail ?? undefined;
  }
}

/**
 * Create an AbortController with timeout
 */
function createTimeoutController(timeoutMs: number = DEFAULT_TIMEOUT): AbortController {
  const controller = new AbortController();
  setTimeout(() => controller.abort(), timeoutMs);
  return controller;
}

/**
 * Parse error response from API
 */
async function parseErrorResponse(response: Response): Promise<ApiRequestError> {
  try {
    const errorData: ErrorResponse = await response.json();
    return new ApiRequestError(
      errorData.detail || 'An error occurred',
      response.status,
      errorData.detail
    );
  } catch {
    return new ApiRequestError(
      `HTTP ${response.status}: ${response.statusText}`,
      response.status
    );
  }
}

/**
 * Generic fetch wrapper with error handling and timeout
 */
async function fetchWithTimeout<T>(
  url: string,
  options: RequestInit = {},
  timeoutMs: number = DEFAULT_TIMEOUT
): Promise<T> {
  const controller = createTimeoutController(timeoutMs);

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });

    // Handle 204 No Content
    if (response.status === 204) {
      return undefined as T;
    }

    // Handle error responses
    if (!response.ok) {
      throw await parseErrorResponse(response);
    }

    // Parse JSON response
    return await response.json();
  } catch (error) {
    // Handle timeout
    if (error instanceof Error && error.name === 'AbortError') {
      throw new ApiRequestError('Request timeout', 408, 'The request took too long to complete');
    }

    // Handle network errors
    if (error instanceof TypeError) {
      throw new ApiRequestError('Network error', undefined, 'Failed to connect to the server');
    }

    // Re-throw API errors
    if (error instanceof ApiRequestError) {
      throw error;
    }

    // Handle unknown errors
    throw new ApiRequestError(
      error instanceof Error ? error.message : 'An unknown error occurred'
    );
  }
}

/**
 * API service for stream management
 */
export const streamApi = {
  /**
   * Get all streams
   */
  async getStreams(): Promise<StreamResponse[]> {
    return fetchWithTimeout<StreamResponse[]>(`${API_BASE_URL}/streams`, {
      method: 'GET',
    });
  },

  /**
   * Create a new stream
   */
  async createStream(data: NewStreamRequest): Promise<StreamResponse> {
    return fetchWithTimeout<StreamResponse>(`${API_BASE_URL}/streams`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  /**
   * Update an existing stream
   */
  async updateStream(streamId: string, data: EditStreamRequest): Promise<StreamResponse> {
    return fetchWithTimeout<StreamResponse>(`${API_BASE_URL}/streams/${streamId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  },

  /**
   * Delete a stream
   */
  async deleteStream(streamId: string): Promise<void> {
    return fetchWithTimeout<void>(`${API_BASE_URL}/streams/${streamId}`, {
      method: 'DELETE',
    });
  },

  /**
   * Reorder streams
   */
  async reorderStreams(order: string[]): Promise<{ success: boolean; message: string }> {
    const data: ReorderRequest = { order };
    return fetchWithTimeout<{ success: boolean; message: string }>(`${API_BASE_URL}/streams`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  },

  /**
   * Get MJPEG stream URL for playback
   */
  getPlaybackUrl(streamId: string): string {
    return `${API_BASE_URL}/streams/play/${streamId}.mjpg`;
  },
};

/**
 * Export API error class for error handling
 */
export { ApiRequestError as ApiError };
