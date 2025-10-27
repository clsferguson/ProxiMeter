/**
 * StreamCard Component - Stream Thumbnail Display
 * 
 * Displays stream information with a single JPEG snapshot preview.
 * Click "Play" to open full streaming view in new window.
 * 
 * @module components/StreamCard
 */

import { Link } from 'react-router-dom'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Edit2, Play, Trash2, AlertCircle, CheckCircle2, Clock, RefreshCw } from 'lucide-react'
import type { StreamResponse } from '@/lib/types'
import { truncateText, maskRtspUrl } from '@/lib/utils'
import { useState, useEffect } from 'react'
import type { ReactElement } from 'react'

// ============================================================================
// Type Definitions
// ============================================================================

interface ScoreData {
  distance?: number
  coordinates?: { x: number; y: number }
  size?: number
  [key: string]: unknown
}

interface StreamCardProps {
  stream: StreamResponse
  scores?: ScoreData
  onDelete?: (streamId: string) => void
}

// ============================================================================
// Helper Functions
// ============================================================================

function getStatusBadge(status: string): ReactElement {
  const normalizedStatus = status.toLowerCase()

  if (normalizedStatus === 'active' || normalizedStatus === 'running') {
    return (
      <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200 dark:bg-green-950 dark:text-green-400 dark:border-green-800">
        <CheckCircle2 className="h-3 w-3 mr-1" />
        Active
      </Badge>
    )
  }

  if (normalizedStatus === 'inactive' || normalizedStatus === 'stopped') {
    return (
      <Badge variant="outline" className="bg-red-50 text-red-700 border-red-200 dark:bg-red-950 dark:text-red-400 dark:border-red-800">
        <AlertCircle className="h-3 w-3 mr-1" />
        Inactive
      </Badge>
    )
  }

  return (
    <Badge variant="outline" className="bg-yellow-50 text-yellow-700 border-yellow-200 dark:bg-yellow-950 dark:text-yellow-400 dark:border-yellow-800">
      <Clock className="h-3 w-3 mr-1" />
      Pending
    </Badge>
  )
}

function formatScoresText(scores: ScoreData): string {
  const parts: string[] = []

  if (scores.distance !== undefined) {
    parts.push(`Dist: ${scores.distance.toFixed(2)}`)
  }

  if (scores.coordinates) {
    const x = scores.coordinates.x?.toFixed(2) ?? '0.00'
    const y = scores.coordinates.y?.toFixed(2) ?? '0.00'
    parts.push(`Pos: (${x}, ${y})`)
  }

  if (scores.size !== undefined) {
    parts.push(`Size: ${scores.size}`)
  }

  return parts.join(' | ') || 'No data'
}

// ============================================================================
// Main Component
// ============================================================================

/**
 * StreamCard Component - Snapshot Preview Only
 * 
 * Shows a single JPEG snapshot that refreshes periodically.
 * The snapshot endpoint provides the latest frame from the MJPEG stream.
 * 
 * @example
 * ```
 * <StreamCard 
 *   stream={stream} 
 *   scores={scores[stream.id]}
 *   onDelete={handleDelete}
 * />
 * ```
 */
