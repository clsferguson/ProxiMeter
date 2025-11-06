/**
 * Model Management Page
 * User Story 5: Manage Cached YOLO Models
 *
 * Administrative page for viewing and managing cached YOLO models
 */

import { Link } from 'react-router-dom';
import Layout from '@/components/Layout';
import { ModelManagement as ModelManagementComponent } from '@/components/ModelManagement';
import { ArrowLeft } from 'lucide-react';

export default function ModelManagement() {
  return (
    <Layout>
      <div className="container mx-auto px-4 py-8 max-w-6xl">
        {/* Header */}
        <div className="mb-6">
          <Link
            to="/"
            className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground mb-4"
          >
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Dashboard
          </Link>
          <h1 className="text-3xl font-bold">Model Management</h1>
          <p className="text-muted-foreground mt-2">
            View and manage cached YOLO models to free up disk space
          </p>
        </div>

        {/* Model Management Component */}
        <ModelManagementComponent />

        {/* Additional Info */}
        <div className="mt-6 p-4 bg-muted rounded-lg">
          <h3 className="text-sm font-medium mb-2">About Model Cache</h3>
          <ul className="text-sm text-muted-foreground space-y-1">
            <li>• Models are downloaded automatically on first use</li>
            <li>• Cached models persist in the Docker volume at <code className="px-1 py-0.5 bg-background rounded">/app/models</code></li>
            <li>• Deleting a model frees disk space but the model will re-download if needed</li>
            <li>• The active model (currently loaded) cannot be deleted</li>
            <li>• Model selection is configured via environment variables at container startup</li>
          </ul>
        </div>
      </div>
    </Layout>
  );
}
