/**
 * MotionMetrics Component - Real-time Motion Detection Metrics Display
 *
 * Displays live metrics for motion-based detection including:
 * - Tracked object counts by state (active, stationary)
 * - GPU utilization percentage
 * - Frame processing time breakdown
 *
 * Uses Server-Sent Events via useStreamMetrics hook for real-time updates.
 *
 * Feature: 006-motion-tracking
 */

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { useStreamMetrics } from '@/hooks'
import { AlertCircle, Activity, RefreshCw } from 'lucide-react'

// ============================================================================
// Type Definitions
// ============================================================================

interface MotionMetricsProps {
  /** Stream ID to monitor */
  streamId: string
  /** Optional className for styling */
  className?: string
}

// ============================================================================
// Main Component
// ============================================================================

/**
 * Displays real-time motion detection metrics for a stream
 *
 * Shows loading state, error handling with retry, and live metric updates.
 * Metrics update at 5 FPS via SSE connection.
 *
 * @example
 * ```tsx
 * <MotionMetrics streamId="abc-123" />
 * ```
 */
export function MotionMetrics({ streamId, className }: MotionMetricsProps) {
  const { metrics, isLoading, error, isConnected, reconnect } = useStreamMetrics({
    streamId,
    autoConnect: true,
    autoReconnect: true
  })

  // ============================================================================
  // Loading State
  // ============================================================================

  if (isLoading && !metrics) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity className="h-5 w-5" />
            Motion Detection Metrics
          </CardTitle>
          <CardDescription>Real-time tracking statistics</CardDescription>
        </CardHeader>
        <CardContent className="space-y-2">
          <div className="flex items-center gap-2">
            <RefreshCw className="h-4 w-4 animate-spin text-muted-foreground" />
            <span className="text-sm text-muted-foreground">Motion detection initializing...</span>
          </div>
          <div className="space-y-2">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-3/4" />
          </div>
        </CardContent>
      </Card>
    )
  }

  // ============================================================================
  // Error State
  // ============================================================================

  if (error) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity className="h-5 w-5" />
            Motion Detection Metrics
          </CardTitle>
          <CardDescription>Real-time tracking statistics</CardDescription>
        </CardHeader>
        <CardContent>
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription className="flex items-center justify-between">
              <span>{error}</span>
              <Button
                variant="outline"
                size="sm"
                onClick={reconnect}
                className="ml-2"
              >
                <RefreshCw className="mr-2 h-4 w-4" />
                Retry
              </Button>
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>
    )
  }

  // ============================================================================
  // No Metrics Yet State
  // ============================================================================

  if (!metrics) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity className="h-5 w-5" />
            Motion Detection Metrics
          </CardTitle>
          <CardDescription>Real-time tracking statistics</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Waiting for metrics data...
          </p>
        </CardContent>
      </Card>
    )
  }

  // ============================================================================
  // Metric Display Helpers
  // ============================================================================

  const hasObjects = metrics.tracked_objects_count > 0 || metrics.stationary_objects_count > 0
  const gpuUtilization = metrics.gpu_utilization_percent !== null
    ? `${metrics.gpu_utilization_percent.toFixed(1)}%`
    : 'N/A'

  // ============================================================================
  // Main Metrics Display
  // ============================================================================

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Activity className="h-5 w-5" />
          Motion Detection Metrics
          {isConnected && (
            <span className="ml-auto inline-flex h-2 w-2 rounded-full bg-green-500" title="Live" />
          )}
        </CardTitle>
        <CardDescription>Real-time tracking statistics</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Object Counts Section */}
        <div className="space-y-2">
          <h4 className="text-sm font-semibold">Tracked Objects</h4>
          {hasObjects ? (
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <span className="text-muted-foreground">Active:</span>
                <span className="ml-2 font-medium text-green-600 dark:text-green-400">
                  {metrics.tracked_objects_count}
                </span>
              </div>
              <div>
                <span className="text-muted-foreground">Stationary:</span>
                <span className="ml-2 font-medium text-yellow-600 dark:text-yellow-400">
                  {metrics.stationary_objects_count}
                </span>
              </div>
              <div>
                <span className="text-muted-foreground">Lost:</span>
                <span className="ml-2 font-medium text-gray-600 dark:text-gray-400">
                  {metrics.lost_objects_count}
                </span>
              </div>
              <div>
                <span className="text-muted-foreground">Motion Regions:</span>
                <span className="ml-2 font-medium">
                  {metrics.motion_regions_count}
                </span>
              </div>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground italic">
              No objects detected
            </p>
          )}
        </div>

        {/* Performance Metrics Section */}
        <div className="space-y-2">
          <h4 className="text-sm font-semibold">Performance</h4>
          <div className="grid grid-cols-1 gap-2 text-sm">
            <div className="flex justify-between">
              <span className="text-muted-foreground">GPU Utilization:</span>
              <span className="font-medium">{gpuUtilization}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Total Frame Time:</span>
              <span className="font-medium">{metrics.total_frame_time_ms.toFixed(1)} ms</span>
            </div>
          </div>
        </div>

        {/* Timing Breakdown Section */}
        <div className="space-y-2">
          <h4 className="text-sm font-semibold">Processing Time Breakdown</h4>
          <div className="grid grid-cols-1 gap-2 text-xs">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Motion Detection:</span>
              <span className="font-mono">{metrics.motion_detection_ms.toFixed(1)} ms</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">YOLO Inference:</span>
              <span className="font-mono">{metrics.yolo_inference_ms.toFixed(1)} ms</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Object Tracking:</span>
              <span className="font-mono">{metrics.tracking_ms.toFixed(1)} ms</span>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
