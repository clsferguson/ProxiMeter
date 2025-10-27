/**
 * useStreams Hook - Stream Management with Real-time Updates
 * 
 * Provides comprehensive stream management functionality including:
 * - CRUD operations (Create, Read, Update, Delete)
 * - Automatic polling for status updates
 * - Real-time score streaming via Server-Sent Events (SSE)
 * - Stream reordering
 * 
 * @module hooks/useStreams
 */

import { useState, useEffect, useCallback } from 'react'
import { streamApi } from '@/services/api'
import type { StreamResponse, NewStreamRequest, EditStreamRequest } from '@/lib/types'

// ============================================================================
// Type Definitions
// ============================================================================

/**
 * Configuration options for the useStreams hook
 */
interface UseStreamsOptions {
  /** Whether to automatically fetch streams on mount (default: true) */
  autoFetch?: boolean
  /** Polling interval in milliseconds for status updates (default: disabled) */
  pollInterval?: number
}

/**
 * Score data structure received from SSE endpoint
 * Contains real-time detection metrics for person tracking
 */
interface ScoreData {
  distance?: number
  coordinates?: { x: number; y: number }
  size?: number
  [key: string]: unknown
}

/**
 * Return type for the useStreams hook
 */
interface UseStreamsReturn {
  /** Array of all streams */
  streams: StreamResponse[]
  /** Loading state for async operations */
  isLoading: boolean
  /** Error message if operation fails */
  error: string | null
  /** Real-time scores indexed by stream ID */
  scores: Record<string, ScoreData>
  /** Manually trigger a streams refresh */
  refetch: () => Promise<void>
  /** Create a new stream */
  createStream: (data: NewStreamRequest) => Promise<StreamResponse>
  /** Update an existing stream */
  updateStream: (id: string, data: EditStreamRequest) => Promise<StreamResponse>
  /** Delete a stream */
  deleteStream: (id: string) => Promise<void>
  /** Reorder streams by ID array */
  reorderStreams: (order: string[]) => Promise<void>
}

// ============================================================================
// Main Hook
// ============================================================================

/**
 * Custom hook for managing RTSP streams with real-time updates
 * 
 * Features:
 * - Automatic fetching on mount (configurable)
 * - Optional polling for periodic status updates
 * - SSE connections for real-time detection scores
 * - Optimistic updates for better UX
 * - Proper cleanup of EventSource connections
 * 
 * @param options - Configuration options
 * @returns Stream management interface
 * 
 * @example
 * ```
 * // Basic usage with auto-fetch
 * const { streams, isLoading, error } = useStreams({ autoFetch: true })
 * 
 * // With polling every 5 seconds
 * const { streams, refetch } = useStreams({ 
 *   autoFetch: true, 
 *   pollInterval: 5000 
 * })
 * 
 * // Manual control
 * const { streams, refetch, createStream } = useStreams({ autoFetch: false })
 * ```
 */
