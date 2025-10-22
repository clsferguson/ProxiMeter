/**
 * Reusable stream form component for adding and editing streams
 * User Stories 2 & 3: Add/Edit Stream forms
 * 
 * Uses react-hook-form with zod validation and shadcn/ui components
 */

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import * as z from 'zod'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { AlertCircle } from 'lucide-react'

import type { StreamResponse } from '@/lib/types'
import { VALIDATION } from '@/lib/constants'

/**
 * Validation schema for stream form
 * Matches spec requirements for stream creation/editing
 */
const streamFormSchema = z.object({
  name: z
    .string()
    .min(1, 'Stream name is required')
    .max(100, 'Stream name must be at most 100 characters'),
  rtsp_url: z
    .string()
    .min(1, 'RTSP URL is required')
    .refine(
      (url) => url.startsWith(VALIDATION.RTSP_URL_PREFIX),
      `Invalid RTSP URL format. Expected ${VALIDATION.RTSP_URL_PREFIX}...`
    ),
})

type StreamFormData = z.infer<typeof streamFormSchema>

interface StreamFormProps {
  /** Initial values for edit mode, undefined for add mode */
  initialValues?: StreamResponse
  /** Callback when form is submitted successfully */
  onSubmit: (data: StreamFormData) => Promise<void>
  /** Whether the form is currently submitting */
  isLoading?: boolean
  /** Error message to display */
  error?: string | null
  /** Submit button label (default: "Add Stream") */
  submitLabel?: string
  /** Whether this is an edit form */
  isEdit?: boolean
}

/**
 * StreamForm component - reusable form for adding/editing streams
 * 
 * Features:
 * - Client-side validation with zod
 * - Real-time error display
 * - Loading state during submission
 * - Cancel button to return to dashboard
 * - Accessible form with proper labels and descriptions
 */
export function StreamForm({
  initialValues,
  onSubmit,
  isLoading = false,
  error = null,
  submitLabel = 'Add Stream',
  isEdit = false,
}: StreamFormProps) {
  const navigate = useNavigate()
  const [submitError, setSubmitError] = useState<string | null>(error)

  const form = useForm<StreamFormData>({
    resolver: zodResolver(streamFormSchema),
    defaultValues: {
      name: initialValues?.name || '',
      rtsp_url: initialValues?.rtsp_url || '',
    },
    mode: 'onBlur', // Validate on blur for better UX
  })

  const handleSubmit = async (data: StreamFormData) => {
    try {
      setSubmitError(null)
      await onSubmit(data)
      // Navigation happens in parent component after successful submission
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to save stream'
      setSubmitError(errorMessage)
      console.error('Form submission error:', err)
    }
  }

  const handleCancel = () => {
    navigate('/')
  }

  return (
    <Card className="w-full max-w-2xl mx-auto">
      <CardHeader>
        <CardTitle>{isEdit ? 'Edit Stream' : 'Add New Stream'}</CardTitle>
        <CardDescription>
          {isEdit
            ? 'Update the stream configuration below'
            : 'Configure a new RTSP stream for monitoring'}
        </CardDescription>
      </CardHeader>
      <CardContent>
        {submitError && (
          <Alert variant="destructive" className="mb-6">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{submitError}</AlertDescription>
          </Alert>
        )}

        <Form {...form}>
          <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-6">
            {/* Stream Name Field */}
            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Stream Name</FormLabel>
                  <FormControl>
                    <Input
                      placeholder="e.g., Front Door Camera"
                      disabled={isLoading}
                      {...field}
                    />
                  </FormControl>
                  <FormDescription>
                    A descriptive name for this stream (max 100 characters)
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* RTSP URL Field */}
            <FormField
              control={form.control}
              name="rtsp_url"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>RTSP URL</FormLabel>
                  <FormControl>
                    <Input
                      placeholder="rtsp://username:password@host:port/path"
                      disabled={isLoading}
                      {...field}
                    />
                  </FormControl>
                  <FormDescription>
                    The RTSP stream URL (must start with rtsp://)
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Form Actions */}
            <div className="flex gap-3 pt-4">
              <Button
                type="submit"
                disabled={isLoading}
                className="flex-1"
              >
                {isLoading ? (
                  <>
                    <span className="mr-2">⏳</span>
                    {isEdit ? 'Saving...' : 'Adding...'}
                  </>
                ) : (
                  submitLabel
                )}
              </Button>
              <Button
                type="button"
                variant="outline"
                onClick={handleCancel}
                disabled={isLoading}
              >
                Cancel
              </Button>
            </div>
          </form>
        </Form>
      </CardContent>
    </Card>
  )
}
