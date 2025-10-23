/**
 * ErrorBoundary Component - Graceful error handling for React components
 * 
 * Composes shadcn/ui primitives: Alert, AlertDescription, Button
 * 
 * Catches JavaScript errors anywhere in the child component tree,
 * logs those errors, and displays a fallback UI instead of crashing.
 * 
 * Features:
 * - Catches render errors in child components
 * - Displays user-friendly error message via shadcn/ui Alert
 * - Provides retry button to recover from error state
 * - Logs error details to console for debugging
 * - Responsive design with Tailwind CSS
 * 
 * @component
 * @param {ErrorBoundaryProps} props - Component props
 * @param {React.ReactNode} props.children - Child components to wrap
 * @param {string} [props.fallbackTitle="Something went wrong"] - Error title
 * @param {string} [props.fallbackMessage] - Error message (defaults to generic message)
 * @returns {JSX.Element} Rendered component or error fallback
 * 
 * @example
 * <ErrorBoundary>
 *   <Dashboard />
 * </ErrorBoundary>
 */

import React from 'react'
import type { ReactNode } from 'react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { AlertCircle, RotateCcw } from 'lucide-react'

interface ErrorBoundaryProps {
  children: ReactNode
  fallbackTitle?: string
  fallbackMessage?: string
}

interface ErrorBoundaryState {
  hasError: boolean
  error: Error | null
}

export class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props)
    this.state = {
      hasError: false,
      error: null,
    }
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return {
      hasError: true,
      error,
    }
  }

  override componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    // Log error details for debugging
    console.error('ErrorBoundary caught an error:', error)
    console.error('Error info:', errorInfo)
  }

  handleReset = () => {
    this.setState({
      hasError: false,
      error: null,
    })
  }

  override render() {
    if (this.state.hasError) {
      return (
        <div className="flex items-center justify-center min-h-screen p-4">
          <div className="w-full max-w-md">
            <Alert variant="destructive" className="mb-4">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                <h2 className="font-semibold mb-2">
                  {this.props.fallbackTitle || 'Something went wrong'}
                </h2>
                <p className="text-sm mb-4">
                  {this.props.fallbackMessage ||
                    'An unexpected error occurred. Please try again or contact support if the problem persists.'}
                </p>
                {this.state.error && (
                  <details className="text-xs mt-2 p-2 bg-destructive/10 rounded">
                    <summary className="cursor-pointer font-mono">Error details</summary>
                    <pre className="mt-2 overflow-auto max-h-32 text-xs">
                      {this.state.error.toString()}
                    </pre>
                  </details>
                )}
              </AlertDescription>
            </Alert>

            <div className="flex gap-2">
              <Button onClick={this.handleReset} className="flex-1" variant="default">
                <RotateCcw className="h-4 w-4 mr-2" />
                Try Again
              </Button>
              <Button
                onClick={() => (window.location.href = '/')}
                className="flex-1"
                variant="outline"
              >
                Go Home
              </Button>
            </div>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}

export default ErrorBoundary
