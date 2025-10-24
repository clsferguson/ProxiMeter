/**
 * Play Stream page - View live RTSP stream
 * User Story 4: Play Live Stream
 * 
 * Displays a live MJPEG stream from the backend with controls and error handling.
 * Uses shadcn/ui components for consistent styling and accessibility.
 */

import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import Layout from '@/components/Layout'
import VideoPlayer from '@/components/VideoPlayer'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { AlertCircle, ArrowLeft } from 'lucide-react'
import { useStreams } from '@/hooks/useStreams'
import type { StreamResponse } from '@/lib/types'

interface ScoreData {
  timestamp: string
  distance: number
  coordinates: { x: number; y: number }
  size: number
}

export default function PlayStream() {
  const { streamId } = useParams<{ streamId: string }>()
  const navigate = useNavigate()
  const { streams, isLoading, error } = useStreams()
  const [stream, setStream] = useState<StreamResponse | null>(null)
  const [scores, setScores] = useState<Record<string, ScoreData>>({})

  useEffect(() => {
    if (streams.length > 0) {
      const found = streams.find(s => s.id === streamId)
      setStream(found || null)
    }
  }, [streamId, streams])

  useEffect(() => {
    if (stream?.status === 'running' || stream?.status === 'Active') {
      const eventSource = new EventSource(`/api/streams/${stream.id}/scores`)
      eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data) as ScoreData
        setScores(prev => ({...prev, [stream.id]: data}))
      }
      eventSource.onerror = () => eventSource.close()
      return () => eventSource.close()
    }
  }, [stream?.id, stream?.status])

  if (isLoading) {
    return (
      <Layout>
        <div className="container mx-auto p-6">
          <div className="flex items-center gap-2 mb-6">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => navigate('/')}
              className="gap-2"
            >
              <ArrowLeft className="h-4 w-4" />
              Back
            </Button>
          </div>
          <div className="text-center py-12">
            <p className="text-muted-foreground">Loading stream...</p>
          </div>
        </div>
      </Layout>
    )
  }

  if (error) {
    return (
      <Layout>
        <div className="container mx-auto p-6">
          <div className="flex items-center gap-2 mb-6">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => navigate('/')}
              className="gap-2"
            >
              <ArrowLeft className="h-4 w-4" />
              Back
            </Button>
          </div>
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

  if (!stream) {
    return (
      <Layout>
        <div className="container mx-auto p-6">
          <div className="flex items-center gap-2 mb-6">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => navigate('/')}
              className="gap-2"
            >
              <ArrowLeft className="h-4 w-4" />
              Back
            </Button>
          </div>
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              Stream not found. Please select a valid stream from the dashboard.
            </AlertDescription>
          </Alert>
        </div>
      </Layout>
    )
  }

  return (
    <Layout>
      <div className="container mx-auto p-6">
        {/* Header with back button */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-4">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => navigate('/')}
              className="gap-2"
            >
              <ArrowLeft className="h-4 w-4" />
              Back to Dashboard
            </Button>
            <div>
              <h1 className="text-3xl font-bold">{stream.name}</h1>
              <p className="text-sm text-muted-foreground mt-1">
                {stream.rtsp_url}
              </p>
            </div>
          </div>
        </div>

        {/* Video player with scores overlay */}
        <div className="relative bg-black rounded-lg overflow-hidden">
          <VideoPlayer streamId={stream.id} rtspUrl={stream.rtsp_url} />
          {scores[stream.id] && (
            <div className="absolute bottom-4 left-4 right-4 bg-black/50 text-white p-2 rounded text-sm">
              Dist: {scores[stream.id].distance.toFixed(2)} | 
              Pos: ({scores[stream.id].coordinates.x.toFixed(2)}, {scores[stream.id].coordinates.y.toFixed(2)}) | 
              Size: {scores[stream.id].size}
            </div>
          )}
        </div>

        {/* Stream info */}
        <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-card border rounded-lg p-4">
            <h3 className="font-semibold mb-2">Stream Details</h3>
            <dl className="space-y-2 text-sm">
              <div className="flex justify-between">
                <dt className="text-muted-foreground">Name:</dt>
                <dd className="font-medium">{stream.name}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-muted-foreground">Status:</dt>
                <dd className="font-medium">
                  <span className={`inline-block w-2 h-2 rounded-full mr-2 ${
                    stream.status === 'Active' ? 'bg-green-500' : 'bg-yellow-500'
                  }`} />
                  {stream.status === 'Active' ? 'Active' : 'Inactive'}
                </dd>
              </div>
            </dl>
          </div>
          <div className="bg-card border rounded-lg p-4">
            <h3 className="font-semibold mb-2">Playback Info</h3>
            <p className="text-sm text-muted-foreground">
              Video should start playing within 3 seconds. If playback fails, check that the RTSP stream is accessible and the backend is running.
            </p>
          </div>
        </div>
      </div>
    </Layout>
  )
}
