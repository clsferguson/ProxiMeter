/**
 * Detection API service for YOLO object detection configuration
 * Handles model config, stream detection settings, and model cache management
 */

import { API_BASE_URL } from '../lib/constants';
import { ApiRequestError } from './api';

const DEFAULT_TIMEOUT = 10000;

/**
 * YOLO model configuration
 */
export interface YOLOConfig {
  model_name: string;
  image_size: number;
  backend: 'nvidia' | 'amd' | 'intel' | 'none';
  model_path: string;
}

/**
 * Stream detection configuration
 */
export interface StreamDetectionConfig {
  enabled: boolean;
  enabled_labels: string[];
  min_confidence: number;
}

/**
 * Cached model metadata
 */
export interface CachedModel {
  model_name: string;
  file_path: string;
  file_size_bytes: number;
  download_date: number;
  is_active: boolean;
}

/**
 * Models list response
 */
export interface ModelsListResponse {
  models: CachedModel[];
  active_model: string | null;
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
    const contentType = response.headers.get('content-type');

    if (contentType?.includes('application/json')) {
      const errorData = await response.json();
      return new ApiRequestError(
        errorData.detail?.message || errorData.detail || 'An error occurred',
        response.status,
        errorData.detail
      );
    }

    return new ApiRequestError(
      `HTTP ${response.status}: ${response.statusText}`,
      response.status
    );
  } catch {
    return new ApiRequestError(
      `HTTP ${response.status}: ${response.statusText}`,
      response.status
    );
  }
}

/**
 * Get YOLO model configuration
 */
export async function getYoloConfig(): Promise<YOLOConfig> {
  const controller = createTimeoutController();

  try {
    const response = await fetch(`${API_BASE_URL}/yolo/config`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
      signal: controller.signal,
    });

    if (!response.ok) {
      throw await parseErrorResponse(response);
    }

    return await response.json();
  } catch (error) {
    if (error instanceof ApiRequestError) {
      throw error;
    }
    if ((error as Error).name === 'AbortError') {
      throw new ApiRequestError('Request timeout', 408);
    }
    throw new ApiRequestError(
      error instanceof Error ? error.message : 'Unknown error',
      undefined
    );
  }
}

/**
 * List all cached YOLO models
 */
export async function listCachedModels(): Promise<ModelsListResponse> {
  const controller = createTimeoutController();

  try {
    const response = await fetch(`${API_BASE_URL}/models`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
      signal: controller.signal,
    });

    if (!response.ok) {
      throw await parseErrorResponse(response);
    }

    return await response.json();
  } catch (error) {
    if (error instanceof ApiRequestError) {
      throw error;
    }
    if ((error as Error).name === 'AbortError') {
      throw new ApiRequestError('Request timeout', 408);
    }
    throw new ApiRequestError(
      error instanceof Error ? error.message : 'Unknown error',
      undefined
    );
  }
}

/**
 * Delete a cached YOLO model
 */
export async function deleteCachedModel(modelName: string): Promise<void> {
  const controller = createTimeoutController();

  try {
    const response = await fetch(`${API_BASE_URL}/models/${encodeURIComponent(modelName)}`, {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      signal: controller.signal,
    });

    if (!response.ok) {
      throw await parseErrorResponse(response);
    }
  } catch (error) {
    if (error instanceof ApiRequestError) {
      throw error;
    }
    if ((error as Error).name === 'AbortError') {
      throw new ApiRequestError('Request timeout', 408);
    }
    throw new ApiRequestError(
      error instanceof Error ? error.message : 'Unknown error',
      undefined
    );
  }
}

/**
 * Get detection configuration for a stream
 */
export async function getDetectionConfig(streamId: string): Promise<StreamDetectionConfig> {
  const controller = createTimeoutController();

  try {
    const response = await fetch(`${API_BASE_URL}/streams/${streamId}/detection`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
      signal: controller.signal,
    });

    if (!response.ok) {
      throw await parseErrorResponse(response);
    }

    return await response.json();
  } catch (error) {
    if (error instanceof ApiRequestError) {
      throw error;
    }
    if ((error as Error).name === 'AbortError') {
      throw new ApiRequestError('Request timeout', 408);
    }
    throw new ApiRequestError(
      error instanceof Error ? error.message : 'Unknown error',
      undefined
    );
  }
}

/**
 * Update detection configuration for a stream
 */
export async function updateDetectionConfig(
  streamId: string,
  config: StreamDetectionConfig
): Promise<{ success: boolean; message: string; applied_immediately: boolean }> {
  const controller = createTimeoutController();

  try {
    const response = await fetch(`${API_BASE_URL}/streams/${streamId}/detection`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config),
      signal: controller.signal,
    });

    if (!response.ok) {
      throw await parseErrorResponse(response);
    }

    return await response.json();
  } catch (error) {
    if (error instanceof ApiRequestError) {
      throw error;
    }
    if ((error as Error).name === 'AbortError') {
      throw new ApiRequestError('Request timeout', 408);
    }
    throw new ApiRequestError(
      error instanceof Error ? error.message : 'Unknown error',
      undefined
    );
  }
}

/**
 * All 80 COCO class names
 */
export const COCO_CLASSES = [
  'person', 'bicycle', 'car', 'motorcycle', 'airplane',
  'bus', 'train', 'truck', 'boat', 'traffic light',
  'fire hydrant', 'stop sign', 'parking meter', 'bench', 'bird',
  'cat', 'dog', 'horse', 'sheep', 'cow',
  'elephant', 'bear', 'zebra', 'giraffe', 'backpack',
  'umbrella', 'handbag', 'tie', 'suitcase', 'frisbee',
  'skis', 'snowboard', 'sports ball', 'kite', 'baseball bat',
  'baseball glove', 'skateboard', 'surfboard', 'tennis racket', 'bottle',
  'wine glass', 'cup', 'fork', 'knife', 'spoon',
  'bowl', 'banana', 'apple', 'sandwich', 'orange',
  'broccoli', 'carrot', 'hot dog', 'pizza', 'donut',
  'cake', 'chair', 'couch', 'potted plant', 'bed',
  'dining table', 'toilet', 'tv', 'laptop', 'mouse',
  'remote', 'keyboard', 'cell phone', 'microwave', 'oven',
  'toaster', 'sink', 'refrigerator', 'book', 'clock',
  'vase', 'scissors', 'teddy bear', 'hair drier', 'toothbrush'
];
