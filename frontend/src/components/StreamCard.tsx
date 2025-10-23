/**
 * StreamCard Component - Individual stream card with status indicators
 * 
 * Composes shadcn/ui primitives: Card, CardContent, CardDescription, CardHeader, CardTitle, Badge, Button
 * 
 * Displays stream information with:
 * - Status badge (green/yellow/red) using shadcn/ui Badge with custom styling
 * - Stream name (truncated at 40 chars with tooltip)
 * - Masked RTSP URL (last 20 chars with tooltip)
 * - Action buttons (Edit, Play, Delete) using shadcn/ui Button variants
 * - Created date display
 * 
 * @component
 * @param {StreamCardProps} props - Component props
 * @param {StreamResponse} props.stream - Stream object with id, name, rtsp_url, status, created_at
 * @returns {JSX.Element} Rendered stream card
 * 
 * @example
 * <StreamCard stream={stream} />
 */

import { Link } from 'react-router-dom'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Edit2, Play, Trash2, AlertCircle, CheckCircle2, Clock } from 'lucide-react'
import type { StreamResponse } from '@/lib/types'
import { truncateText, maskRtspUrl } from '@/lib/utils'

interface StreamCardProps {
  stream: StreamResponse
}

export default function StreamCard({ stream }: StreamCardProps) {
  // Determine status color based on stream status
  const getStatusBadge = () => {
    switch (stream.status) {
      case 'Active':
        return (
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">
              <CheckCircle2 className="h-3 w-3 mr-1" />
              Active
            </Badge>
          </div>
        )
      case 'Inactive':
        return (
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="bg-red-50 text-red-700 border-red-200">
              <AlertCircle className="h-3 w-3 mr-1" />
              Inactive
            </Badge>
          </div>
        )
      default:
        return (
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="bg-yellow-50 text-yellow-700 border-yellow-200">
              <Clock className="h-3 w-3 mr-1" />
              Pending
            </Badge>
          </div>
        )
    }
  }

  const truncatedName = truncateText(stream.name, 40)
  const maskedUrl = maskRtspUrl(stream.rtsp_url)
  // Show last 20 chars of masked URL
  const displayUrl =
    maskedUrl.length > 20 ? '...' + maskedUrl.slice(-20) : maskedUrl

  return (
    <Card className="flex flex-col h-full hover:shadow-md transition-shadow">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1 min-w-0">
            <CardTitle className="text-lg truncate" title={stream.name}>
              {truncatedName}
            </CardTitle>
            <CardDescription className="text-xs mt-1 truncate" title={maskedUrl}>
              {displayUrl}
            </CardDescription>
          </div>
          {getStatusBadge()}
        </div>
      </CardHeader>

      <CardContent className="flex-1 space-y-4 pb-4">
        {/* Stream Details */}
        <div className="space-y-2 text-sm">
          <div className="flex justify-between items-center">
            <span className="text-muted-foreground">Status:</span>
            <span className="font-medium">{stream.status}</span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-muted-foreground">Created:</span>
            <span className="font-medium text-xs">
              {new Date(stream.created_at).toLocaleDateString()}
            </span>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-col gap-2 pt-2">
          <div className="flex gap-2">
            <Link to={`/play/${stream.id}`} className="flex-1">
              <Button size="sm" className="w-full" variant="default">
                <Play className="h-4 w-4 mr-1" />
                Play
              </Button>
            </Link>
            <Link to={`/edit/${stream.id}`} className="flex-1">
              <Button size="sm" variant="outline" className="w-full">
                <Edit2 className="h-4 w-4 mr-1" />
                Edit
              </Button>
            </Link>
          </div>
          <Button size="sm" variant="ghost" className="w-full text-destructive hover:text-destructive hover:bg-destructive/10">
            <Trash2 className="h-4 w-4 mr-1" />
            Delete
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
