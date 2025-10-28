/**
 * Dashboard Page - Stream Overview and Management
 * 
 * Primary landing page that displays all configured RTSP streams in a grid layout.
 * 
 * Features:
 * - Real-time stream status monitoring with 2-second polling
 * - Live video previews for all streams
 * - Real-time detection scores overlay (distance, position, size)
 * - Responsive grid layout (1 col mobile, 2 col tablet, 3 col desktop)
 * - Error handling with retry capability
 * - Empty state for first-time users
 * - Loading states with proper UX
 * 
 * User Story: View Stream Dashboard
 * As a user, I want to see all my configured streams with their current status
 * so that I can quickly monitor my camera feeds and detection metrics.
 * 
 * @module pages/Dashboard
 */

import { useState } from 'react'
import Layout from '@/components/Layout'
import StreamCard from '@/components/StreamCard'
import EmptyState from '@/components/EmptyState'
import { useStreams } from '@/hooks/useStreams'
import { Alert, AlertDescription } from '@/components/ui/alert'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { AlertCircle, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'

// ============================================================================
// Main Component
// ============================================================================

/**
 * Dashboard Component
 * 
 * CRITICAL FIXES:
 * 1. Removed duplicate polling useEffect (was causing double requests)
 * 2. Now uses scores from useStreams hook (prevents SSE connection issues)
 * 3. Added proper delete confirmation dialog
 * 4. Improved error handling and loading states
 * 
 * The useStreams hook handles ALL polling and SSE connections centrally,
 * preventing infinite loops and duplicate network requests.
 */
export default function Dashboard() {
  
  // ============================================================================
  // State Management
  // ============================================================================

  // Get streams data from centralized hook with 2-second polling
  const { 
    streams, 
    isLoading, 
    error, 
    refetch, 
    deleteStream 
  } = useStreams({ 
    autoFetch: true, 
    pollInterval: 2000 
  })

  // Delete confirmation dialog state
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [streamToDelete, setStreamToDelete] = useState<string | null>(null)
  const [isDeleting, setIsDeleting] = useState(false)

  // ============================================================================
  // Event Handlers
  // ============================================================================

  /**
   * Opens delete confirmation dialog for a specific stream
   * 
   * @param streamId - ID of the stream to delete
   */
  const handleDeleteClick = (streamId: string) => {
    setStreamToDelete(streamId)
    setDeleteDialogOpen(true)
  }

  /**
   * Confirms and executes stream deletion
   * Shows loading state and handles errors gracefully
   */
  const handleConfirmDelete = async () => {
    if (!streamToDelete) return

    try {
      setIsDeleting(true)
      await deleteStream(streamToDelete)
      setDeleteDialogOpen(false)
      setStreamToDelete(null)
    } catch (err) {
      console.error('Failed to delete stream:', err)
      // Error is already set in the hook, will display in UI
    } finally {
      setIsDeleting(false)
    }
  }

  /**
   * Cancels delete operation and closes dialog
   */
  const handleCancelDelete = () => {
    setDeleteDialogOpen(false)
    setStreamToDelete(null)
  }

  /**
   * Retries fetching streams after an error
   */
  const handleRetry = () => {
    refetch()
  }

  // ============================================================================
  // Helper Functions
  // ============================================================================

  /**
   * Gets the display name of the stream being deleted
   * Used in confirmation dialog
   */
  const getStreamName = (): string => {
    if (!streamToDelete) return ''
    const stream = streams.find(s => s.id === streamToDelete)
    return stream?.name || 'this stream'
  }

  // ============================================================================
  // Render
  // ============================================================================

  return (
    <Layout>
      {/* Page Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">Stream Dashboard</h1>
        <p className="text-muted-foreground">
          Monitor your RTSP streams in real-time with person detection metrics
        </p>
      </div>

      {/* Main Content Area */}
      <div className="space-y-6">
        
        {/* Loading State - Only shown on initial load */}
        {isLoading && streams.length === 0 && (
          <div className="flex flex-col items-center justify-center py-12 space-y-4">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
            <p className="text-muted-foreground">Loading streams...</p>
          </div>
        )}

        {/* Error State - Only shown if no streams loaded */}
        {error && streams.length === 0 && (
          <Alert variant="destructive" className="max-w-2xl mx-auto">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription className="flex items-center justify-between">
              <span>{error}</span>
              <Button 
                onClick={handleRetry} 
                variant="outline" 
                size="sm"
                className="ml-4"
              >
                Retry
              </Button>
            </AlertDescription>
          </Alert>
        )}

        {/* Empty State - No streams configured */}
        {!isLoading && !error && streams.length === 0 && (
          <EmptyState />
        )}

        {/* Streams Grid - Responsive layout */}
        {streams.length > 0 && (
          <div className="grid gap-6 sm:grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
            {streams.map(stream => (
              <StreamCard 
                key={stream.id} 
                stream={stream}
                onDelete={handleDeleteClick}
              />
            ))}
          </div>
        )}

        {/* Background polling indicator - shown when refreshing with existing data */}
        {isLoading && streams.length > 0 && (
          <div className="fixed bottom-4 right-4 bg-card border border-border rounded-lg px-4 py-2 shadow-lg flex items-center gap-2">
            <Loader2 className="h-4 w-4 animate-spin text-primary" />
            <span className="text-sm text-muted-foreground">Updating...</span>
          </div>
        )}
      </div>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Stream</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete <strong>{getStreamName()}</strong>? 
              This action cannot be undone and will stop all detection on this stream.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel 
              onClick={handleCancelDelete}
              disabled={isDeleting}
            >
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction 
              onClick={handleConfirmDelete}
              disabled={isDeleting}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {isDeleting ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Deleting...
                </>
              ) : (
                'Delete'
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </Layout>
  )
}
