/**
 * Dashboard Page - Stream Overview and Management
 */

import { useState, useEffect } from 'react'
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

export default function Dashboard() {
  
  const { 
    streams, 
    isLoading, 
    error, 
    refetch, 
    deleteStream 
  } = useStreams({ 
    autoFetch: true
  })

  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [streamToDelete, setStreamToDelete] = useState<string | null>(null)
  const [isDeleting, setIsDeleting] = useState(false)

  // ============================================================================
  // Refetch streams when returning to dashboard (e.g., from PlayStream)
  // ============================================================================
  
  useEffect(() => {
    // Refetch when component mounts or becomes visible
    const handleVisibilityChange = () => {
      if (!document.hidden) {
        refetch()
      }
    }

    // Refetch when navigating back to dashboard
    const handleFocus = () => {
      refetch()
    }

    document.addEventListener('visibilitychange', handleVisibilityChange)
    window.addEventListener('focus', handleFocus)

    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange)
      window.removeEventListener('focus', handleFocus)
    }
  }, [refetch])

  const handleDeleteClick = (streamId: string) => {
    setStreamToDelete(streamId)
    setDeleteDialogOpen(true)
  }

  const handleConfirmDelete = async () => {
    if (!streamToDelete) return

    try {
      setIsDeleting(true)
      await deleteStream(streamToDelete)
      setDeleteDialogOpen(false)
      setStreamToDelete(null)
    } catch (err) {
      console.error('Failed to delete stream:', err)
    } finally {
      setIsDeleting(false)
    }
  }

  const handleCancelDelete = () => {
    setDeleteDialogOpen(false)
    setStreamToDelete(null)
  }

  const handleRetry = () => {
    refetch()
  }

  const getStreamName = (): string => {
    if (!streamToDelete) return ''
    const stream = streams.find(s => s.id === streamToDelete)
    return stream?.name || 'this stream'
  }

  return (
    <Layout>
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">Stream Dashboard</h1>
        <p className="text-muted-foreground">
          Monitor your RTSP streams with static snapshots
        </p>
      </div>

      <div className="space-y-6">
        
        {isLoading && streams.length === 0 && (
          <div className="flex flex-col items-center justify-center py-12 space-y-4">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
            <p className="text-muted-foreground">Loading streams...</p>
          </div>
        )}

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

        {!isLoading && !error && streams.length === 0 && (
          <EmptyState />
        )}

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
      </div>

      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Stream</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete <strong>{getStreamName()}</strong>? 
              This action cannot be undone and will stop the stream.
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
