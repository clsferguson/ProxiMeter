/**
 * Custom hook for stream management
 * Handles fetching, creating, updating, and deleting streams
 */

import { useState, useEffect, useCallback } from 'react'
import { streamApi } from '@/services/api'
import type { StreamResponse, NewStreamRequest, EditStreamRequest } from '@/lib/types'

interface UseStreamsOptions {
  autoFetch?: boolean
  pollInterval?: number
}

interface UseStreamsReturn {
  streams: StreamResponse[]
  isLoading: boolean
  error: string | null
  refetch: () => Promise<void>
  createStream: (data: NewStreamRequest) => Promise<StreamResponse>
  updateStream: (id: string, data: EditStreamRequest) => Promise<StreamResponse>
  deleteStream: (id: string) => Promise<void>
  reorderStreams: (order: string[]) => Promise<void>
}

/**
 * Hook for managing streams with automatic polling
 */
export function useStreams(options: UseStreamsOptions = {}): UseStreamsReturn {
  const { autoFetch = true, pollInterval } = options

  const [streams, setStreams] = useState<StreamResponse[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

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

  // Add scores state
  const [scores, setScores] = useState<Record<string, any>>({})

  useEffect(() => {
    streams.forEach(s => {
      if (s.status === 'running' && !scores[s.id]) {
        const eventSource = new EventSource(`/api/streams/${s.id}/scores`)
        eventSource.onmessage = (event) => {
          const data = JSON.parse(event.data)
          setScores(prev => ({...prev, [s.id]: data}))
        }
        eventSource.onerror = () => eventSource.close()
      }
    })
  }, [streams])


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

  const updateStream = useCallback(async (id: string, data: EditStreamRequest): Promise<StreamResponse> => {
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

  const deleteStream = useCallback(async (id: string): Promise<void> => {
    try {
      setError(null)
      await streamApi.deleteStream(id)
      setStreams(prev => prev.filter(s => s.id !== id))
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to delete stream'
      setError(errorMessage)
      throw err
    }
  }, [])

  const reorderStreams = useCallback(async (order: string[]): Promise<void> => {
    try {
      setError(null)
      await streamApi.reorderStreams(order)
      // Optimistically update local state
      const reordered = order.map(id => streams.find(s => s.id === id)).filter(Boolean) as StreamResponse[]
      setStreams(reordered)
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to reorder streams'
      setError(errorMessage)
      throw err
    }
  }, [streams])

  // Initial fetch
  useEffect(() => {
    if (autoFetch) {
      fetchStreams()
    }
  }, [autoFetch, fetchStreams])

  // Polling
  useEffect(() => {
    if (!pollInterval || pollInterval <= 0) {
      return
    }

    const intervalId = setInterval(() => {
      fetchStreams()
    }, pollInterval)

    return () => clearInterval(intervalId)
  }, [pollInterval, fetchStreams])

  return {
    streams,
    isLoading,
    error,
    refetch: fetchStreams,
    createStream,
    updateStream,
    deleteStream,
    reorderStreams,
  }
}
