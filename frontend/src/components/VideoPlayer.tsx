/**
 * VideoPlayer Component - Display live MJPEG stream
 * 
 * Composes shadcn/ui primitives: AspectRatio, Button, DropdownMenu, DropdownMenuContent, DropdownMenuItem,
 * DropdownMenuTrigger, Alert, AlertDescription, Skeleton
 * 
 * Renders an HTML5 video element with MJPEG stream source.
 * Includes error handling, loading states, and fullscreen controls.
 * Uses shadcn/ui AspectRatio for responsive video container.
 * 
 * Features:
 * - MJPEG stream playback via HTML5 video element
 * - Loading skeleton during stream initialization
 * - Error states: unavailable, unsupported codec, network error
 * - Fullscreen toggle using Fullscreen API
 * - Mute/unmute toggle
 * - Responsive aspect ratio (16:9)
 * - Graceful error recovery with retry capability
 * 
 * @component
 * @param {VideoPlayerProps} props - Component props
 * @param {string} props.streamId - Stream ID for constructing MJPEG URL
 * @param {string} props.rtspUrl - Original RTSP URL (for reference, not used directly)
 * @returns {JSX.Element} Rendered video player
 * 
 * @example
 * <VideoPlayer streamId="stream-123" rtspUrl="rtsp://camera.local/stream" />
 */

import { useEffect, useRef, useState } from 'react'
import { AspectRatio } from '@/components/ui/aspect-ratio'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { AlertCircle, Maximize2, MoreVertical, Volume2, VolumeX } from 'lucide-react'
import { Skeleton } from '@/components/ui/skeleton'

interface VideoPlayerProps {
  streamId: string
  rtspUrl: string
}

type PlayerError = 'unavailable' | 'unsupported' | 'network' | null

export default function VideoPlayer({ streamId, rtspUrl: _rtspUrl }: VideoPlayerProps) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<PlayerError>(null)
  const [isMuted, setIsMuted] = useState(false)
  const [isFullscreen, setIsFullscreen] = useState(false)

  // Construct MJPEG stream URL from RTSP URL
  // Backend serves MJPEG at /api/streams/play/{id}.mjpg
  const mjpegUrl = `/api/streams/play/${streamId}.mjpg`

  useEffect(() => {
    const video = videoRef.current
    if (!video) return

    // Reset state
    setIsLoading(true)
    setError(null)

    // Set video source
    video.src = mjpegUrl

    // Handle video events
    const handleLoadStart = () => {
      setIsLoading(true)
      setError(null)
    }

    const handleCanPlay = () => {
      setIsLoading(false)
      setError(null)
    }

    const handleError = () => {
      setIsLoading(false)
      // Determine error type based on video error code
      if (video.error) {
        switch (video.error.code) {
          case video.error.MEDIA_ERR_ABORTED:
            setError('network')
            break
          case video.error.MEDIA_ERR_NETWORK:
            setError('network')
            break
          case video.error.MEDIA_ERR_DECODE:
            setError('unsupported')
            break
          case video.error.MEDIA_ERR_SRC_NOT_SUPPORTED:
            setError('unsupported')
            break
          default:
            setError('unavailable')
        }
      } else {
        setError('unavailable')
      }
    }

    const handleStalled = () => {
      setError('network')
    }

    const handleSuspend = () => {
      // Stream suspended, likely network issue
      if (isLoading) {
        setError('network')
      }
    }

    // Add event listeners
    video.addEventListener('loadstart', handleLoadStart)
    video.addEventListener('canplay', handleCanPlay)
    video.addEventListener('error', handleError)
    video.addEventListener('stalled', handleStalled)
    video.addEventListener('suspend', handleSuspend)

    // Attempt to load and play
    video.load()
    video.play().catch(() => {
      // Autoplay may be blocked, that's okay
      setIsLoading(false)
    })

    // Cleanup
    return () => {
      video.removeEventListener('loadstart', handleLoadStart)
      video.removeEventListener('canplay', handleCanPlay)
      video.removeEventListener('error', handleError)
      video.removeEventListener('stalled', handleStalled)
      video.removeEventListener('suspend', handleSuspend)
      video.pause()
      video.src = ''
    }
  }, [mjpegUrl, streamId, isLoading])

  const handleFullscreen = async () => {
    if (!containerRef.current) return

    try {
      if (!isFullscreen) {
        if (containerRef.current.requestFullscreen) {
          await containerRef.current.requestFullscreen()
          setIsFullscreen(true)
        }
      } else {
        if (document.fullscreenElement) {
          await document.exitFullscreen()
          setIsFullscreen(false)
        }
      }
    } catch (err) {
      console.error('Fullscreen error:', err)
    }
  }

  const handleToggleMute = () => {
    if (videoRef.current) {
      videoRef.current.muted = !isMuted
      setIsMuted(!isMuted)
    }
  }

  const handleRetry = () => {
    if (videoRef.current) {
      setIsLoading(true)
      setError(null)
      videoRef.current.load()
      videoRef.current.play().catch(() => {
        setIsLoading(false)
      })
    }
  }

  return (
    <div ref={containerRef} className="relative w-full bg-black">
      <AspectRatio ratio={16 / 9} className="bg-black">
        {isLoading && (
          <div className="absolute inset-0 flex items-center justify-center bg-black/80 z-10">
            <div className="text-center">
              <Skeleton className="h-12 w-12 rounded-full mx-auto mb-4 bg-slate-700" />
              <p className="text-white text-sm">Loading stream...</p>
              <p className="text-slate-400 text-xs mt-1">
                Video should start within 3 seconds
              </p>
            </div>
          </div>
        )}

        {error && (
          <div className="absolute inset-0 flex items-center justify-center bg-black/80 z-10">
            <div className="text-center max-w-sm">
              <Alert variant="destructive" className="mb-4">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>
                  {error === 'unavailable' && 'Stream is unavailable. Check if the RTSP source is online.'}
                  {error === 'unsupported' && 'Unsupported video codec. The stream format may not be compatible.'}
                  {error === 'network' && 'Network error. Check your connection and try again.'}
                </AlertDescription>
              </Alert>
              <Button onClick={handleRetry} variant="outline" size="sm">
                Retry
              </Button>
            </div>
          </div>
        )}

        <video
          ref={videoRef}
          className="w-full h-full object-contain"
          controls={false}
          autoPlay
          muted={isMuted}
        />

        {/* Video controls overlay */}
        <div className="absolute bottom-0 left-0 right-0 bg-linear-to-t from-black/80 to-transparent p-4 opacity-0 hover:opacity-100 transition-opacity">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Button
                size="sm"
                variant="ghost"
                onClick={handleToggleMute}
                className="text-white hover:bg-white/20"
                title={isMuted ? 'Unmute' : 'Mute'}
              >
                {isMuted ? (
                  <VolumeX className="h-4 w-4" />
                ) : (
                  <Volume2 className="h-4 w-4" />
                )}
              </Button>
            </div>

            <div className="flex items-center gap-2">
              <Button
                size="sm"
                variant="ghost"
                onClick={handleFullscreen}
                className="text-white hover:bg-white/20"
                title="Fullscreen"
              >
                <Maximize2 className="h-4 w-4" />
              </Button>

              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button
                    size="sm"
                    variant="ghost"
                    className="text-white hover:bg-white/20"
                  >
                    <MoreVertical className="h-4 w-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem onClick={handleRetry}>
                    Reload Stream
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => {
                    const url = `${window.location.origin}${mjpegUrl}`
                    window.open(url, '_blank')
                  }}>
                    Open in New Tab
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </div>
        </div>
      </AspectRatio>
    </div>
  )
}
