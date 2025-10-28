/**
 * VideoPlayer Component - Canvas-based MJPEG Stream Player
 * 
 * Displays full-resolution MJPEG streams using HTML5 Canvas for memory-safe rendering.
 * Manually parses multipart MJPEG boundaries to avoid browser memory leaks and crashes.
 * 
 * Features:
 * - Full resolution streaming (no forced resize)
 * - Proper JPEG boundary detection (0xFFD8 start, 0xFFD9 end markers)
 * - Memory-safe rendering with blob URL cleanup
 * - Fullscreen support via Fullscreen API
 * - Error handling and retry capability
 * - Loading states with skeleton UI
 * 
 * Technical Implementation:
 * - Uses Fetch API to stream raw MJPEG bytes
 * - Manually parses JPEG frame boundaries from byte stream
 * - Renders each frame to canvas at original resolution
 * - Properly cleans up resources with AbortController
 * - Prevents memory leaks by revoking blob URLs immediately
 * 
 * This approach is similar to how Frigate NVR handles MJPEG streams,
 * avoiding the browser's poor support for multipart/x-mixed-replace.
 * 
 * @component
 * @param {VideoPlayerProps} props - Component props
 * @param {string} props.streamId - Stream ID for constructing MJPEG URL
 * @param {string} props.rtspUrl - Original RTSP URL (for reference)
 * @returns {JSX.Element} Rendered video player with canvas
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
import { AlertCircle, Maximize2, MoreVertical } from 'lucide-react'
import { Skeleton } from '@/components/ui/skeleton'

interface VideoPlayerProps {
  streamId: string
  rtspUrl: string
}

type PlayerError = 'unavailable' | 'unsupported' | 'network' | null

export default function VideoPlayer({ streamId }: VideoPlayerProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<PlayerError>(null)
  const [isFullscreen, setIsFullscreen] = useState(false)
  const abortControllerRef = useRef<AbortController | null>(null)

  const mjpegUrl = `/api/streams/${streamId}/mjpeg`

  useEffect(() => {
    let active = true
    abortControllerRef.current = new AbortController()

    /**
     * Find JPEG start marker (0xFFD8) in byte buffer.
     * 
     * @param buffer - Uint8Array containing MJPEG stream bytes
     * @returns Index of start marker, or -1 if not found
     */
    const findJPEGStart = (buffer: Uint8Array): number => {
      for (let i = 0; i < buffer.length - 1; i++) {
        if (buffer[i] === 0xFF && buffer[i + 1] === 0xD8) {
          return i
        }
      }
      return -1
    }

    /**
     * Find JPEG end marker (0xFFD9) in byte buffer.
     * 
     * @param buffer - Uint8Array containing MJPEG stream bytes
     * @returns Index of end marker, or -1 if not found
     */
    const findJPEGEnd = (buffer: Uint8Array): number => {
      for (let i = 0; i < buffer.length - 1; i++) {
        if (buffer[i] === 0xFF && buffer[i + 1] === 0xD9) {
          return i
        }
      }
      return -1
    }

    /**
     * Start MJPEG stream consumption and rendering.
     * 
     * Fetches the MJPEG stream, parses frame boundaries, and renders
     * each complete JPEG frame to the canvas at full resolution.
     */
    const startStream = async () => {
      try {
        setIsLoading(true)
        setError(null)

        // Fetch MJPEG stream with abort signal
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

        // Process stream bytes continuously
        while (active) {
          const { done, value } = await reader.read()
          
          if (done) {
            console.log('MJPEG stream ended')
            break
          }

          // Append new data to buffer
          const newBuffer = new Uint8Array(buffer.length + value.length)
          newBuffer.set(buffer)
          newBuffer.set(value, buffer.length)
          buffer = newBuffer

          // Look for complete JPEG frame (start marker to end marker)
          const startIdx = findJPEGStart(buffer)
          const endIdx = findJPEGEnd(buffer)

          if (startIdx !== -1 && endIdx !== -1 && endIdx > startIdx) {
            // Extract one complete JPEG frame
            const jpegData = buffer.slice(startIdx, endIdx + 2)
            buffer = buffer.slice(endIdx + 2)

            // Render frame to canvas at full resolution
            const blob = new Blob([jpegData], { type: 'image/jpeg' })
            const imgUrl = URL.createObjectURL(blob)
            
            const img = new Image()
            img.onload = () => {
              // Set canvas dimensions to match image (full resolution)
              canvas.width = img.width
              canvas.height = img.height
              ctx.drawImage(img, 0, 0)
              
              // Clean up blob URL to prevent memory leaks
              URL.revokeObjectURL(imgUrl)
            }
            img.onerror = () => {
              // Clean up even on error
              URL.revokeObjectURL(imgUrl)
              console.error('Failed to decode JPEG frame')
            }
            img.src = imgUrl
          }

          // Prevent buffer from growing indefinitely (5MB limit)
          if (buffer.length > 5 * 1024 * 1024) {
            console.warn('Buffer overflow, resetting')
            buffer = new Uint8Array(0)
          }
        }
      } catch (err: unknown) {
        // Handle AbortError (user cancelled) vs actual errors
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

    // Cleanup function
    return () => {
      active = false
      abortControllerRef.current?.abort()
    }
  }, [mjpegUrl, streamId])

  /**
   * Toggle fullscreen mode for the video container.
   * Uses Fullscreen API with proper state tracking.
   */
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

  /**
   * Retry stream connection by reloading the page.
   * This ensures a clean state for reconnection.
   */
  const handleRetry = () => {
    window.location.reload()
  }

  return (
    <div ref={containerRef} className="relative w-full bg-black">
      <AspectRatio ratio={16 / 9} className="bg-black">
        {/* Loading State */}
        {isLoading && (
          <div className="absolute inset-0 flex items-center justify-center bg-black/80 z-10">
            <div className="text-center">
              <Skeleton className="h-12 w-12 rounded-full mx-auto mb-4 bg-slate-700" />
              <p className="text-white text-sm">Loading stream...</p>
              <p className="text-slate-400 text-xs mt-1">
                Connecting to MJPEG stream...
              </p>
            </div>
          </div>
        )}

        {/* Error State */}
        {error && (
          <div className="absolute inset-0 flex items-center justify-center bg-black/80 z-10">
            <div className="text-center max-w-sm">
              <Alert variant="destructive" className="mb-4">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>
                  {error === 'network' && 'Network error. Check if stream is running.'}
                  {error === 'unavailable' && 'Stream unavailable. Start the stream first.'}
                  {error === 'unsupported' && 'Unsupported format. Check stream configuration.'}
                </AlertDescription>
              </Alert>
              <Button onClick={handleRetry} variant="outline" size="sm">
                Retry
              </Button>
            </div>
          </div>
        )}

        {/* Canvas for rendering full-resolution MJPEG frames */}
        <canvas
          ref={canvasRef}
          className="w-full h-full object-contain"
        />

        {/* Video Controls Overlay */}
        <div className="absolute bottom-0 left-0 right-0 bg-linear-to-t from-black/80 to-transparent p-4 opacity-0 hover:opacity-100 transition-opacity">
          <div className="flex items-center justify-between">
            <span className="text-white text-sm">Full Resolution MJPEG</span>

            <div className="flex items-center gap-2">
              {/* Fullscreen Button */}
              <Button
                size="sm"
                variant="ghost"
                onClick={handleFullscreen}
                className="text-white hover:bg-white/20"
                title="Fullscreen"
              >
                <Maximize2 className="h-4 w-4" />
              </Button>

              {/* More Options Menu */}
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
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </div>
        </div>
      </AspectRatio>
    </div>
  )
}