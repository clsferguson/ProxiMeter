/**
 * StreamCard Component - Manual Refresh Only
 * 
 * NO automatic snapshot fetching. User must click refresh button.
 */

import { Link } from 'react-router-dom'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Edit2, Play, Trash2, AlertCircle, CheckCircle2, Clock, RefreshCw, Camera } from 'lucide-react'
import type { StreamResponse } from '@/lib/types'
import { truncateText, maskRtspUrl } from '@/lib/utils'
import { API_BASE_URL } from '@/lib/constants'
import { useState } from 'react'
import type { ReactElement } from 'react'

interface StreamCardProps {
  stream: StreamResponse
  onDelete?: (streamId: string) => void
}

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

export default function StreamCard({ stream, onDelete }: StreamCardProps) {
  
  const [snapshotKey, setSnapshotKey] = useState(0)
  const [imageError, setImageError] = useState(false)
  const [isRefreshing, setIsRefreshing] = useState(false)

  const truncatedName = truncateText(stream.name, 40)
  const maskedUrl = maskRtspUrl(stream.rtsp_url)
  const displayUrl = maskedUrl.length > 20 ? '...' + maskedUrl.slice(-20) : maskedUrl
  const createdDate = new Date(stream.created_at).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  })

  const snapshotUrl = stream.status === 'running' && snapshotKey > 0
    ? `${API_BASE_URL}/streams/${stream.id}/snapshot?t=${snapshotKey}`
    : null

  const handleDelete = () => {
    if (onDelete) {
      onDelete(stream.id)
    }
  }

  const handleRefreshSnapshot = async () => {
    setIsRefreshing(true)
    setImageError(false)
    setSnapshotKey(prev => prev + 1)
    
    setTimeout(() => {
      setIsRefreshing(false)
    }, 500)
  }

  const handleImageError = () => {
    setImageError(true)
    setIsRefreshing(false)
  }

  const handleImageLoad = () => {
    setIsRefreshing(false)
  }

  return (
    <Card className="flex flex-col h-full hover:shadow-lg transition-all duration-200">
      
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1 min-w-0">
            <CardTitle className="text-lg truncate font-semibold" title={stream.name}>
              {truncatedName}
            </CardTitle>
            <CardDescription className="text-xs mt-1 truncate font-mono" title={maskedUrl}>
              {displayUrl}
            </CardDescription>
          </div>
          <div className="shrink-0">
            {getStatusBadge(stream.status)}
          </div>
        </div>
      </CardHeader>

      <CardContent className="flex-1 space-y-4 pb-4">
        
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

        {/* Snapshot preview */}
        <div className="relative w-full aspect-video bg-black rounded-md overflow-hidden">
          {stream.status === 'running' && snapshotUrl && !imageError ? (
            <>
              <img
                src={snapshotUrl}
                alt={`${stream.name} snapshot`}
                className="w-full h-full object-contain"
                onError={handleImageError}
                onLoad={handleImageLoad}
              />
              
              <Button
                size="sm"
                variant="ghost"
                className="absolute bottom-2 right-2 h-8 w-8 p-0 bg-black/50 hover:bg-black/70 text-white"
                onClick={handleRefreshSnapshot}
                disabled={isRefreshing}
                title="Refresh snapshot"
              >
                <RefreshCw className={`h-4 w-4 ${isRefreshing ? 'animate-spin' : ''}`} />
              </Button>

              {isRefreshing && (
                <div className="absolute inset-0 flex items-center justify-center bg-black/20">
                  <RefreshCw className="h-8 w-8 text-white animate-spin" />
                </div>
              )}
            </>
          ) : (
            <div className="w-full h-full flex items-center justify-center bg-muted">
              <div className="text-center space-y-3">
                {stream.status === 'running' && snapshotKey === 0 ? (
                  // Stream running but user hasn't clicked refresh yet
                  <>
                    <Camera className="h-8 w-8 mx-auto text-muted-foreground" />
                    <p className="text-sm text-muted-foreground">Click refresh to capture snapshot</p>
                    <Button size="sm" variant="outline" onClick={handleRefreshSnapshot} disabled={isRefreshing}>
                      <RefreshCw className={`h-4 w-4 mr-2 ${isRefreshing ? 'animate-spin' : ''}`} />
                      Capture Snapshot
                    </Button>
                  </>
                ) : stream.status === 'running' && imageError ? (
                  // Stream running but snapshot failed
                  <>
                    <AlertCircle className="h-8 w-8 mx-auto text-muted-foreground" />
                    <p className="text-sm text-muted-foreground">Failed to load</p>
                    <Button size="sm" variant="outline" onClick={handleRefreshSnapshot} disabled={isRefreshing}>
                      <RefreshCw className={`h-4 w-4 mr-2 ${isRefreshing ? 'animate-spin' : ''}`} />
                      Retry
                    </Button>
                  </>
                ) : (
                  // Stream not running
                  <>
                    <Camera className="h-8 w-8 mx-auto text-muted-foreground" />
                    <p className="text-sm text-muted-foreground">No preview available</p>
                    <p className="text-xs text-muted-foreground px-4">
                      Start the stream to capture snapshots
                    </p>
                  </>
                )}
              </div>
            </div>
          )}
        </div>

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
          <Button 
            size="sm" 
            variant="ghost" 
            className="w-full text-destructive hover:text-destructive hover:bg-destructive/10"
            onClick={handleDelete}
          >
            <Trash2 className="h-4 w-4 mr-1" />
            Delete
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
