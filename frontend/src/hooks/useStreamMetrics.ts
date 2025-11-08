/**
 * useStreamMetrics Hook - Real-time Motion Detection Metrics via SSE
 *
 * Provides real-time streaming of motion detection metrics including:
 * - Motion region counts
 * - Tracked object counts (active, stationary, lost)
 * - GPU utilization
 * - Frame processing timing breakdown
 *
 * Uses Server-Sent Events (SSE) for 5 FPS metric updates.
 *
 * Feature: 006-motion-tracking
 * @module hooks/useStreamMetrics
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import type { MotionDetectionMetrics } from '@/lib/types'

// ============================================================================
// Type Definitions
// ============================================================================

/**
 * Configuration options for the useStreamMetrics hook
 */
interface UseStreamMetricsOptions {
  /** Stream ID to monitor */
  streamId: string
  /** Whether to automatically connect on mount (default: true) */
  autoConnect?: boolean
  /** Whether to automatically reconnect on error (default: true) */
  autoReconnect?: boolean
  /** Maximum reconnect attempts before giving up (default: 5) */
  maxReconnectAttempts?: number
  /** Initial reconnect delay in ms (doubles with exponential backoff, default: 1000) */
  reconnectDelay?: number
}

/**
 * Return type for the useStreamMetrics hook
 */
interface UseStreamMetricsReturn {
  /** Current motion detection metrics (null if not yet received) */
  metrics: MotionDetectionMetrics | null
  /** Loading state (true during initial connection) */
  isLoading: boolean
  /** Error message if connection fails */
  error: string | null
  /** Whether SSE connection is currently active */
  isConnected: boolean
  /** Manually reconnect to SSE endpoint */
  reconnect: () => void
  /** Manually disconnect from SSE endpoint */
  disconnect: () => void
}

// ============================================================================
// Main Hook
// ============================================================================

/**
 * Custom hook for streaming real-time motion detection metrics via SSE
 *
 * Features:
 * - Automatic connection on mount (configurable)
 * - Exponential backoff for reconnection attempts
 * - Proper cleanup of EventSource connections
 * - Real-time metric updates at 5 FPS (200ms interval)
 *
 * @param options - Configuration options
 * @returns Motion metrics streaming interface
 *
 * @example
 * ```tsx
 * // Basic usage
 * const { metrics, isLoading, error } = useStreamMetrics({
 *   streamId: 'abc-123'
 * })
 *
 * // With manual control
 * const { metrics, isConnected, reconnect, disconnect } = useStreamMetrics({
 *   streamId: 'abc-123',
 *   autoConnect: false
 * })
 * ```
 */
