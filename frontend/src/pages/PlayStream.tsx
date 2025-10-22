/**
 * Play Stream page - View live RTSP stream
 * User Story 4: Play Live Stream
 */

import { useParams } from 'react-router-dom'
import Layout from '@/components/Layout'

export default function PlayStream() {
  const { streamId } = useParams<{ streamId: string }>()

  return (
    <Layout>
      <div className="container mx-auto p-6">
        <h1 className="text-3xl font-bold mb-6">Play Stream</h1>
        <p className="text-muted-foreground">
          Playing stream: {streamId}
        </p>
        <p className="text-muted-foreground">Video player will be implemented in Phase 6</p>
      </div>
    </Layout>
  )
}
