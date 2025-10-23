/**
 * Application-wide constants and configuration
 */

/**
 * API base URL for backend communication
 * Since the frontend is served from the backend container,
 * we use a relative path that works in all environments
 */
export const API_BASE_URL = '/api' as const

/**
 * Default polling intervals (milliseconds)
 */
export const POLLING_INTERVALS = {
  STREAM_STATUS: 2000, // 2 seconds for stream status updates
} as const

/**
 * API timeout configuration (milliseconds)
 */
export const API_TIMEOUTS = {
  DEFAULT: 10000, // 10 seconds default timeout
  STREAM_FETCH: 5000, // 5 seconds for fetching stream data
} as const

/**
 * UI configuration
 */
export const UI_CONFIG = {
  MIN_TOUCH_TARGET: 44, // Minimum touch target size in pixels (44x44px)
  MOBILE_BREAKPOINT: 768, // Mobile breakpoint in pixels
  MAX_STREAM_NAME_LENGTH: 40, // Max characters before ellipsis
} as const

/**
 * Form validation constants
 */
export const VALIDATION = {
  THRESHOLD_MIN: 0,
  THRESHOLD_MAX: 1,
  RTSP_URL_PREFIX: 'rtsp://',
} as const
