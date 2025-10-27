/**
 * StreamForm Component - Add/Edit Stream Configuration
 * 
 * Constitution-compliant stream configuration form with GPU-aware defaults.
 * 
 * Constitution Compliance:
 * - Principle II: 5fps hardcoded, auto-start always enabled
 * - Principle III: GPU backend detection and hardware acceleration
 * 
 * Features:
 * - GPU-aware FFmpeg parameter defaults
 * - Client-side validation using react-hook-form + zod
 * - Centralized FFmpeg defaults (not hardcoded in component)
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
import { Switch } from '@/components/ui/switch'
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
import { getGpuBackend } from '@/hooks/useApi'

import type { StreamResponse } from '@/lib/types'

// ============================================================================
// FFmpeg Default Parameters by GPU Backend
// ============================================================================

/**
 * Base FFmpeg parameters used for all streams regardless of GPU backend.
 * These control basic stream behavior, logging, and reliability.
 * 
 * Constitution Principle II: FFmpeg handles all RTSP processing.
 */
const BASE_FFMPEG_PARAMS = [
  '-hide_banner',           // Suppress FFmpeg banner output in logs
  '-loglevel', 'warning',   // Only show warnings and errors (reduces log noise)
  '-threads', '2',          // Limit CPU threads to 2 (efficiency for GPU-accelerated workload)
  '-rtsp_transport', 'tcp', // Use TCP instead of UDP for reliability
  '-timeout', '10000000',   // 10 second timeout for network operations (10M microseconds)
] as const

/**
 * GPU-specific hardware acceleration parameters.
 * Applied based on detected GPU backend from entrypoint.sh via GPU_BACKEND_DETECTED env var.
 * 
 * Constitution Principle III: GPU backend contract enforcement.
 * 
 * NVIDIA: Uses CUDA with NVDEC hardware decoder
 * AMD: Uses VAAPI (Video Acceleration API)
 * Intel: Uses Quick Sync Video (QSV)
 */
const GPU_FFMPEG_PARAMS = {
  nvidia: [
    '-hwaccel', 'cuda',                    // Enable NVIDIA CUDA acceleration
    '-hwaccel_output_format', 'cuda',      // Keep decoded frames in GPU memory
    '-c:v', 'h264_cuvid',                  // Use CUDA video decoder (NVDEC)
  ],
  amd: [
    '-hwaccel', 'vaapi',                   // Enable AMD VAAPI acceleration
    '-hwaccel_device', '/dev/dri/renderD128', // AMD GPU device path
    '-c:v', 'h264',                        // Standard H.264 decoder with VAAPI
  ],
  intel: [
    '-hwaccel', 'qsv',                     // Enable Intel Quick Sync Video
    '-hwaccel_device', '/dev/dri/renderD128', // Intel GPU device path
    '-c:v', 'h264_qsv',                    // Intel QSV H.264 decoder
  ],
  none: [] as string[],                    // No hardware acceleration (CPU only - not recommended)
} as const

/**
 * Builds complete FFmpeg parameter string based on detected GPU backend.
 * 
 * This is the single source of truth for default FFmpeg parameters.
 * Parameters are concatenated and used as placeholder in the form.
 * 
 * @param gpuBackend - Detected GPU backend (nvidia, amd, intel, none)
 * @returns Space-separated FFmpeg parameter string
 * 
 * @example
 * buildDefaultFFmpegParams('nvidia')
 * // Returns: "-hide_banner -loglevel warning ... -hwaccel cuda -hwaccel_output_format cuda -c:v h264_cuvid"
 */
function buildDefaultFFmpegParams(gpuBackend: string): string {
  const gpuParams = GPU_FFMPEG_PARAMS[gpuBackend as keyof typeof GPU_FFMPEG_PARAMS] || []
  return [...BASE_FFMPEG_PARAMS, ...gpuParams].join(' ')
}

// ============================================================================
// Validation Schema
// ============================================================================

/**
 * Zod validation schema for stream form.
 * 
 * Constitution-compliant validation:
 * - Name: 1-50 characters
 * - RTSP URL: Must start with rtsp:// or rtsps://
 * - Hardware acceleration: Boolean (default true)
 * - FFmpeg params: Optional string (defaults applied on backend if empty)
 * 
 * Note: auto_start and target_fps are hardcoded on backend per constitution.
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
  
  hw_accel_enabled: z.boolean(),
  
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
 * Auto-start is always true per constitution (continuous monitoring).
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
  
  // ========================================================================
  // Form Initialization
  // ========================================================================
  
  const form = useForm<StreamFormData>({
    resolver: zodResolver(streamFormSchema),
    defaultValues: {
      name: initialValues?.name ?? '',
      rtsp_url: initialValues?.rtsp_url ?? '',
      hw_accel_enabled: initialValues?.hw_accel_enabled ?? true,
      ffmpeg_params: initialValues?.ffmpeg_params?.join(' ') ?? '',
    },
    mode: 'onBlur', // Validate on blur for better UX
  })
  
  // ========================================================================
  // GPU Backend Detection
  // ========================================================================
  
  /**
   * Fetch GPU backend on mount to determine default FFmpeg parameters.
   * 
   * Calls /api/streams/gpu-backend which returns GPU_BACKEND_DETECTED
   * env var set by entrypoint.sh during container startup.
   * 
   * Constitution Principle III: Explicit GPU backend contract.
   */
  useEffect(() => {
    let mounted = true
    
    const fetchGpuBackend = async () => {
      try {
        const data = await getGpuBackend()
        
        if (!mounted) return
        
        setGpuBackend(data.gpu_backend || 'none')
        
        // Log GPU status for debugging
        if (data.gpu_backend === 'none') {
          console.warn('No GPU detected - hardware acceleration unavailable')
        } else {
          console.info(`GPU backend detected: ${data.gpu_backend}`)
        }
        
      } catch (err) {
        console.error('Failed to fetch GPU backend:', err)
        if (mounted) {
          setGpuBackend('none')
        }
      } finally {
        if (mounted) {
          setIsLoadingGpu(false)
        }
      }
    }
    
    fetchGpuBackend()
    
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
  
  // Generate placeholder text based on detected GPU backend
  const ffmpegPlaceholder = isLoadingGpu 
    ? 'Loading GPU backend...'
    : buildDefaultFFmpegParams(gpuBackend)
  
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
            : 'Configure a new RTSP stream (5fps, full resolution, auto-start enabled)'}
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
                    Complete RTSP URL including credentials. Stream processes at 5fps automatically.
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
                      Use GPU for stream decoding ({gpuBackend !== 'none' ? `${gpuBackend} detected` : 'no GPU detected'})
                    </FormDescription>
                  </div>
                  <FormControl>
                    <Switch
                      checked={field.value}
                      onCheckedChange={field.onChange}
                      disabled={isLoading || gpuBackend === 'none'}
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
                    {isEdit && ' Note: Changing params requires stopping and restarting the stream.'}
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />
            
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
