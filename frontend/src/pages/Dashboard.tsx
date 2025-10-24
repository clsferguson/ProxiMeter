import { useEffect, useState, useRef } from 'react';
import { Link } from 'react-router-dom';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Plus, Pencil, Trash2, Loader2 } from 'lucide-react';

interface Stream {
  id: string;
  name: string;
  rtsp_url: string;
  status: 'running' | 'stopped' | 'error';
  target_fps: number;
  hw_accel_enabled: boolean;
  created_at: string;
  order: number;
}

export default function Dashboard() {
  const [streams, setStreams] = useState<Stream[]>([]);
  const [loading, setLoading] = useState(true);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  
  // Use ref to track active streams for cleanup without adding to deps
  const activeStreamIds = useRef<string[]>([]);

  const fetchStreams = async () => {
    try {
      const response = await fetch('/api/streams');
      const data = await response.json();
      setStreams(data);
      
      // Update ref with running stream IDs
      activeStreamIds.current = data
        .filter((s: Stream) => s.status === 'running')
        .map((s: Stream) => s.id);
      
      return data;
    } catch (error) {
      console.error('Error fetching streams:', error);
      return [];
    }
  };

  const startStream = async (streamId: string) => {
    try {
      await fetch(`/api/streams/${streamId}/start`, { method: 'POST' });
    } catch (error) {
      console.error(`Error starting stream ${streamId}:`, error);
    }
  };

  const stopStream = async (streamId: string) => {
    try {
      await fetch(`/api/streams/${streamId}/stop`, { method: 'POST' });
    } catch (error) {
      console.error(`Error stopping stream ${streamId}:`, error);
    }
  };

  // Auto-start all stopped streams on mount
  useEffect(() => {
    const initializeStreams = async () => {
      setLoading(true);
      const fetchedStreams = await fetchStreams();
      
      // Start all stopped streams
      const startPromises = fetchedStreams
        .filter((stream: Stream) => stream.status === 'stopped')
        .map((stream: Stream) => startStream(stream.id));
      
      await Promise.all(startPromises);
      
      // Refresh to get updated statuses
      await fetchStreams();
      setLoading(false);
    };

    initializeStreams();

    // Auto-refresh every 2 seconds
    const interval = setInterval(fetchStreams, 2000);

    // Cleanup: stop all streams when component unmounts
    return () => {
      clearInterval(interval);
      
      // Stop all active streams tracked in ref
      activeStreamIds.current.forEach(streamId => {
        stopStream(streamId);
      });
    };
  }, []); // Empty deps is correct - only run on mount/unmount

  const handleDelete = async (streamId: string, streamName: string) => {
    if (!confirm(`Are you sure you want to delete "${streamName}"?`)) {
      return;
    }

    setDeletingId(streamId);
    try {
      // Stop stream first if running
      const stream = streams.find(s => s.id === streamId);
      if (stream?.status === 'running') {
        await stopStream(streamId);
      }

      const response = await fetch(`/api/streams/${streamId}`, {
        method: 'DELETE',
      });
      
      if (!response.ok) {
        throw new Error('Failed to delete stream');
      }
      
      await fetchStreams();
    } catch (error) {
      console.error('Error deleting stream:', error);
      alert('Failed to delete stream');
    } finally {
      setDeletingId(null);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'running':
        return 'bg-green-100 text-green-800 border-green-200';
      case 'stopped':
        return 'bg-gray-100 text-gray-800 border-gray-200';
      case 'error':
        return 'bg-red-100 text-red-800 border-red-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin mx-auto mb-2" />
          <div className="text-lg">Initializing streams...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6 max-w-7xl">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold">ProxiMeter</h1>
          <p className="text-gray-600 mt-1">RTSP Stream Management</p>
        </div>
        <Link to="/streams/new">
          <Button className="flex items-center gap-2">
            <Plus className="w-4 h-4" />
            Add Stream
          </Button>
        </Link>
      </div>

      {streams.length === 0 ? (
        <Card>
          <CardContent className="text-center py-12">
            <p className="text-gray-500 mb-4">No streams configured yet</p>
            <Link to="/streams/new">
              <Button>Add Your First Stream</Button>
            </Link>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {streams.map((stream) => (
            <Card key={stream.id} className="overflow-hidden">
              <CardContent className="p-0">
                {/* Video Preview */}
                <div className="relative bg-gray-900 aspect-video">
                  {stream.status === 'running' ? (
                    <img
                      src={`/api/streams/${stream.id}/mjpeg?t=${Date.now()}`}
                      alt={stream.name}
                      className="w-full h-full object-cover"
                    />
                  ) : stream.status === 'stopped' ? (
                    <div className="w-full h-full flex items-center justify-center text-gray-400">
                      <div className="text-center">
                        <Loader2 className="w-12 h-12 animate-spin mx-auto mb-2 opacity-50" />
                        <p className="text-sm">Starting stream...</p>
                      </div>
                    </div>
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-gray-400">
                      <div className="text-center">
                        <p className="text-sm">Stream Error</p>
                        <p className="text-xs mt-1 opacity-70">Check RTSP URL</p>
                      </div>
                    </div>
                  )}
                  
                  {/* Status Badge */}
                  <div className="absolute top-2 right-2">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium border ${getStatusColor(stream.status)}`}>
                      {stream.status}
                    </span>
                  </div>
                </div>

                {/* Stream Info */}
                <div className="p-4">
                  <h3 className="font-semibold text-lg mb-2">{stream.name}</h3>
                  
                  <div className="flex flex-wrap gap-2 text-xs text-gray-600 mb-4">
                    <span className="bg-gray-100 px-2 py-1 rounded">
                      {stream.target_fps} FPS
                    </span>
                    {stream.hw_accel_enabled && (
                      <span className="bg-blue-100 text-blue-700 px-2 py-1 rounded">
                        GPU
                      </span>
                    )}
                  </div>

                  {/* Action Buttons */}
                  <div className="flex gap-2">
                    <Link to={`/streams/${stream.id}/edit`} className="flex-1">
                      <Button variant="outline" size="sm" className="w-full">
                        <Pencil className="w-4 h-4 mr-1" />
                        Edit
                      </Button>
                    </Link>
                    
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleDelete(stream.id, stream.name)}
                      disabled={deletingId === stream.id}
                    >
                      {deletingId === stream.id ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <Trash2 className="w-4 h-4" />
                      )}
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