export default function StreamCard({ stream, scores, onDelete }: StreamCardProps) {
  
  // ============================================================================
  // State Management
  // ============================================================================
  
  const [snapshotKey, setSnapshotKey] = useState(0)
  const [imageError, setImageError] = useState(false)

  // Refresh snapshot every 5 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      setSnapshotKey(prev => prev + 1)
      setImageError(false)
    }, 5000)

    return () => clearInterval(interval)
  }, [])

  // ============================================================================
  // Data Preparation
  // ============================================================================

  const truncatedName = truncateText(stream.name, 40)
  const maskedUrl = maskRtspUrl(stream.rtsp_url)
  const displayUrl = maskedUrl.length > 20 ? '...' + maskedUrl.slice(-20) : maskedUrl
  const createdDate = new Date(stream.created_at).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  })

  // Snapshot URL with cache-busting key
  const snapshotUrl = `/api/streams/${stream.id}/snapshot?t=${snapshotKey}`

  // ============================================================================
  // Event Handlers
  // ============================================================================

  const handleDelete = () => {
    if (onDelete) {
      onDelete(stream.id)
    }
  }

  const handleRefreshSnapshot = () => {
    setSnapshotKey(prev => prev + 1)
    setImageError(false)
  }

  const handleImageError = () => {
    setImageError(true)
  }

  // ============================================================================
  // Render
  // ============================================================================

  return (
    <Card className="flex flex-col h-full hover:shadow-lg transition-all duration-200">
      
      {/* Header: Stream name and status */}
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1 min-w-0">
            <CardTitle 
              className="text-lg truncate font-semibold" 
              title={stream.name}
            >
              {truncatedName}
            </CardTitle>
            <CardDescription 
              className="text-xs mt-1 truncate font-mono" 
              title={maskedUrl}
            >
              {displayUrl}
            </CardDescription>
          </div>
          <div className="shrink-0">
            {getStatusBadge(stream.status)}
          </div>
        </div>
      </CardHeader>

      {/* Content: Snapshot and metadata */}
      <CardContent className="flex-1 space-y-4 pb-4">
        
        {/* Stream metadata */}
        <div className="space-y-2 text-sm">
          <div className="flex justify-between items-center">
            <span className="text-muted-foreground">Status:</span>
            <span className="font-medium capitalize">{stream.status}</span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-muted-foreground">Created:</span>
            <span className="font-medium text-xs">{createdDate}</span>
          </div>
        </div>

        {/* Snapshot preview with scores overlay */}
        <div className="relative w-full aspect-video bg-black rounded-md overflow-hidden">
          {!imageError ? (
            <>
              <img
                src={snapshotUrl}
                alt={`${stream.name} snapshot`}
                className="w-full h-full object-contain"
                onError={handleImageError}
              />
              
              {/* Scores overlay */}
              {scores && (
                <div className="absolute top-2 left-2 right-2 pointer-events-none">
                  <div className="bg-black/70 backdrop-blur-sm text-white text-xs px-3 py-1.5 rounded-md border border-white/20 font-mono">
                    {formatScoresText(scores)}
                  </div>
                </div>
              )}

              {/* Refresh indicator */}
              <Button
                size="sm"
                variant="ghost"
                className="absolute bottom-2 right-2 h-8 w-8 p-0 bg-black/50 hover:bg-black/70 text-white"
                onClick={handleRefreshSnapshot}
                title="Refresh snapshot"
              >
                <RefreshCw className="h-4 w-4" />
              </Button>
            </>
          ) : (
            <div className="w-full h-full flex items-center justify-center bg-muted">
              <div className="text-center space-y-2">
                <AlertCircle className="h-8 w-8 mx-auto text-muted-foreground" />
                <p className="text-sm text-muted-foreground">Snapshot unavailable</p>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={handleRefreshSnapshot}
                >
                  <RefreshCw className="h-4 w-4 mr-2" />
                  Retry
                </Button>
              </div>
            </div>
          )}
        </div>

        {/* Action buttons */}
        <div className="flex flex-col gap-2 pt-2">
          <div className="flex gap-2">
            {/* Play button - navigates to full screen view */}
            <Link to={`/play/${stream.id}`} className="flex-1">
              <Button 
                size="sm" 
                className="w-full" 
                variant="default"
                title="View stream in full screen"
              >
                <Play className="h-4 w-4 mr-1" />
                Play
              </Button>
            </Link>

            {/* Edit button */}
            <Link to={`/edit/${stream.id}`} className="flex-1">
              <Button 
                size="sm" 
                variant="outline" 
                className="w-full"
                title="Edit stream settings"
              >
                <Edit2 className="h-4 w-4 mr-1" />
                Edit
              </Button>
            </Link>
          </div>

          {/* Delete button */}
          <Button 
            size="sm" 
            variant="ghost" 
            className="w-full text-destructive hover:text-destructive hover:bg-destructive/10"
            onClick={handleDelete}
            title="Delete this stream"
          >
            <Trash2 className="h-4 w-4 mr-1" />
            Delete
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
