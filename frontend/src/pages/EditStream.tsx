/**
 * Edit Stream page - Modify existing RTSP stream
 * User Story 3: Edit Existing Stream
 */

import { useParams } from 'react-router-dom'
import Layout from '@/components/Layout'

export default function EditStream() {
  const { streamId } = useParams<{ streamId: string }>()

  return (
    <Layout>
      <div className="container mx-auto p-6">
        <h1 className="text-3xl font-bold mb-6">Edit Stream</h1>
        <p className="text-muted-foreground">
          Editing stream: {streamId}
        </p>
        <p className="text-muted-foreground">Edit stream form will be implemented in Phase 5</p>
      </div>
    </Layout>
  )
}
