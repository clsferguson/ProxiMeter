/**
 * Edit Stream page - Modify existing RTSP stream
 * User Story 3: Edit Existing Stream
 * 
 * Acceptance Scenarios:
 * 1. User navigates to edit stream - sees form pre-populated with current values
 * 2. User modifies stream settings and saves - config.yml updated, dashboard reflects changes
 * 3. User can delete stream with confirmation dialog
 * 4. User sees error if stream not found - redirects to dashboard
 */

import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import Layout from '@/components/Layout'
import { StreamForm } from '@/components/StreamForm'
import { useStreams } from '@/hooks/useStreams'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
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
import { AlertCircle, Trash2 } from 'lucide-react'
import type { StreamResponse } from '@/lib/types'

interface StreamFormData {
  name: string
  rtsp_url: string
}

export default function EditStream() {
  const { streamId } = useParams<{ streamId: string }>()
  const navigate = useNavigate()
  const { streams, updateStream, deleteStream, isLoading: streamsLoading } = useStreams()
  
  const [stream, setStream] = useState<StreamResponse | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showDeleteDialog, setShowDeleteDialog] = useState(false)
  const [isDeleting, setIsDeleting] = useState(false)

  // Find the stream from the list
  useEffect(() => {
    if (streamId && streams.length > 0) {
      const found = streams.find(s => s.id === streamId)
      if (found) {
        setStream(found)
      } else {
        setError(`Stream with ID "${streamId}" not found`)
      }
    }
  }, [streamId, streams])

  const handleSubmit = async (data: StreamFormData) => {
    if (!streamId) return

    try {
      setIsLoading(true)
      setError(null)
      await updateStream(streamId, data)
      // Navigate back to dashboard after successful update
      navigate('/')
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to update stream'
      setError(errorMessage)
      throw err
    } finally {
      setIsLoading(false)
    }
  }

  const handleDelete = async () => {
    if (!streamId) return

    try {
      setIsDeleting(true)
      setError(null)
      await deleteStream(streamId)
      // Navigate back to dashboard after successful deletion
      navigate('/')
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to delete stream'
      setError(errorMessage)
    } finally {
      setIsDeleting(false)
      setShowDeleteDialog(false)
    }
  }

  // Loading state while fetching streams
  if (streamsLoading && !stream) {
    return (
      <Layout>
        <div className="container mx-auto p-6">
          <div className="flex items-center justify-center py-12">
            <p className="text-muted-foreground">Loading stream...</p>
          </div>
        </div>
      </Layout>
    )
  }

  // Stream not found
  if (error && !stream) {
    return (
      <Layout>
        <div className="container mx-auto p-6">
          <Alert variant="destructive" className="mb-6">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
          <Button onClick={() => navigate('/')}>Back to Dashboard</Button>
        </div>
      </Layout>
    )
  }

  // Stream found - show edit form
  return (
    <Layout>
      <div className="container mx-auto p-6">
        <div className="mb-8">
          <h1 className="text-3xl font-bold mb-2">Edit Stream</h1>
          <p className="text-muted-foreground">
            Update the stream configuration below
          </p>
        </div>

        {error && (
          <Alert variant="destructive" className="mb-6">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {stream && (
          <div className="space-y-6">
            <StreamForm
              initialValues={stream}
              onSubmit={handleSubmit}
              isLoading={isLoading}
              error={error}
              submitLabel="Save Changes"
              isEdit={true}
            />

            {/* Delete Stream Section */}
            <div className="border-t pt-6">
              <h3 className="text-lg font-semibold mb-4 text-destructive">Danger Zone</h3>
              <p className="text-sm text-muted-foreground mb-4">
                Delete this stream permanently. This action cannot be undone.
              </p>
              <Button
                variant="destructive"
                onClick={() => setShowDeleteDialog(true)}
                disabled={isDeleting}
                className="gap-2"
              >
                <Trash2 className="h-4 w-4" />
                Delete Stream
              </Button>
            </div>
          </div>
        )}

        {/* Delete Confirmation Dialog */}
        <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Delete Stream?</AlertDialogTitle>
              <AlertDialogDescription>
                Are you sure you want to delete &quot;{stream?.name}&quot;? This action cannot be undone.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel disabled={isDeleting}>Cancel</AlertDialogCancel>
              <AlertDialogAction
                onClick={handleDelete}
                disabled={isDeleting}
                className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              >
                {isDeleting ? 'Deleting...' : 'Delete'}
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>
    </Layout>
  )
}
