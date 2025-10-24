/**
 * Custom hook for API state management
 * Provides loading, error, and data state for async operations
 */

import { useState, useCallback } from 'react'

interface UseApiState<T> {
  data: T | null
  isLoading: boolean
  error: string | null
}

interface UseApiReturn<T, Args extends unknown[]> extends UseApiState<T> {
  execute: (...args: Args) => Promise<T | null>
  reset: () => void
  setData: (data: T | null) => void
}

/**
 * Hook for managing async API calls with loading and error states
 */
export function useApi<T, Args extends unknown[] = []>(
  apiFunction: (...args: Args) => Promise<T>
): UseApiReturn<T, Args> {
  const [state, setState] = useState<UseApiState<T>>({
    data: null,
    isLoading: false,
    error: null,
  })

  const execute = useCallback(
    async (..._args: Args): Promise<T | null> => {
      try {
        setState(prev => ({ ...prev, isLoading: true, error: null }))
        const result = await apiFunction(..._args)
        setState({ data: result, isLoading: false, error: null })
        return result
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'An error occurred'
        setState(prev => ({ ...prev, isLoading: false, error: errorMessage }))
        return null
      }
    },
    [apiFunction]
  )

  const reset = useCallback(() => {
    setState({ data: null, isLoading: false, error: null })
  }, [])

  const setData = useCallback((data: T | null) => {
    setState(prev => ({ ...prev, data }))
  }, [])

  return {
    ...state,
    execute,
    reset,
    setData,
  }
}

export async function getGpuBackend(): Promise<{gpu_backend: string}> {
  const response = await fetch('/api/streams/gpu-backend')
  if (!response.ok) throw new Error('Failed to fetch GPU backend')
  return response.json()
}


/**
 * Hook for managing form submission state
 */
export function useFormSubmit<T, Args extends unknown[] = []>(
  submitFunction: (...args: Args) => Promise<T>
) {
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  const submit = useCallback(
    async (..._args: Args): Promise<T | null> => {
      try {
        setIsSubmitting(true)
        setError(null)
        setSuccess(false)
        const result = await submitFunction(..._args)
        setSuccess(true)
        return result
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Submission failed'
        setError(errorMessage)
        return null
      } finally {
        setIsSubmitting(false)
      }
    },
    [submitFunction]
  )

  const reset = useCallback(() => {
    setIsSubmitting(false)
    setError(null)
    setSuccess(false)
  }, [])

  return {
    submit,
    isSubmitting,
    error,
    success,
    reset,
  }
}
