import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"
import { VALIDATION, UI_CONFIG } from './constants'

/**
 * Merge Tailwind CSS classes with proper precedence
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * Mask RTSP URL credentials for display
 * Replaces username:password@ with ***:***@
 * 
 * @param url - RTSP URL with potential credentials
 * @returns Masked URL safe for display
 * 
 * @example
 * maskRtspUrl('rtsp://admin:pass123@192.168.1.100/stream')
 * // Returns: 'rtsp://***:***@192.168.1.100/stream'
 */
export function maskRtspUrl(url: string): string {
  try {
    const urlObj = new URL(url)
    if (urlObj.username || urlObj.password) {
      return url.replace(/\/\/[^@]+@/, '//***:***@')
    }
    return url
  } catch {
    // If URL parsing fails, return as-is
    return url
  }
}

/**
 * Validate RTSP URL format
 * 
 * @param url - URL to validate
 * @returns True if valid RTSP URL
 */
export function isValidRtspUrl(url: string): boolean {
  if (!url || typeof url !== 'string') {
    return false
  }

  // Must start with rtsp://
  if (!url.toLowerCase().startsWith(VALIDATION.RTSP_URL_PREFIX)) {
    return false
  }

  // Try to parse as URL
  try {
    const urlObj = new URL(url)
    return urlObj.protocol === 'rtsp:'
  } catch {
    return false
  }
}

/**
 * Validate stream name
 * 
 * @param name - Stream name to validate
 * @returns True if valid name
 */
export function isValidStreamName(name: string): boolean {
  return typeof name === 'string' && name.trim().length > 0 && name.length <= 50
}

/**
 * Truncate text with ellipsis
 * 
 * @param text - Text to truncate
 * @param maxLength - Maximum length before truncation
 * @returns Truncated text with ellipsis if needed
 */
export function truncateText(text: string, maxLength: number = UI_CONFIG.MAX_STREAM_NAME_LENGTH): string {
  if (text.length <= maxLength) {
    return text
  }
  return text.slice(0, maxLength) + '...'
}

/**
 * Format date/time for display
 * 
 * @param dateString - ISO date string
 * @returns Formatted date string
 */
export function formatDateTime(dateString: string): string {
  try {
    const date = new Date(dateString)
    return new Intl.DateTimeFormat('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }).format(date)
  } catch {
    return dateString
  }
}

/**
 * Format relative time (e.g., "2 minutes ago")
 * 
 * @param dateString - ISO date string
 * @returns Relative time string
 */
export function formatRelativeTime(dateString: string): string {
  try {
    const date = new Date(dateString)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMins / 60)
    const diffDays = Math.floor(diffHours / 24)

    if (diffMins < 1) return 'just now'
    if (diffMins < 60) return `${diffMins} minute${diffMins > 1 ? 's' : ''} ago`
    if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`
    if (diffDays < 7) return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`
    
    return formatDateTime(dateString)
  } catch {
    return dateString
  }
}

/**
 * Debounce function for performance optimization
 * 
 * @param func - Function to debounce
 * @param wait - Wait time in milliseconds
 * @returns Debounced function
 */
export function debounce<T extends (...args: unknown[]) => unknown>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: ReturnType<typeof setTimeout> | null = null

  return function executedFunction(...args: Parameters<T>) {
    const later = () => {
      timeout = null
      func(...args)
    }

    if (timeout !== null) {
      clearTimeout(timeout)
    }
    timeout = setTimeout(later, wait)
  }
}

/**
 * Sleep/delay utility for async operations
 * 
 * @param ms - Milliseconds to sleep
 * @returns Promise that resolves after delay
 */
export function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms))
}