export function useStreamMetrics(options: UseStreamMetricsOptions): UseStreamMetricsReturn {
  const {
    streamId,
    autoConnect = true,
    autoReconnect = true,
    maxReconnectAttempts = 5,
    reconnectDelay = 1000
  } = options

  // ============================================================================
  // State Management
  // ============================================================================

  const [metrics, setMetrics] = useState<MotionDetectionMetrics | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isConnected, setIsConnected] = useState(false)

  // ============================================================================
  // Refs for SSE Connection Management
  // ============================================================================

  const eventSourceRef = useRef<EventSource | null>(null)
  const reconnectAttemptsRef = useRef(0)
  const reconnectTimeoutRef = useRef<number | null>(null)
  const shouldConnectRef = useRef(autoConnect)

  // ============================================================================
  // SSE Connection Management
  // ============================================================================

  /**
   * Establish SSE connection to metrics endpoint
   * Includes error handling and automatic reconnection with exponential backoff
   */
  const connect = useCallback(() => {
    // Don't connect if we already have an active connection
    if (eventSourceRef.current) {
      console.log(`[useStreamMetrics] Already connected to ${streamId}`)
      return
    }

    // Don't connect if we shouldn't
    if (!shouldConnectRef.current) {
      console.log(`[useStreamMetrics] Connection disabled for ${streamId}`)
      return
    }

    console.log(`[useStreamMetrics] Connecting to metrics SSE for stream ${streamId}`)
    setIsLoading(true)
    setError(null)

    try {
      const eventSource = new EventSource(`/api/streams/${streamId}/motion/metrics/stream`)
      eventSourceRef.current = eventSource

      // Handle incoming metric data
      eventSource.onmessage = (event: MessageEvent) => {
        try {
          const data = JSON.parse(event.data) as MotionDetectionMetrics
          setMetrics(data)
          setIsLoading(false)
          setIsConnected(true)
          setError(null)

          // Reset reconnect attempts on successful message
          reconnectAttemptsRef.current = 0
        } catch (parseError) {
          console.error(`[useStreamMetrics] Failed to parse SSE data for stream ${streamId}:`, parseError)
          setError('Failed to parse metrics data')
        }
      }

      // Handle connection open
      eventSource.onopen = () => {
        console.log(`[useStreamMetrics] SSE connection opened for stream ${streamId}`)
        setIsConnected(true)
        setIsLoading(false)
        reconnectAttemptsRef.current = 0
      }

      // Handle connection errors
      eventSource.onerror = (event) => {
        console.error(`[useStreamMetrics] SSE connection error for stream ${streamId}:`, event)
        setIsConnected(false)
        setIsLoading(false)

        // Close the failed connection
        if (eventSourceRef.current) {
          eventSourceRef.current.close()
          eventSourceRef.current = null
        }

        // Attempt reconnection if enabled and under max attempts
        if (autoReconnect && reconnectAttemptsRef.current < maxReconnectAttempts) {
          const delay = reconnectDelay * Math.pow(2, reconnectAttemptsRef.current)
          reconnectAttemptsRef.current += 1

          console.log(
            `[useStreamMetrics] Reconnecting to ${streamId} in ${delay}ms ` +
            `(attempt ${reconnectAttemptsRef.current}/${maxReconnectAttempts})`
          )

          setError(`Connection lost. Reconnecting... (attempt ${reconnectAttemptsRef.current}/${maxReconnectAttempts})`)

          reconnectTimeoutRef.current = setTimeout(() => {
            connect()
          }, delay)
        } else {
          setError('Live metrics unavailable - connection lost')
        }
      }
    } catch (err) {
      console.error(`[useStreamMetrics] Failed to create EventSource for ${streamId}:`, err)
      setError('Failed to connect to metrics stream')
      setIsLoading(false)
      setIsConnected(false)
    }
  }, [streamId, autoReconnect, maxReconnectAttempts, reconnectDelay])

  /**
   * Disconnect from SSE endpoint
   * Cleans up EventSource and cancels any pending reconnection attempts
   */
  const disconnect = useCallback(() => {
    console.log(`[useStreamMetrics] Disconnecting from stream ${streamId}`)

    // Mark that we should not auto-reconnect
    shouldConnectRef.current = false

    // Close EventSource connection
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
      eventSourceRef.current = null
    }

    // Cancel any pending reconnection
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = null
    }

    // Reset state
    setIsConnected(false)
    setIsLoading(false)
    reconnectAttemptsRef.current = 0
  }, [streamId])

  /**
   * Manually trigger reconnection
   * Resets reconnect attempts counter
   */
  const reconnect = useCallback(() => {
    console.log(`[useStreamMetrics] Manual reconnect requested for ${streamId}`)
    shouldConnectRef.current = true
    reconnectAttemptsRef.current = 0
    disconnect()
    connect()
  }, [streamId, connect, disconnect])

  // ============================================================================
  // Auto-connect Effect
  // ============================================================================

  /**
   * Automatically connect on mount if autoConnect is enabled
   * Cleanup: Disconnect on unmount
   */
  useEffect(() => {
    if (autoConnect) {
      connect()
    }

    // Cleanup: Disconnect when component unmounts or streamId changes
    return () => {
      disconnect()
    }
  }, [streamId, autoConnect, connect, disconnect])

  // ============================================================================
  // Return Public API
  // ============================================================================

  return {
    metrics,
    isLoading,
    error,
    isConnected,
    reconnect,
    disconnect
  }
}
