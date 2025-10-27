/**
 * PlayStream Page - Live MJPEG Stream Viewer
 * 
 * User Story 4: Play Live Stream
 * 
 * Displays live MJPEG stream from backend in a contained card with:
 * - Stream metadata display
 * - Real-time detection scores overlay
 * - Back navigation to dashboard
 * - Error handling and loading states
 * 
 * Constitution-compliant: 5fps streaming, full resolution
 * 
 * @module pages/PlayStream
 */

import { useEffect, useState, useMemo } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import Layout from '@/components/Layout'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { AlertCircle, ArrowLeft, Activity, Video } from 'lucide-react'
import { useStreams } from '@/hooks/useStreams'
import type { StreamResponse } from '@/lib/types'

// ============================================================================
// Types
// ============================================================================

interface ScoreData {
  timestamp: string
  distance?: number
  coordinates?: { x: number; y: number }
  size?: number
}

// ============================================================================
// Main Component
// ============================================================================

/**
 * PlayStream Page Component
 * 
 * Displays live MJPEG stream in a contained card layout with metadata.
 * Stream loads at 5fps per constitution requirements.
 */
export default function PlayStream() {
  const { streamId } = useParams<{ streamId: string }>()
  const navigate = useNavigate()
  const { streams, isLoading, error } = useStreams()
  
  const [scores, setScores] = useState<ScoreData | null>(null)
  const [imageError, setImageError] = useState(false)

  // ========================================================================
  // Derived State - Find Stream (No setState in Effect!)
  // ========================================================================
  
  /**
   * Find the current stream from the streams list using useMemo.
   * This avoids calling setState inside an effect, which can cause
   * cascading renders and performance issues.
   */
  const stream = useMemo<StreamResponse | null>(() => {
    if (!streamId || streams.length === 0) {
      return null
    }
    return streams.find(s => s.id === streamId) || null
  }, [streamId, streams])

// ========================================================================
// SSE Score Streaming
// ========================================================================

/**
 * Subscribe to Server-Sent Events for real-time detection scores.
 * Only connects when stream exists and is running.
 * 
 * Uses stream object directly in dependencies to avoid optional chaining.
 */
useEffect(() => {
  // Early return if no stream or not running
  if (!stream || stream.status !== 'running') {
    return
  }

  let eventSource: EventSource | null = null

  try {
    eventSource = new EventSource(`/api/streams/${stream.id}/scores`)
    
    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as ScoreData
        setScores(data)
      } catch (err) {
        console.error('Failed to parse score data:', err)
      }
    }
    
    eventSource.onerror = (err) => {
      console.error('SSE error:', err)
      eventSource?.close()
    }
    
  } catch (err) {
    console.error('Failed to create EventSource:', err)
  }

  return () => {
    eventSource?.close()
  }
}, [stream])


  // ========================================================================
  // Event Handlers
  // ========================================================================
  
  const handleBack = () => {
    navigate('/')
  }

  const handleImageError = () => {
    setImageError(true)
  }


  // ========================================================================
  // Render: Loading State
  // ========================================================================
  
  if (isLoading) {
    return (
      <Layout>
        <div className="container mx-auto p-6 max-w-7xl">
          <Button
            variant="ghost"
            size="sm"
            onClick={handleBack}
            className="mb-6"
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Dashboard
          </Button>
          <Card>
            <CardContent className="py-12">
              <div className="text-center">
                <Activity className="h-8 w-8 mx-auto mb-4 text-muted-foreground animate-pulse" />
                <p className="text-muted-foreground">Loading stream...</p>
              </div>
            </CardContent>
          </Card>
        </div>
      </Layout>
    )
  }


  // ========================================================================
  // Render: Error State
  // ========================================================================
  
  if (error) {
    return (
      <Layout>
        <div className="container mx-auto p-6 max-w-7xl">
          <Button
            variant="ghost"
            size="sm"
            onClick={handleBack}
            className="mb-6"
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Dashboard
          </Button>
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              Failed to load stream: {error}
            </AlertDescription>
          </Alert>
        </div>
      </Layout>
    )
  }


  // ========================================================================
  // Render: Stream Not Found
  // ========================================================================
  
  if (!stream) {
    return (
      <Layout>
        <div className="container mx-auto p-6 max-w-7xl">
          <Button
            variant="ghost"
            size="sm"
            onClick={handleBack}
            className="mb-6"
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Dashboard
          </Button>
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              Stream not found. It may have been deleted.
            </AlertDescription>
          </Alert>
        </div>
      </Layout>
    )
  }


  // ========================================================================
  // Render: Stream Display
  // ========================================================================
  
 // const streamUrl = `/api/streams/${stream.id}/mjpeg?t=${imageKey}`

  return (
    <Layout>
      <div className="container mx-auto p-6 max-w-7xl">
        
        {/* Header with back button */}
        <div className="flex items-center gap-4 mb-6">
          <Button
            variant="ghost"
            size="sm"
            onClick={handleBack}
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back
          </Button>
          <div className="flex-1">
            <h1 className="text-2xl font-bold">{stream.name}</h1>
            <p className="text-sm text-muted-foreground">Live Stream (5 FPS)</p>
          </div>
          <Badge variant={stream.status === 'running' ? 'default' : 'secondary'}>
            {stream.status === 'running' ? 'Running' : 'Stopped'}
          </Badge>
        </div>

        {/* Main stream card */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Video className="h-5 w-5" />
              Live View
            </CardTitle>
            <CardDescription>
              Real-time MJPEG stream at 5 FPS, full resolution
            </CardDescription>
          </CardHeader>
          <CardContent>
            {stream.status !== 'running' ? (
              <Alert>
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>
                  Stream is not running. Start the stream from the dashboard to view live video.
                </AlertDescription>
              </Alert>
            ) : (
              <div className="relative w-full bg-black rounded-lg overflow-hidden">
                {/* Video display - MJPEG multipart stream */}
                <div className="relative w-full" style={{ paddingBottom: '56.25%' }}>
                  {!imageError ? (
                    <img
                      src={`/api/streams/${stream.id}/mjpeg`}
                      alt={`${stream.name} live stream`}
                      className="absolute inset-0 w-full h-full object-contain"
                      onError={handleImageError}
                      style={{
                        imageRendering: 'auto',
                      }}
                    />
                  ) : (
                    <div className="absolute inset-0 flex items-center justify-center bg-black/90">
                      <div className="text-center text-white">
                        <AlertCircle className="h-12 w-12 mx-auto mb-4 opacity-50" />
                        <p className="text-lg font-semibold mb-2">Stream Unavailable</p>
                        <p className="text-sm opacity-75 max-w-md mx-auto">
                          Cannot connect to stream. Verify:
                          <br />• RTSP stream is accessible
                          <br />• FFmpeg process is running
                          <br />• Stream is started on dashboard
                        </p>
                        <Button
                          variant="outline"
                          size="sm"
                          className="mt-4"
                          onClick={() => {
                            setImageError(false)
                          }}
                        >
                          Retry Connection
                        </Button>
                      </div>
                    </div>
                  )}
                </div>

                {/* Scores overlay */}
                {scores && !imageError && (
                  <div className="absolute bottom-4 left-4 right-4">
                    <div className="bg-black/70 backdrop-blur-sm text-white px-4 py-2 rounded-lg border border-white/20">
                      <div className="flex flex-wrap gap-4 text-sm font-mono">
                        {scores.distance !== undefined && (
                          <span>Distance: {scores.distance.toFixed(2)}</span>
                        )}
                        {scores.coordinates && (
                          <span>
                            Position: ({scores.coordinates.x.toFixed(2)}, {scores.coordinates.y.toFixed(2)})
                          </span>
                        )}
                        {scores.size !== undefined && (
                          <span>Size: {scores.size}</span>
                        )}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Stream metadata grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Card>
            <CardHeader>
              <CardTitle>Stream Details</CardTitle>
            </CardHeader>
            <CardContent>
              <dl className="space-y-3 text-sm">
                <div className="flex justify-between items-center">
                  <dt className="text-muted-foreground">Name</dt>
                  <dd className="font-medium">{stream.name}</dd>
                </div>
                <div className="flex justify-between items-center">
                  <dt className="text-muted-foreground">Status</dt>
                  <dd>
                    <Badge variant={stream.status === 'running' ? 'default' : 'secondary'}>
                      {stream.status}
                    </Badge>
                  </dd>
                </div>
                <div className="flex justify-between items-center">
                  <dt className="text-muted-foreground">GPU Acceleration</dt>
                  <dd className="font-medium">
                    {stream.hw_accel_enabled ? 'Enabled' : 'Disabled'}
                  </dd>
                </div>
                <div className="flex justify-between items-center">
                  <dt className="text-muted-foreground">Auto Start</dt>
                  <dd className="font-medium">
                    {stream.auto_start ? 'Enabled' : 'Disabled'}
                  </dd>
                </div>
              </dl>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Playback Info</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3 text-sm text-muted-foreground">
                <p>
                  <strong className="text-foreground">Frame Rate:</strong> 5 FPS (constitution-mandated cap)
                </p>
                <p>
                  <strong className="text-foreground">Resolution:</strong> Original (no scaling)
                </p>
                <p>
                  <strong className="text-foreground">Format:</strong> MJPEG over HTTP
                </p>
                <p className="text-xs pt-2">
                  If playback fails, verify the RTSP stream is accessible and the backend FFmpeg process is running.
                </p>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </Layout>
  )
}
