/**
 * Dashboard page - View all configured RTSP streams
 * User Story 1: View Stream Dashboard
 * 
 * Displays all configured streams with real-time status indicators
 * Status updates every 2 seconds with visual feedback (green/yellow/red)
 */

import { useEffect } from 'react'
import Layout from '@/components/Layout'
import StreamCard from '@/components/StreamCard'
import EmptyState from '@/components/EmptyState'
import { useStreams } from '@/hooks/useStreams'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { AlertCircle } from 'lucide-react'

export default function Dashboard() {
  const { streams, isLoading, error, refetch } = useStreams({ autoFetch: true, pollInterval: 2000 })

  useEffect(() => {
    // Set up polling for real-time status updates every 2 seconds
    const pollInterval = setInterval(() => {
      refetch()
    }, 2000)

    return () => clearInterval(pollInterval)
  }, [refetch])

  const handleRetry = () => {
    refetch()
  }

  return (
    <Layout>
      {/* Page Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">Stream Dashboard</h1>
        <p className="text-muted-foreground">Monitor your RTSP streams in real-time</p>
      </div>

      {/* Main Content */}
      <div className="space-y-6">
        {/* Loading State */}
        {isLoading && streams.length === 0 && (
          <div className="text-center py-12">Loading streams...</div>
        )}

        {/* Error State */}
        {error && streams.length === 0 && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
            <button onClick={handleRetry}>Retry</button>
          </Alert>
        )}

        {/* Empty State */}
        {!isLoading && !error && streams.length === 0 && <EmptyState />}

        {/* Streams Grid */}
        {streams.length > 0 && (
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {streams.map(stream => (
              <StreamCard key={stream.id} stream={stream} />
            ))}
          </div>
        )}
      </div>
    </Layout>
  )
}
