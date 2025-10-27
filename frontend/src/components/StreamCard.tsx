/**
 * StreamCard Component - Individual Stream Display with Real-time Updates
 * 
 * Displays a single RTSP stream with:
 * - Live video preview via VideoPlayer
 * - Real-time detection scores overlay (distance, coordinates, size)
 * - Status badge with visual indicators (Active/Inactive/Pending)
 * - Stream metadata (name, RTSP URL, created date)
 * - Action buttons (Play, Edit, Delete)
 * 
 * Scores are now obtained from the parent useStreams hook to avoid
 * duplicate SSE connections and infinite loops.
 * 
 * @module components/StreamCard
 */

import { Link } from 'react-router-dom'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Edit2, Play, Trash2, AlertCircle, CheckCircle2, Clock } from 'lucide-react'
import type { StreamResponse } from '@/lib/types'
import { truncateText, maskRtspUrl } from '@/lib/utils'
import VideoPlayer from './VideoPlayer'
import type { ReactElement } from 'react'

// ============================================================================
// Type Definitions
// ============================================================================

/**
 * Score data structure for real-time person detection metrics
 */
interface ScoreData {
  distance?: number
  coordinates?: { x: number; y: number }
  size?: number
  [key: string]: unknown
}

/**
 * Props for StreamCard component
 */
interface StreamCardProps {
  /** Stream object containing all stream data */
  stream: StreamResponse
  /** Real-time scores from SSE (provided by parent useStreams hook) */
  scores?: ScoreData
  /** Callback when delete button is clicked */
  onDelete?: (streamId: string) => void
}

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Determines the appropriate status badge based on stream status
 * 
 * Status mapping:
 * - 'running' / 'Active' → Green badge with checkmark
 * - 'stopped' / 'Inactive' → Red badge with alert icon
 * - Other → Yellow badge with clock icon (Pending/Unknown)
 * 
 * @param status - Current stream status
 * @returns React element with styled badge
 */
function getStatusBadge(status: string): ReactElement {
  // Normalize status (handle both 'running'/'stopped' and 'Active'/'Inactive')
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

  // Default: pending or unknown status
  return (
    <Badge variant="outline" className="bg-yellow-50 text-yellow-700 border-yellow-200 dark:bg-yellow-950 dark:text-yellow-400 dark:border-yellow-800">
      <Clock className="h-3 w-3 mr-1" />
      Pending
    </Badge>
  )
}

/**
 * Formats score data into a readable string for overlay display
 * 
 * @param scores - Score data object
 * @returns Formatted string with distance, position, and size
 */
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
 * StreamCard Component
 * 
 * CRITICAL FIX: Removed internal SSE connection to prevent infinite loop.
 * Scores are now passed as props from parent useStreams hook, which manages
 * all SSE connections centrally.
 * 
 * @example
 * ```
 * const { streams, scores } = useStreams()
 * 
 * {streams.map(stream => (
 *   <StreamCard 
 *     key={stream.id} 
 *     stream={stream} 
 *     scores={scores[stream.id]}
 *     onDelete={handleDelete}
 *   />
 * ))}
 * ```
 */
export default function StreamCard({ stream, scores, onDelete }: StreamCardProps) {
  
  // ============================================================================
  // Data Preparation
  // ============================================================================

  // Truncate long stream names for display (full name shown in tooltip)
  const truncatedName = truncateText(stream.name, 40)
  
  // Mask sensitive RTSP URL (hide username/password)
  const maskedUrl = maskRtspUrl(stream.rtsp_url)
  
  // Show last 20 characters of masked URL for quick reference
  const displayUrl = maskedUrl.length > 20 
    ? '...' + maskedUrl.slice(-20) 
    : maskedUrl

  // Format created date for display
  const createdDate = new Date(stream.created_at).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  })

  // ============================================================================
  // Event Handlers
  // ============================================================================

  /**
   * Handles delete button click
   * Calls parent callback if provided
   */
  const handleDelete = () => {
    if (onDelete) {
      onDelete(stream.id)
    }
  }

  // ============================================================================
  // Render
  // ============================================================================

  return (
    <Card className="flex flex-col h-full hover:shadow-lg transition-all duration-200 hover:scale-[1.02]">
      
      {/* Header: Stream name, URL, and status badge */}
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-2">
          
          {/* Stream name and URL */}
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

          {/* Status badge */}
          <div className="shrink-0">
            {getStatusBadge(stream.status)}
          </div>
        </div>
      </CardHeader>

      {/* Content: Video preview, scores, and metadata */}
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

        {/* Video player with optional scores overlay */}
        <div className="relative w-full">
          <VideoPlayer streamId={stream.id} rtspUrl={stream.rtsp_url} />
          
          {/* Scores overlay - only shown when scores are available */}
          {scores && (
            <div className="absolute top-2 left-2 right-2 pointer-events-none">
              <div className="bg-black/70 backdrop-blur-sm text-white text-xs px-3 py-1.5 rounded-md border border-white/20 font-mono">
                {formatScoresText(scores)}
              </div>
            </div>
          )}
        </div>

        {/* Action buttons */}
        <div className="flex flex-col gap-2 pt-2">
          
          {/* Primary actions: Play and Edit */}
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

            {/* Edit button - navigates to edit form */}
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

          {/* Destructive action: Delete */}
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
