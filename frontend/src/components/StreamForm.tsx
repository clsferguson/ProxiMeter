/**
 * StreamForm Component - Reusable form for adding and editing streams
 * 
 * Composes shadcn/ui primitives: Form, FormControl, FormDescription, FormField, FormItem, FormLabel, FormMessage,
 * Card, CardContent, CardDescription, CardHeader, CardTitle, Alert, AlertDescription, Button, Input
 * 
 * User Stories 2 & 3: Add/Edit Stream forms
 * 
 * Features:
 * - Client-side validation using react-hook-form + zod
 * - Real-time error display via shadcn/ui FormMessage
 * - Loading state during submission with disabled button
 * - Cancel button to return to dashboard
 * - Accessible form with proper labels and descriptions
 * - Responsive layout using Tailwind CSS
 * 
 * @component
 * @param {StreamFormProps} props - Component props
 * @param {StreamResponse} [props.initialValues] - Initial values for edit mode, undefined for add mode
 * @param {Function} props.onSubmit - Callback when form is submitted successfully
 * @param {boolean} [props.isLoading=false] - Whether the form is currently submitting
 * @param {string|null} [props.error=null] - Error message to display
 * @param {string} [props.submitLabel="Add Stream"] - Submit button label
 * @param {boolean} [props.isEdit=false] - Whether this is an edit form
 * @returns {JSX.Element} Rendered form
 * 
 * @example
 * <StreamForm
 *   onSubmit={handleSubmit}
 *   submitLabel="Add Stream"
 * />
 */

import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import * as z from 'zod'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Switch } from '@/components/ui/switch'
import { Textarea } from '@/components/ui/textarea'
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
import { getGpuBackend } from '@/hooks/useApi'

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
  hw_accel_enabled: z.boolean().default(true),
  ffmpeg_params: z.string().optional().transform(val => val ? val.split(' ').filter(Boolean) : []),
  target_fps: z.coerce.number().min(1).max(30).default(5),
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
  const [gpuBackend, setGpuBackend] = useState('none')
  const [paramsPlaceholder, setParamsPlaceholder] = useState('')

  const form = useForm<StreamFormData>({
    resolver: zodResolver(streamFormSchema),
    defaultValues: {
      name: initialValues?.name || '',
      rtsp_url: initialValues?.rtsp_url || '',
      hw_accel_enabled: initialValues?.hw_accel_enabled ?? true,
      ffmpeg_params: initialValues?.ffmpeg_params?.join(' ') || '',
      target_fps: initialValues?.target_fps ?? 5,
    },
    mode: 'onBlur', // Validate on blur for better UX
  })

  useEffect(() => {
    getGpuBackend()
      .then(data => {
        setGpuBackend(data.gpu_backend)
        let placeholder = '-hide_banner -loglevel warning -threads 2 -rtsp_transport tcp -timeout 10000000'
        if (data.gpu_backend === 'nvidia') {
          placeholder += ' -hwaccel cuda -hwaccel_output_format cuda -c:v h264_cuvid'
        } else if (data.gpu_backend === 'amd') {
          placeholder += ' -hwaccel amf -c:v h264_amf'
        } else if (data.gpu_backend === 'intel') {
          placeholder += ' -hwaccel qsv -c:v h264_qsv'
        }
        setParamsPlaceholder(placeholder)
      })
      .catch(() => setGpuBackend('none'))
  }, [])

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
                    <br />
                    Note: Future zone coordinates will be normalized (0-1) relative to stream resolution for consistency.
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Hardware Acceleration Switch */}
            <FormField
              control={form.control}
              name="hw_accel_enabled"
              render={({ field }) => (
                <FormItem className="flex flex-row items-center justify-between rounded-lg border p-4">
                  <div className="space-y-0.5">
                    <FormLabel className="text-base">
                      Hardware Acceleration
                    </FormLabel>
                    <FormDescription>
                      Enable GPU acceleration if available ({gpuBackend})
                    </FormDescription>
                  </div>
                  <FormControl>
                    <Switch
                      checked={field.value}
                      onCheckedChange={field.onChange}
                    />
                  </FormControl>
                </FormItem>
              )}
            />

            {/* FFmpeg Parameters Field */}
            <FormField
              control={form.control}
              name="ffmpeg_params"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>FFmpeg Parameters</FormLabel>
                  <FormControl>
                    <Textarea
                      placeholder={paramsPlaceholder}
                      {...field}
                    />
                  </FormControl>
                  <FormDescription>
                    Space-separated FFmpeg flags (defaults shown; edit for custom)
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Target FPS Field */}
            <FormField
              control={form.control}
              name="target_fps"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Target FPS</FormLabel>
                  <FormControl>
                    <Input
                      type="number"
                      min={1}
                      max={30}
                      placeholder="5"
                      {...field}
                    />
                  </FormControl>
                  <FormDescription>
                    Frames per second (1-30, default 5)
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
