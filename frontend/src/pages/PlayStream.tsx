/**
 * PlayStream Page - Full Screen Stream Viewer
 * 
 * Displays a live MJPEG stream at 5fps in a dedicated window.
 * Streams are always full resolution, fit to window size.
 * No audio, optimized for low bandwidth monitoring.
 * 
 * @module pages/PlayStream
 */

import { useParams } from 'react-router-dom'
import { useEffect, useRef, useState } from 'react'
import { Button } from '@/components/ui/button'
import { AlertCircle, Maximize2, Minimize2, X } from 'lucide-react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Skeleton } from '@/components/ui/skeleton'

type PlayerError = 'unavailable' | 'network' | null

/**
 * PlayStream Component
 * 
 * Renders a full-window MJPEG stream viewer with manual frame parsing.
 * The stream is always 5fps, full resolution, no audio.
 * FFmpeg transcoding happens automatically on the backend.
 */
export default function PlayStream() {
  const { streamId } = useParams<{ streamId: string }>()
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<PlayerError>(null)
  const [isFullscreen, setIsFullscreen] = useState(false)
  const abortControllerRef = useRef<AbortController | null>(null)

  const mjpegUrl = `/api/streams/${streamId}/mjpeg`

  // ============================================================================
  // MJPEG Stream Processing
  // ============================================================================

  useEffect(() => {
    let active = true
    abortControllerRef.current = new AbortController()

    const findJPEGStart = (buffer: Uint8Array): number => {
      for (let i = 0; i < buffer.length - 1; i++) {
        if (buffer[i] === 0xFF && buffer[i + 1] === 0xD8) {
          return i
        }
      }
      return -1
    }

    const findJPEGEnd = (buffer: Uint8Array): number => {
      for (let i = 0; i < buffer.length - 1; i++) {
        if (buffer[i] === 0xFF && buffer[i + 1] === 0xD9) {
          return i
        }
      }
      return -1
    }

    const startStream = async () => {
      try {
        setIsLoading(true)
        setError(null)

        const response = await fetch(mjpegUrl, {
          signal: abortControllerRef.current?.signal
        })
        
        if (!response.ok) {
          throw new Error('Stream unavailable')
        }
        
        if (!response.body) {
          throw new Error('No response body')
        }

        setIsLoading(false)

        const reader = response.body.getReader()
        let buffer = new Uint8Array(0)

        const canvas = canvasRef.current
        if (!canvas) return

        const ctx = canvas.getContext('2d')
        if (!ctx) return

        while (active) {
          const { done, value } = await reader.read()
          
          if (done) {
            console.log('MJPEG stream ended')
            break
          }

          const newBuffer = new Uint8Array(buffer.length + value.length)
          newBuffer.set(buffer)
          newBuffer.set(value, buffer.length)
          buffer = newBuffer

          const startIdx = findJPEGStart(buffer)
          const endIdx = findJPEGEnd(buffer)

          if (startIdx !== -1 && endIdx !== -1 && endIdx > startIdx) {
            const jpegData = buffer.slice(startIdx, endIdx + 2)
            buffer = buffer.slice(endIdx + 2)

            const blob = new Blob([jpegData], { type: 'image/jpeg' })
            const imgUrl = URL.createObjectURL(blob)
            
            const img = new Image()
            img.onload = () => {
              // Set canvas to full resolution, CSS will handle fit-to-window
              canvas.width = img.width
              canvas.height = img.height
              ctx.drawImage(img, 0, 0)
              URL.revokeObjectURL(imgUrl)
            }
            img.onerror = () => {
              URL.revokeObjectURL(imgUrl)
              console.error('Failed to decode JPEG frame')
            }
            img.src = imgUrl
          }

          if (buffer.length > 5 * 1024 * 1024) {
            console.warn('Buffer overflow, resetting')
            buffer = new Uint8Array(0)
          }
        }
      } catch (err: unknown) {
        if (err instanceof Error && err.name === 'AbortError') {
          console.log('Stream fetch aborted')
          return
        }
        
        console.error('Stream error:', err)
        if (active) {
          setError('network')
          setIsLoading(false)
        }
      }
    }

    startStream()

    return () => {
      active = false
      abortControllerRef.current?.abort()
    }
  }, [mjpegUrl, streamId])

  // ============================================================================
  // Event Handlers
  // ============================================================================

  const handleFullscreen = async () => {
    if (!containerRef.current) return

    try {
      if (!isFullscreen) {
        await containerRef.current.requestFullscreen()
        setIsFullscreen(true)
      } else {
        await document.exitFullscreen()
        setIsFullscreen(false)
      }
    } catch (err) {
      console.error('Fullscreen error:', err)
    }
  }

  const handleClose = () => {
    window.close()
  }

  const handleRetry = () => {
    window.location.reload()
  }

  // ============================================================================
  // Render
  // ============================================================================

  return (
    <div 
      ref={containerRef} 
      className="relative w-screen h-screen bg-black flex flex-col"
    >
      {/* Control bar */}
      <div className="absolute top-0 left-0 right-0 bg-black/80 backdrop-blur-sm p-2 flex items-center justify-between z-10 opacity-0 hover:opacity-100 transition-opacity">
        <div className="text-white text-sm font-mono">
          Stream: {streamId} | 5fps Full Resolution
        </div>
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant="ghost"
            onClick={handleFullscreen}
            className="text-white hover:bg-white/20"
            title={isFullscreen ? 'Exit fullscreen' : 'Fullscreen'}
          >
            {isFullscreen ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={handleClose}
            className="text-white hover:bg-white/20"
            title="Close window"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Main content area */}
      <div className="flex-1 flex items-center justify-center">
        {/* Loading state */}
        {isLoading && (
          <div className="absolute inset-0 flex items-center justify-center bg-black/80 z-10">
            <div className="text-center">
              <Skeleton className="h-12 w-12 rounded-full mx-auto mb-4 bg-slate-700" />
              <p className="text-white text-sm">Loading stream...</p>
              <p className="text-slate-400 text-xs mt-1">
                Connecting to 5fps MJPEG stream...
              </p>
            </div>
          </div>
        )}

        {/* Error state */}
        {error && (
          <div className="absolute inset-0 flex items-center justify-center bg-black/80 z-10">
            <div className="text-center max-w-sm">
              <Alert variant="destructive" className="mb-4">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>
                  {error === 'network' && 'Network error. Stream may not be running.'}
                  {error === 'unavailable' && 'Stream unavailable. Check configuration.'}
                </AlertDescription>
              </Alert>
              <Button onClick={handleRetry} variant="outline" size="sm">
                Retry
              </Button>
            </div>
          </div>
        )}

        {/* Canvas for full resolution MJPEG at 5fps */}
        <canvas
          ref={canvasRef}
          className="max-w-full max-h-full object-contain"
          style={{ width: '100%', height: '100%' }}
        />
      </div>
    </div>
  )
}
