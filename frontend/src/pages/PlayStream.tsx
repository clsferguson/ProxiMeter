/**
 * PlayStream Page - Live MJPEG Stream Viewer
 * 
 * User Story 4: Play Live Stream
 * 
 * Displays live MJPEG stream from backend with:
 * - Stream metadata display
 * - Minimal overlays (removed unnecessary scores)
 * - Back navigation to dashboard
 * - Efficient error handling and loading states
 * - Auto-retry on connection loss
 * 
 * Constitution-compliant: 5fps streaming, full resolution
 * 
 * Performance Optimizations:
 * - Removed SSE score streaming (not yet implemented)
 * - Simplified state management
 * - Single img tag for MJPEG (browser handles multipart)
 * - Proper cleanup on unmount
 * - Memoized stream lookup to avoid re-renders
 * 
 * @module pages/PlayStream
 */

import { useEffect, useState, useMemo, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import Layout from '@/components/Layout'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { AlertCircle, ArrowLeft, Activity, Video, RefreshCw } from 'lucide-react'
import { useStreams } from '@/hooks/useStreams'
import { API_BASE_URL } from '@/lib/constants'
import type { StreamResponse } from '@/lib/types'

// ============================================================================
// Main Component
// ============================================================================

/**
 * PlayStream Page Component
 * 
 * Displays live MJPEG stream at 5fps per constitution requirements.
 * Uses native browser multipart/x-mixed-replace handling via <img> tag.
 */
export default function PlayStream() {
  const { streamId } = useParams<{ streamId: string }>()
  const navigate = useNavigate()
  const { streams, isLoading, error } = useStreams()
  
  // Simple state management - removed unnecessary SSE scores
  const [imageError, setImageError] = useState(false)
  const [retryCount, setRetryCount] = useState(0)

  // ========================================================================
  // Derived State - Find Stream (Memoized for Performance)
  // ========================================================================
  
  /**
   * Find the current stream from the streams list using useMemo.
   * This avoids calling setState inside an effect and prevents
   * unnecessary re-renders when streams list updates.
   */
  const stream = useMemo<StreamResponse | null>(() => {
    if (!streamId || streams.length === 0) {
      return null
    }
    return streams.find(s => s.id === streamId) || null
  }, [streamId, streams])

  // ========================================================================
  // Event Handlers (Memoized)
  // ========================================================================
  
  const handleBack = useCallback(() => {
    navigate('/')
  }, [navigate])

  const handleImageError = useCallback(() => {
    setImageError(true)
  }, [])

  const handleImageLoad = useCallback(() => {
    // Successfully loaded/reloaded stream
    setImageError(false)
    if (retryCount > 0) {
      setRetryCount(0)
    }
  }, [retryCount])

  const handleRetry = useCallback(() => {
    setImageError(false)
    setRetryCount(prev => prev + 1)
  }, [])

  // ========================================================================
  // Auto-Retry on Error (Optional - can be removed if not desired)
  // ========================================================================
  
  useEffect(() => {
    if (!imageError || !stream || stream.status !== 'running') {
      return
    }

    // Auto-retry after 5 seconds, up to 3 times
    if (retryCount < 3) {
      const timer = setTimeout(() => {
        handleRetry()
      }, 5000)

      return () => clearTimeout(timer)
    }
  }, [imageError, stream, retryCount, handleRetry])

  // ========================================================================
  // Build Stream URL (Only if Stream is Running)
  // ========================================================================
  
  const streamUrl = useMemo(() => {
    if (!stream || stream.status !== 'running') {
      return null
    }
    // Add retry count to force reload on retry
    return `${API_BASE_URL}/streams/${stream.id}/mjpeg?t=${retryCount}`
  }, [stream, retryCount])

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
                  {!imageError && streamUrl ? (
                    <img
                      src={streamUrl}
                      alt={`${stream.name} live stream`}
                      className="absolute inset-0 w-full h-full object-contain"
                      onError={handleImageError}
                      onLoad={handleImageLoad}
                      style={{
                        imageRendering: 'auto',
                      }}
                    />
                  ) : (
                    <div className="absolute inset-0 flex items-center justify-center bg-black/90">
                      <div className="text-center text-white max-w-md px-6">
                        <AlertCircle className="h-12 w-12 mx-auto mb-4 opacity-50" />
                        <p className="text-lg font-semibold mb-2">Stream Unavailable</p>
                        <p className="text-sm opacity-75 mb-4">
                          Cannot connect to stream. Verify:<br />
                          • RTSP stream is accessible<br />
                          • FFmpeg process is running<br />
                          • Stream is started on dashboard
                        </p>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={handleRetry}
                          className="bg-white/10 hover:bg-white/20"
                        >
                          <RefreshCw className="h-4 w-4 mr-2" />
                          Retry Connection {retryCount > 0 && `(Attempt ${retryCount + 1}/3)`}
                        </Button>
                      </div>
                    </div>
                  )}
                </div>
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
                <p>
                  <strong className="text-foreground">Protocol:</strong> multipart/x-mixed-replace
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
