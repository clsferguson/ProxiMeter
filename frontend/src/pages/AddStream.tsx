/**
 * Add Stream page - Create a new RTSP stream
 * User Story 2: Add New Stream
 * 
 * Acceptance Scenarios:
 * 1. User navigates to add stream form and sees form with name, RTSP URL fields
 * 2. User enters valid stream details and submits - stream saved and appears in dashboard
 * 3. User enters invalid RTSP URL - sees validation error message
 */

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Layout from '@/components/Layout'
import { StreamForm } from '@/components/StreamForm'
import { useStreams } from '@/hooks/useStreams'

interface StreamFormData {
  name: string
  rtsp_url: string
}

export default function AddStream() {
  const navigate = useNavigate()
  const { createStream } = useStreams()
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (data: StreamFormData) => {
    try {
      setIsLoading(true)
      setError(null)
      await createStream(data)
      // Navigate back to dashboard after successful creation
      navigate('/')
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to add stream'
      setError(errorMessage)
      throw err
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <Layout>
      <div className="container mx-auto p-6">
        <div className="mb-8">
          <h1 className="text-3xl font-bold mb-2">Add Stream</h1>
          <p className="text-muted-foreground">
            Configure a new RTSP stream for monitoring
          </p>
        </div>

        <StreamForm
          onSubmit={handleSubmit}
          isLoading={isLoading}
          error={error}
          submitLabel="Add Stream"
          isEdit={false}
        />
      </div>
    </Layout>
  )
}