export function useStreams(options: UseStreamsOptions = {}): UseStreamsReturn {
  const { autoFetch = true, pollInterval } = options

  // ============================================================================
  // State Management
  // ============================================================================

  const [streams, setStreams] = useState<StreamResponse[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [scores, setScores] = useState<Record<string, ScoreData>>({})

  // ============================================================================
  // Stream Fetching
  // ============================================================================

  /**
   * Fetches all streams from the API
   * Updates loading and error states appropriately
   */
  const fetchStreams = useCallback(async () => {
    try {
      setIsLoading(true)
      setError(null)
      const data = await streamApi.getStreams()
      setStreams(data)
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch streams'
      setError(errorMessage)
      console.error('Error fetching streams:', err)
    } finally {
      setIsLoading(false)
    }
  }, [])

  // ============================================================================
  // Real-time Score Streaming (SSE)
  // ============================================================================

  /**
   * Establishes SSE connections for running streams to receive real-time scores
   * 
   * CRITICAL FIX: Does NOT include 'scores' in dependency array to prevent
   * infinite loop. The effect only re-runs when the streams array changes.
   * 
   * Cleanup: All EventSource connections are properly closed when:
   * - Component unmounts
   * - Streams array changes (old connections closed, new ones opened)
   */
  useEffect(() => {
    const eventSources: Record<string, EventSource> = {}

    // Create SSE connection for each running stream
    streams.forEach(stream => {
      if (stream.status === 'running') {
        const eventSource = new EventSource(`/api/streams/${stream.id}/scores`)
        eventSources[stream.id] = eventSource

        // Handle incoming score data
        eventSource.onmessage = (event: MessageEvent) => {
          try {
            const data = JSON.parse(event.data) as ScoreData
            // Update scores using functional update to avoid stale closure
            setScores(prev => ({ ...prev, [stream.id]: data }))
          } catch (parseError) {
            console.error(`Failed to parse SSE data for stream ${stream.id}:`, parseError)
          }
        }

        // Handle connection errors
        eventSource.onerror = (error) => {
          console.error(`SSE connection error for stream ${stream.id}:`, error)
          eventSource.close()
          delete eventSources[stream.id]
        }
      }
    })

    // Cleanup: Close all EventSource connections when effect re-runs or unmounts
    return () => {
      Object.entries(eventSources).forEach(([id, es]) => {
        console.log(`Closing SSE connection for stream ${id}`)
        es.close()
      })
    }
  }, [streams]) // Only depend on streams, NOT scores (prevents infinite loop)

  // ============================================================================
  // CRUD Operations
  // ============================================================================

  /**
   * Creates a new stream
   * Optimistically updates local state on success
   */
  const createStream = useCallback(async (data: NewStreamRequest): Promise<StreamResponse> => {
    try {
      setError(null)
      const newStream = await streamApi.createStream(data)
      setStreams(prev => [...prev, newStream])
      return newStream
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to create stream'
      setError(errorMessage)
      throw err
    }
  }, [])

  /**
   * Updates an existing stream
   * Optimistically updates local state on success
   */
  const updateStream = useCallback(async (
    id: string, 
    data: EditStreamRequest
  ): Promise<StreamResponse> => {
    try {
      setError(null)
      const updatedStream = await streamApi.updateStream(id, data)
      setStreams(prev => prev.map(s => s.id === id ? updatedStream : s))
      return updatedStream
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to update stream'
      setError(errorMessage)
      throw err
    }
  }, [])

  /**
   * Deletes a stream
   * Removes from local state on success
   */
  const deleteStream = useCallback(async (id: string): Promise<void> => {
    try {
      setError(null)
      await streamApi.deleteStream(id)
      setStreams(prev => prev.filter(s => s.id !== id))
      // Clean up associated scores
      setScores(prev => {
        const updated = { ...prev }
        delete updated[id]
        return updated
      })
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to delete stream'
      setError(errorMessage)
      throw err
    }
  }, [])

  /**
   * Reorders streams based on provided ID array
   * Optimistically updates local state
   */
  const reorderStreams = useCallback(async (order: string[]): Promise<void> => {
    try {
      setError(null)
      await streamApi.reorderStreams(order)
      
      // Optimistically reorder local state
      const reordered = order
        .map(id => streams.find(s => s.id === id))
        .filter(Boolean) as StreamResponse[]
      
      setStreams(reordered)
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to reorder streams'
      setError(errorMessage)
      throw err
    }
  }, [streams])

  // ============================================================================
  // Initial Fetch Effect
  // ============================================================================

  /**
   * Automatically fetches streams on mount if autoFetch is enabled
   */
  useEffect(() => {
    if (autoFetch) {
      fetchStreams()
    }
  }, [autoFetch, fetchStreams])

  // ============================================================================
  // Polling Effect
  // ============================================================================

  /**
   * Sets up periodic polling for stream status updates
   * Only runs if pollInterval is provided and greater than 0
   */
  useEffect(() => {
    // Skip if polling is disabled
    if (!pollInterval || pollInterval <= 0) {
      return
    }

    const intervalId = setInterval(() => {
      fetchStreams()
    }, pollInterval)

    // Cleanup: Clear interval on unmount or when pollInterval changes
    return () => clearInterval(intervalId)
  }, [pollInterval, fetchStreams])

  // ============================================================================
  // Return Public API
  // ============================================================================

  return {
    streams,
    isLoading,
    error,
    scores,
    refetch: fetchStreams,
    createStream,
    updateStream,
    deleteStream,
    reorderStreams,
  }
}
