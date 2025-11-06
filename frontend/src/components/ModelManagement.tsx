/**
 * ModelManagement Component
 * User Story 5: Manage Cached YOLO Models
 *
 * Displays cached YOLO models with ability to delete unused models
 */

import { useState, useEffect } from 'react';
import { listCachedModels, deleteCachedModel, type CachedModel } from '@/services/detection';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Skeleton } from '@/components/ui/skeleton';
import { AlertCircle, Trash2, RefreshCw, CheckCircle } from 'lucide-react';
import { toast } from 'sonner';

export function ModelManagement() {
  const [models, setModels] = useState<CachedModel[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [modelToDelete, setModelToDelete] = useState<CachedModel | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const loadModels = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const data = await listCachedModels();
      setModels(data.models);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to load models';
      setError(errorMessage);
      toast.error('Failed to load models', { description: errorMessage });
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadModels();
  }, []);

  const handleDeleteClick = (model: CachedModel) => {
    setModelToDelete(model);
    setDeleteDialogOpen(true);
  };

  const handleDeleteConfirm = async () => {
    if (!modelToDelete) return;

    try {
      setIsDeleting(true);
      await deleteCachedModel(modelToDelete.model_name);

      const freedMB = (modelToDelete.file_size_bytes / (1024 * 1024)).toFixed(1);
      toast.success('Model deleted', {
        description: `Freed ${freedMB} MB of disk space`,
        icon: <CheckCircle className="h-4 w-4" />,
      });

      // Refresh model list
      await loadModels();
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to delete model';
      toast.error('Failed to delete model', { description: errorMessage });
    } finally {
      setIsDeleting(false);
      setDeleteDialogOpen(false);
      setModelToDelete(null);
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`;
  };

  const formatDate = (timestamp: number): string => {
    return new Date(timestamp * 1000).toLocaleString();
  };

  const getTotalSize = (): string => {
    const total = models.reduce((sum, model) => sum + model.file_size_bytes, 0);
    return formatFileSize(total);
  };

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Cached YOLO Models</CardTitle>
          <CardDescription>Loading models...</CardDescription>
        </CardHeader>
        <CardContent>
          <Skeleton className="h-40 w-full" />
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Cached YOLO Models</CardTitle>
        </CardHeader>
        <CardContent>
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
          <Button variant="outline" className="mt-4" onClick={loadModels}>
            <RefreshCw className="mr-2 h-4 w-4" />
            Retry
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <>
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Cached YOLO Models</CardTitle>
              <CardDescription>
                Manage downloaded YOLO models ({models.length} model{models.length !== 1 ? 's' : ''}, {getTotalSize()} total)
              </CardDescription>
            </div>
            <Button variant="outline" size="sm" onClick={loadModels}>
              <RefreshCw className="mr-2 h-4 w-4" />
              Refresh
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {models.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <p>No cached models found</p>
              <p className="text-sm mt-2">Models will be downloaded on first use</p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Model Name</TableHead>
                  <TableHead>File Size</TableHead>
                  <TableHead>Downloaded</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {models.map((model) => (
                  <TableRow key={model.model_name}>
                    <TableCell className="font-mono text-sm">
                      {model.model_name}
                    </TableCell>
                    <TableCell>{formatFileSize(model.file_size_bytes)}</TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {formatDate(model.download_date)}
                    </TableCell>
                    <TableCell>
                      {model.is_active ? (
                        <Badge variant="default">Active</Badge>
                      ) : (
                        <Badge variant="secondary">Cached</Badge>
                      )}
                    </TableCell>
                    <TableCell className="text-right">
                      <Button
                        variant="ghost"
                        size="sm"
                        disabled={model.is_active}
                        onClick={() => handleDeleteClick(model)}
                      >
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}

          {models.some((m) => m.is_active) && (
            <p className="text-xs text-muted-foreground mt-4">
              Note: Active models cannot be deleted. Stop using the model first or restart with a different model.
            </p>
          )}
        </CardContent>
      </Card>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Model?</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete <strong>{modelToDelete?.model_name}</strong>?
              This will free {modelToDelete ? formatFileSize(modelToDelete.file_size_bytes) : '0 B'} of disk space.
              <br />
              <br />
              The model will be re-downloaded if needed in the future.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isDeleting}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeleteConfirm}
              disabled={isDeleting}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {isDeleting ? 'Deleting...' : 'Delete'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
