/**
 * PlayStream Page - Live MJPEG Stream Viewer
 * 
 * Displays CONTINUOUS live MJPEG stream at 5fps. No overlays, no scores.
 * Just the pure video stream.
 * 
 * @module pages/PlayStream
 */

import { useState, useMemo, useCallback } from 'react'
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

export default function PlayStream() {
  const { streamId } = useParams<{ streamId: string }>()
  const navigate = useNavigate()
  const { streams, isLoading, error } = useStreams()
  
  const [imageError, setImageError] = useState(false)

  const stream = useMemo<StreamResponse | null>(() => {
    if (!streamId || streams.length === 0) return null
    return streams.find(s => s.id === streamId) || null
  }, [streamId, streams])

  const handleBack = useCallback(() => navigate('/'), [navigate])
  const handleImageError = useCallback(() => setImageError(true), [])
  const handleRetry = useCallback(() => setImageError(false), [])

  // MJPEG stream URL - continuous live stream
  const streamUrl = useMemo(() => {
    if (!stream || stream.status !== 'running') return null
    return `${API_BASE_URL}/streams/${stream.id}/mjpeg`
  }, [stream])

  if (isLoading) {
    return (
      <Layout>
        <div className="container mx-auto p-6 max-w-7xl">
          <Button variant="ghost" size="sm" onClick={handleBack} className="mb-6">
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

  if (error) {
    return (
      <Layout>
        <div className="container mx-auto p-6 max-w-7xl">
          <Button variant="ghost" size="sm" onClick={handleBack} className="mb-6">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Dashboard
          </Button>
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>Failed to load stream: {error}</AlertDescription>
          </Alert>
        </div>
      </Layout>
    )
  }

  if (!stream) {
    return (
      <Layout>
        <div className="container mx-auto p-6 max-w-7xl">
          <Button variant="ghost" size="sm" onClick={handleBack} className="mb-6">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Dashboard
          </Button>
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>Stream not found. It may have been deleted.</AlertDescription>
          </Alert>
        </div>
      </Layout>
    )
  }

  return (
    <Layout>
      <div className="container mx-auto p-6 max-w-7xl">
        
        <div className="flex items-center gap-4 mb-6">
          <Button variant="ghost" size="sm" onClick={handleBack}>
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
                {/* LIVE MJPEG STREAM - NO OVERLAYS */}
                <div className="relative w-full" style={{ paddingBottom: '56.25%' }}>
                  {!imageError && streamUrl ? (
                    <img
                      src={streamUrl}
                      alt={`${stream.name} live stream`}
                      className="absolute inset-0 w-full h-full object-contain"
                      onError={handleImageError}
                    />
                  ) : (
                    <div className="absolute inset-0 flex items-center justify-center bg-black/90">
                      <div className="text-center text-white max-w-md px-6">
                        <AlertCircle className="h-12 w-12 mx-auto mb-4 opacity-50" />
                        <p className="text-lg font-semibold mb-2">Stream Unavailable</p>
                        <p className="text-sm opacity-75 mb-4">
                          Cannot connect to stream.
                        </p>
                        <Button variant="outline" size="sm" onClick={handleRetry}>
                          <RefreshCw className="h-4 w-4 mr-2" />
                          Retry Connection
                        </Button>
                      </div>
                    </div>
                  )}
                </div>
                {/* NO SCORES OVERLAY - removed */}
              </div>
            )}
          </CardContent>
        </Card>

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
              </dl>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Playback Info</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3 text-sm text-muted-foreground">
                <p><strong className="text-foreground">Frame Rate:</strong> 5 FPS</p>
                <p><strong className="text-foreground">Resolution:</strong> Original (no scaling)</p>
                <p><strong className="text-foreground">Format:</strong> MJPEG over HTTP</p>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </Layout>
  )
}
