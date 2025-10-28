/**
 * StreamForm Component - Add/Edit Stream Configuration
 * 
 * Constitution-compliant stream configuration form with GPU-aware defaults.
 * 
 * Constitution Compliance:
 * - Principle II: 5fps hardcoded, streams always auto-start
 * - Principle III: GPU backend detection and hardware acceleration (always enabled)
 * 
 * Features:
 * - GPU-aware FFmpeg parameter defaults from backend API (single source of truth)
 * - Client-side validation using react-hook-form + zod
 * - Real-time error display
 * - Accessible form with proper ARIA labels
 * 
 * @module components/StreamForm
 */

import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import * as z from 'zod'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
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
import { AlertCircle, Loader2 } from 'lucide-react'
import { getGpuBackend, getFfmpegDefaults } from '@/hooks/useApi'

import type { StreamResponse } from '@/lib/types'

// ============================================================================
// Validation Schema
// ============================================================================

/**
 * Zod validation schema for stream form.
 * 
 * Constitution-compliant validation:
 * - Name: 1-50 characters
 * - RTSP URL: Must start with rtsp:// or rtsps://
 * - FFmpeg params: Optional string (defaults applied on backend if empty)
 * 
 * Note: Hardware acceleration and auto_start are hardcoded on backend per constitution.
 */
const streamFormSchema = z.object({
  name: z
    .string()
    .min(1, 'Stream name is required')
    .max(50, 'Stream name must be 50 characters or less'),
  
  rtsp_url: z
    .string()
    .min(1, 'RTSP URL is required')
    .regex(
      /^rtsps?:\/\/.+/i,
      'Must be a valid RTSP URL (rtsp:// or rtsps://)'
    ),
  
  ffmpeg_params: z.string().optional(),
})

type StreamFormData = z.infer<typeof streamFormSchema>

/**
 * Transformed submission data with ffmpeg_params as string array.
 * Backend expects array format, form uses string for easier editing.
 */
type StreamSubmitData = Omit<StreamFormData, 'ffmpeg_params'> & {
  ffmpeg_params: string[]
}

// ============================================================================
// Component Props
// ============================================================================

interface StreamFormProps {
  /** Initial values for edit mode, undefined for add mode */
  initialValues?: StreamResponse
  /** Callback when form is submitted successfully */
  onSubmit: (data: StreamSubmitData) => Promise<void>
  /** Whether the form is currently submitting */
  isLoading?: boolean
  /** Error message to display */
  error?: string | null
  /** Submit button label (default: "Add Stream") */
  submitLabel?: string
  /** Whether this is an edit form (affects title and descriptions) */
  isEdit?: boolean
}

// ============================================================================
// Main Component
// ============================================================================

