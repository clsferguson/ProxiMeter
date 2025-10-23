/**
 * EmptyState Component - Displayed when no streams are configured
 * 
 * Composes shadcn/ui primitives: Button, Alert
 * Uses lucide-react icons for visual emphasis
 * 
 * Shows a centered message with:
 * - Large icon (AlertCircle from lucide-react)
 * - Descriptive heading and text
 * - Prominent "Add First Stream" CTA button using shadcn/ui Button
 * - Helpful tip box with RTSP URL format example
 * 
 * @component
 * @returns {JSX.Element} Rendered empty state
 * 
 * @example
 * <EmptyState />
 */

import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { AlertCircle, Plus } from 'lucide-react'

export default function EmptyState() {
  return (
    <div className="flex items-center justify-center py-12">
      <div className="text-center max-w-md">
        <div className="bg-muted rounded-lg p-8 mb-6">
          <AlertCircle className="h-16 w-16 text-muted-foreground mx-auto opacity-50" />
        </div>
        
        <h2 className="text-2xl font-bold mb-2">No Streams Configured</h2>
        <p className="text-muted-foreground mb-6">
          Get started by adding your first RTSP stream to monitor it in real-time.
        </p>

        <Link to="/add">
          <Button size="lg" className="w-full">
            <Plus className="h-5 w-5 mr-2" />
            Add First Stream
          </Button>
        </Link>

        <div className="mt-8 p-4 bg-muted/50 rounded-lg">
          <p className="text-sm text-muted-foreground">
            <strong>Tip:</strong> You&apos;ll need the RTSP URL of your camera stream to get started.
            The typical format is <code className="bg-background px-2 py-1 rounded text-xs">rtsp://host:port/path</code>
          </p>
        </div>
      </div>
    </div>
  )
}
