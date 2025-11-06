/**
 * Stream Detection Configuration page
 * User Story 2: Filter Detected Objects by Label
 * User Story 3: Set Minimum Confidence Threshold
 *
 * Allows users to:
 * - Enable/disable object detection per stream
 * - Select which COCO class labels to detect
 * - Adjust minimum confidence threshold
 * - View live stream preview with bounding boxes
 */

import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import Layout from '@/components/Layout';
import { LabelSelector } from '@/components/LabelSelector';
import { ConfidenceSlider } from '@/components/ConfidenceSlider';
import { useStreams } from '@/hooks/useStreams';
import { getDetectionConfig, updateDetectionConfig, type StreamDetectionConfig } from '@/services/detection';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Skeleton } from '@/components/ui/skeleton';
import { AlertCircle, ArrowLeft, Save, Check } from 'lucide-react';
import { toast } from 'sonner';

export default function StreamDetection() {
  const { streamId } = useParams<{ streamId: string }>();
  const navigate = useNavigate();
  const { streams, isLoading: streamsLoading } = useStreams();

  const [config, setConfig] = useState<StreamDetectionConfig | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const stream = streams.find(s => s.id === streamId);

  // Load detection config on mount
  useEffect(() => {
    const loadConfig = async () => {
      if (!streamId) return;

      try {
        setIsLoading(true);
        setError(null);
        const detectionConfig = await getDetectionConfig(streamId);
        setConfig(detectionConfig);
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Failed to load detection config';
        setError(errorMessage);
        toast.error('Failed to load detection config', {
          description: errorMessage,
        });
      } finally {
        setIsLoading(false);
      }
    };

    loadConfig();
  }, [streamId]);

  const handleSave = async () => {
    if (!streamId || !config) return;

    try {
      setIsSaving(true);
      setError(null);

      const result = await updateDetectionConfig(streamId, config);

      toast.success('Detection config saved', {
        description: result.applied_immediately
          ? 'Changes applied immediately to live stream'
          : 'Restart stream to apply changes',
        icon: <Check className="h-4 w-4" />,
      });

      // Navigate back after short delay
      setTimeout(() => {
        navigate('/');
      }, 1500);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to save detection config';
      setError(errorMessage);
      toast.error('Failed to save detection config', {
        description: errorMessage,
      });
    } finally {
      setIsSaving(false);
    }
  };

  const handleCancel = () => {
    navigate('/');
  };

  if (streamsLoading || isLoading) {
    return (
      <Layout>
        <div className="container mx-auto px-4 py-8 max-w-4xl">
          <Skeleton className="h-8 w-64 mb-6" />
          <Skeleton className="h-[600px] w-full" />
        </div>
      </Layout>
    );
  }

  if (!stream) {
    return (
      <Layout>
        <div className="container mx-auto px-4 py-8 max-w-4xl">
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              Stream with ID "{streamId}" not found
            </AlertDescription>
          </Alert>
          <Button variant="outline" className="mt-4" onClick={() => navigate('/')}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Dashboard
          </Button>
        </div>
      </Layout>
    );
  }

  if (!config) {
    return (
      <Layout>
        <div className="container mx-auto px-4 py-8 max-w-4xl">
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error || 'Failed to load detection config'}</AlertDescription>
          </Alert>
          <Button variant="outline" className="mt-4" onClick={() => navigate('/')}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Dashboard
          </Button>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="container mx-auto px-4 py-8 max-w-4xl">
        {/* Header */}
        <div className="mb-6">
          <Link to="/" className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground mb-4">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Dashboard
          </Link>
          <h1 className="text-3xl font-bold">Detection Settings</h1>
          <p className="text-muted-foreground mt-2">Configure object detection for "{stream.name}"</p>
        </div>

        {/* Error Alert */}
        {error && (
          <Alert variant="destructive" className="mb-6">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        <div className="space-y-6">
          {/* Enable Detection Toggle */}
          <Card>
            <CardHeader>
              <CardTitle>Detection Status</CardTitle>
              <CardDescription>
                Enable or disable object detection for this stream
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between">
                <div className="space-y-1">
                  <Label htmlFor="detection-enabled" className="text-base">
                    Object Detection
                  </Label>
                  <p className="text-sm text-muted-foreground">
                    {config.enabled
                      ? 'Bounding boxes will be displayed on detected objects'
                      : 'Stream will play without object detection'}
                  </p>
                </div>
                <Switch
                  id="detection-enabled"
                  checked={config.enabled}
                  onCheckedChange={(checked) => setConfig({ ...config, enabled: checked })}
                />
              </div>
            </CardContent>
          </Card>

          {/* Label Selection */}
          {config.enabled && (
            <Card>
              <CardHeader>
                <CardTitle>Object Labels</CardTitle>
                <CardDescription>
                  Select which object classes to detect and display
                </CardDescription>
              </CardHeader>
              <CardContent>
                <LabelSelector
                  selectedLabels={config.enabled_labels}
                  onChange={(labels) => setConfig({ ...config, enabled_labels: labels })}
                />
              </CardContent>
            </Card>
          )}

          {/* Confidence Threshold */}
          {config.enabled && (
            <Card>
              <CardHeader>
                <CardTitle>Confidence Threshold</CardTitle>
                <CardDescription>
                  Minimum confidence score (0-1) for displaying detections
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ConfidenceSlider
                  value={config.min_confidence}
                  onChange={(value) => setConfig({ ...config, min_confidence: value })}
                />
              </CardContent>
            </Card>
          )}

          {/* Live Preview */}
          {config.enabled && stream.status === 'running' && (
            <Card>
              <CardHeader>
                <CardTitle>Live Preview</CardTitle>
                <CardDescription>
                  Real-time view of detection with current settings
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="relative aspect-video bg-muted rounded-lg overflow-hidden">
                  <img
                    src={`/api/streams/${streamId}/stream`}
                    alt={stream.name}
                    className="w-full h-full object-contain"
                  />
                </div>
                <p className="text-sm text-muted-foreground mt-2">
                  Note: Preview will update after saving changes
                </p>
              </CardContent>
            </Card>
          )}

          {/* Action Buttons */}
          <div className="flex gap-4 justify-end">
            <Button variant="outline" onClick={handleCancel} disabled={isSaving}>
              Cancel
            </Button>
            <Button onClick={handleSave} disabled={isSaving}>
              {isSaving ? (
                <>
                  <span className="mr-2">Saving...</span>
                </>
              ) : (
                <>
                  <Save className="mr-2 h-4 w-4" />
                  Save Changes
                </>
              )}
            </Button>
          </div>
        </div>
      </div>
    </Layout>
  );
}