/**
 * StreamForm Component
 * 
 * Hardware acceleration and auto-start are always enabled per constitution.
 * Target FPS is hardcoded to 5fps on backend per Principle II.
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
  
  // ========================================================================
  // State Management
  // ========================================================================
  
  const [submitError, setSubmitError] = useState<string | null>(error)
  const [gpuBackend, setGpuBackend] = useState<string>('none')
  const [isLoadingGpu, setIsLoadingGpu] = useState(true)
  const [ffmpegDefaults, setFfmpegDefaults] = useState<string>('')
  
  // ========================================================================
  // Form Initialization
  // ========================================================================
  
  const form = useForm<StreamFormData>({
    resolver: zodResolver(streamFormSchema),
    defaultValues: {
      name: initialValues?.name ?? '',
      rtsp_url: initialValues?.rtsp_url ?? '',
      ffmpeg_params: initialValues?.ffmpeg_params?.join(' ') ?? '',
    },
    mode: 'onBlur', // Validate on blur for better UX
  })
  
  // ========================================================================
  // GPU Backend & FFmpeg Defaults Detection
  // ========================================================================
  
  /**
   * Fetch GPU backend and FFmpeg defaults on mount.
   * 
   * Calls:
   * - /api/streams/gpu-backend: Returns GPU_BACKEND_DETECTED env var
   * - /api/streams/ffmpeg-defaults: Returns default FFmpeg parameters
   * 
   * This establishes the single source of truth from backend config.
   * 
   * Constitution Principle III: Explicit GPU backend contract.
   */
  useEffect(() => {
    let mounted = true
    
    const fetchGpuAndDefaults = async () => {
      try {
        // Fetch GPU backend
        const gpuData = await getGpuBackend()
        
        if (!mounted) return
        
        setGpuBackend(gpuData.gpu_backend || 'none')
        
        // Fetch FFmpeg defaults (single source of truth)
        const defaultsData = await getFfmpegDefaults()
        if (mounted) {
          setFfmpegDefaults(defaultsData.combined_params)
        }
        
        // Log GPU status for debugging
        if (gpuData.gpu_backend === 'none') {
          console.warn('No GPU detected - hardware acceleration unavailable')
        } else {
          console.info(`GPU backend detected: ${gpuData.gpu_backend}`)
          console.info(`FFmpeg defaults: ${defaultsData.combined_params}`)
        }
        
      } catch (err) {
        console.error('Failed to fetch GPU backend or FFmpeg defaults:', err)
        if (mounted) {
          setGpuBackend('none')
          setFfmpegDefaults('')
        }
      } finally {
        if (mounted) {
          setIsLoadingGpu(false)
        }
      }
    }
    
    fetchGpuAndDefaults()
    
    return () => {
      mounted = false
    }
  }, [])
  
  // ========================================================================
  // Event Handlers
  // ========================================================================
  
  /**
   * Handle form submission with data transformation.
   * 
   * Transforms ffmpeg_params from space-separated string to array.
   * If empty, backend will apply defaults based on GPU backend.
   */
  const handleSubmit = async (data: StreamFormData) => {
    try {
      setSubmitError(null)
      
      // Transform ffmpeg_params string to array
      // Backend will apply defaults if empty
      const ffmpegParamsArray: string[] = data.ffmpeg_params
        ? data.ffmpeg_params.split(' ').filter(param => param.trim() !== '')
        : []
      
      const transformedData: StreamSubmitData = {
        ...data,
        ffmpeg_params: ffmpegParamsArray,
      }
      
      await onSubmit(transformedData)
      // Navigation handled by parent component after successful submission
      
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to save stream'
      setSubmitError(errorMessage)
      console.error('Form submission error:', err)
    }
  }
  
  /**
   * Handle cancel button - navigate back to dashboard.
   */
  const handleCancel = () => {
    navigate('/')
  }
  
  // ========================================================================
  // Computed Values
  // ========================================================================
  
  // Generate placeholder text from backend FFmpeg defaults
  const ffmpegPlaceholder = isLoadingGpu 
    ? 'Loading GPU backend...'
    : ffmpegDefaults || 'No defaults available'
  
  // ========================================================================
  // Render
  // ========================================================================
  
  return (
    <Card className="w-full max-w-2xl mx-auto">
      <CardHeader>
        <CardTitle>{isEdit ? 'Edit Stream' : 'Add New Stream'}</CardTitle>
        <CardDescription>
          {isEdit
            ? 'Update stream configuration (will require manual restart if FFmpeg params changed)'
            : 'Configure a new RTSP stream (5fps, full resolution, GPU-accelerated, auto-starts)'}
        </CardDescription>
      </CardHeader>
      
      <CardContent>
        {/* Error Display */}
        {submitError && (
          <Alert variant="destructive" className="mb-6">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{submitError}</AlertDescription>
          </Alert>
        )}
        
        {/* GPU Backend Warning */}
        {!isLoadingGpu && gpuBackend === 'none' && (
          <Alert variant="destructive" className="mb-6">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              <strong>No GPU detected.</strong> Hardware acceleration is unavailable.
              This application requires a GPU (NVIDIA/AMD/Intel) for operation.
            </AlertDescription>
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
                    A descriptive name for this camera stream (1-50 characters)
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
                      placeholder="rtsp://username:password@192.168.1.100:554/stream"
                      type="url"
                      disabled={isLoading}
                      {...field}
                    />
                  </FormControl>
                  <FormDescription>
                    Complete RTSP URL including credentials. Must start with rtsp:// or rtsps://
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />
            
            {/* FFmpeg Parameters Field */}
            <FormField
              control={form.control}
              name="ffmpeg_params"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>FFmpeg Parameters (Optional)</FormLabel>
                  <FormControl>
                    <Textarea
                      placeholder={ffmpegPlaceholder}
                      disabled={isLoading || isLoadingGpu}
                      rows={4}
                      className="font-mono text-sm"
                      {...field}
                    />
                  </FormControl>
                  <FormDescription>
                    Space-separated FFmpeg flags. Leave empty to use GPU backend defaults shown above.
                    Custom parameters completely replace defaults (not merged).
                    {isEdit && ' Note: Changing params requires stopping and restarting the stream.'}
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />
            
            {/* Info about hardcoded settings */}
            <Alert>
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                <strong>Note:</strong> All streams use GPU acceleration ({gpuBackend !== 'none' ? gpuBackend : 'unavailable'}), 
                run at 5 FPS, and start automatically. These settings cannot be changed.
              </AlertDescription>
            </Alert>
            
            {/* Form Actions */}
            <div className="flex gap-3 pt-4">
              <Button
                type="submit"
                disabled={isLoading || isLoadingGpu}
                className="flex-1"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
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
