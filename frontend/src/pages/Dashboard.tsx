import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Plus, Play, Square, Pencil, Trash2 } from 'lucide-react';

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
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const fetchStreams = async () => {
    try {
      const response = await fetch('/api/streams');
      const data = await response.json();
      setStreams(data);
    } catch (error) {
      console.error('Error fetching streams:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStreams();
    const interval = setInterval(fetchStreams, 2000);
    return () => clearInterval(interval);
  }, []);

  const handleStartStop = async (streamId: string, currentStatus: string) => {
    setActionLoading(streamId);
    try {
      const endpoint = currentStatus === 'running' ? 'stop' : 'start';
      const response = await fetch(`/api/streams/${streamId}/${endpoint}`, {
        method: 'POST',
      });
      
      if (!response.ok) {
        throw new Error(`Failed to ${endpoint} stream`);
      }
      
      await fetchStreams();
    } catch (error) {
      console.error('Error toggling stream:', error);
      alert(`Failed to ${currentStatus === 'running' ? 'stop' : 'start'} stream`);
    } finally {
      setActionLoading(null);
    }
  };

  const handleDelete = async (streamId: string, streamName: string) => {
    if (!confirm(`Are you sure you want to delete "${streamName}"?`)) {
      return;
    }

    setActionLoading(streamId);
    try {
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
      setActionLoading(null);
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
        <div className="text-lg">Loading streams...</div>
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
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-gray-400">
                      <div className="text-center">
                        <Square className="w-12 h-12 mx-auto mb-2 opacity-50" />
                        <p className="text-sm">
                          {stream.status === 'error' ? 'Stream Error' : 'Stream Stopped'}
                        </p>
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
                    <Button
                      onClick={() => handleStartStop(stream.id, stream.status)}
                      disabled={actionLoading === stream.id}
                      variant={stream.status === 'running' ? 'destructive' : 'default'}
                      className="flex-1"
                      size="sm"
                    >
                      {actionLoading === stream.id ? (
                        'Loading...'
                      ) : stream.status === 'running' ? (
                        <>
                          <Square className="w-4 h-4 mr-1" />
                          Stop
                        </>
                      ) : (
                        <>
                          <Play className="w-4 h-4 mr-1" />
                          Start
                        </>
                      )}
                    </Button>
                    
                    <Link to={`/streams/${stream.id}/edit`}>
                      <Button variant="outline" size="sm">
                        <Pencil className="w-4 h-4" />
                      </Button>
                    </Link>
                    
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleDelete(stream.id, stream.name)}
                      disabled={actionLoading === stream.id}
                    >
                      <Trash2 className="w-4 h-4" />
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
