/**
 * Dashboard page - View all configured RTSP streams
 * User Story 1: View Stream Dashboard
 * 
 * Displays all configured streams with real-time status indicators
 * Status updates every 2 seconds with visual feedback (green/yellow/red)
 */

import { useEffect, useState } from 'react'
import Layout from '@/components/Layout'
import StreamCard from '@/components/StreamCard'
import EmptyState from '@/components/EmptyState'
import { useStreams } from '@/hooks/useStreams'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { AlertCircle } from 'lucide-react'

export default function Dashboard() {
  const { streams, isLoading, error, refetch } = useStreams({ autoFetch: true, pollInterval: 2000 })
  const [metrics, setMetrics] = useState<Record<string, number>>({})

  useEffect(() => {
    // Set up polling for real-time status updates every 2 seconds
    const pollInterval = setInterval(() => {
      refetch()
    }, 2000)

    return () => clearInterval(pollInterval)
  }, [refetch])

  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        const res = await fetch('/api/metrics')
        const data = await res.text()  // Prometheus text
        // Parse simple gauges, e.g., stream_fps{stream_id="id"} 5
        const fpsMap: Record<string, number> = {}
        data.split('\n').forEach(line => {
          if (line.includes('stream_fps{stream_id="') ) {
            const match = line.match(/stream_fps\{stream_id="([^"]+)"\}\s+(\d+\.?\d*)/)
            if (match) fpsMap[match[1]] = parseFloat(match[2])
          }
        })
        setMetrics(fpsMap)
      } catch (err) {
        console.error('Failed to fetch metrics:', err)
      }
    }
    fetchMetrics()
    const interval = setInterval(fetchMetrics, 5000)
    return () => clearInterval(interval)
  }, [])

  const handleRetry = () => {
    refetch()
  }

  return (
    <Layout>
      <div className="min-h-screen">
        {/* Page Header */}
        <div className="bg-linear-to-br from-primary/5 to-primary/10 border-b">
          <div className="container mx-auto px-4 py-8 md:py-12">
            <h1 className="text-4xl md:text-5xl font-bold text-foreground mb-2">Stream Dashboard</h1>
            <p className="text-muted-foreground">Monitor your RTSP streams in real-time</p>
          </div>
        </div>

        {/* Main Content */}
        <main className="container mx-auto px-4 py-8">
          {/* Loading State */}
          {isLoading && streams.length === 0 && (
            <div className="flex items-center justify-center py-12">
              <div className="text-center">
                <div className="inline-block h-12 w-12 animate-spin rounded-full border-4 border-muted border-t-primary"></div>
                <p className="mt-4 text-muted-foreground">Loading streams...</p>
              </div>
            </div>
          )}

          {/* Error State */}
          {error && streams.length === 0 && (
            <div className="space-y-4">
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>
                  <div className="flex flex-col gap-3">
                    <div>{error}</div>
                    <button
                      onClick={handleRetry}
                      className="inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50 bg-destructive text-destructive-foreground hover:bg-destructive/90 h-10 px-4 py-2 w-fit"
                    >
                      Retry
                    </button>
                  </div>
                </AlertDescription>
              </Alert>
            </div>
          )}

          {/* Empty State */}
          {!isLoading && !error && streams.length === 0 && <EmptyState />}

          {/* Streams Grid */}
          {streams.length > 0 && (
            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 auto-rows-max">
                {streams.map(stream => (
                  <StreamCard key={stream.id} stream={stream} />
                ))}
              </div>
            </div>
          )}
        </main>
      </div>
    </Layout>
  )
}
