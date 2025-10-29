# Feature Specification: YOLO Object Detection with Bounding Boxes

**Feature Branch**: `005-yolo-object-detection`
**Created**: 2025-10-29
**Status**: Draft
**Input**: User description: "I want to add yolo-onnx object detection to the ffmpeg>mjpeg pipline. I want a docker env var to set which yolo model, and the img detect size. ie yolo11n 320, yolo9t 320. etc. then in the ui of the camera stream, the user can set what labels to look for, and set a min confidence value in order to put a bounding box over the object."

## Clarifications

### Session 2025-10-29

- Q: YOLO Model Distribution Strategy - How should models be provided to the container? → A: Auto-download specified model on first startup from Ultralytics/GitHub (smaller image, requires internet on first run, cache locally)
- Q: Default Label Selection Behavior - Which COCO labels should be enabled by default for new streams? → A: Only "person" label enabled by default
- Q: Default Confidence Threshold Value - What should the default minimum confidence threshold be for new streams? → A: 0.7 (70%)
- Q: Model Cache Persistence Location - Where should downloaded YOLO models be cached? → A: Separate dedicated volume for models at /app/models with UI for model management (delete/rebuild capabilities)
- Q: Inference Performance Degradation Handling - How should the system handle inference that takes longer than the frame budget? → A: Skip frame and continue (maintain ≤5 FPS, some detections may be missed during slowdowns)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Configure YOLO Model at Container Startup (Priority: P1)

A user deploying ProxiMeter wants to choose which YOLO model to use for object detection based on their hardware capabilities and accuracy requirements. They set environment variables before starting the container to specify the model and detection image size.

**Why this priority**: This is foundational - the container must load and initialize the correct YOLO model before any detection can occur. Without this, no other object detection features can function.

**Independent Test**: Can be fully tested by setting environment variables (e.g., `YOLO_MODEL=yolo11n`, `YOLO_IMAGE_SIZE=320`) and verifying the container starts successfully, loads the specified model, and logs model initialization details. Delivers a working object detection pipeline ready to process frames.

**Acceptance Scenarios**:

1. **Given** the container is not running, **When** a user sets `YOLO_MODEL=yolo11n` and `YOLO_IMAGE_SIZE=320` and starts the container, **Then** the container loads the YOLO11n model with 320x320 input size and logs successful model initialization
2. **Given** the container is not running, **When** a user sets `YOLO_MODEL=yolo9t` and `YOLO_IMAGE_SIZE=640` and starts the container, **Then** the container loads the YOLO9t model with 640x640 input size
3. **Given** no environment variables are set, **When** the container starts, **Then** the container loads a default model (yolo11n at 320x320) and logs this as the default configuration
4. **Given** an invalid model name is provided, **When** the container starts, **Then** the container logs an error and fails to start with a clear error message indicating valid model options
5. **Given** an invalid image size is provided (non-numeric or outside 320-1280 range), **When** the container starts, **Then** the container logs an error and fails to start with a clear error message

---

### User Story 2 - Filter Detected Objects by Label (Priority: P2)

A user viewing a camera stream wants to see only specific types of objects (e.g., only "person", "car", and "dog") to reduce visual clutter and focus on relevant detections. They configure which COCO labels to display through the UI.

**Why this priority**: This provides immediate value by letting users customize what they see without restarting the container. It's independent of confidence thresholds and can be tested by selecting different label combinations.

**Independent Test**: Can be fully tested by configuring a stream with specific labels selected (e.g., "person", "car"), sending test frames with various objects, and verifying only bounding boxes for selected labels appear. Delivers customizable object filtering per stream.

**Acceptance Scenarios**:

1. **Given** a new stream is created, **When** the user views the stream without changing label configuration, **Then** only "person" detections appear with bounding boxes (default behavior)
2. **Given** a stream is configured with labels "person" and "car" selected, **When** the detection system processes a frame containing a person, car, and dog, **Then** bounding boxes appear only for the person and car
3. **Given** a stream is configured with no labels selected, **When** the detection system processes a frame, **Then** no bounding boxes appear (all objects are filtered out)
4. **Given** a stream is configured with all available COCO labels selected, **When** the detection system processes a frame, **Then** bounding boxes appear for all detected objects regardless of class
5. **Given** a user is viewing the stream configuration UI, **When** they view the label selector, **Then** they see a list of all COCO class labels (80 classes) with checkboxes for multi-select, with "person" pre-selected by default
6. **Given** a user has selected specific labels, **When** they save the configuration, **Then** the selection persists and is applied immediately to the live stream without requiring a page refresh

---

### User Story 3 - Set Minimum Confidence Threshold (Priority: P2)

A user wants to reduce false positive detections by setting a minimum confidence threshold (e.g., 0.5 or 50%) so that only high-confidence detections show bounding boxes. They adjust a slider or input field in the UI per stream.

**Why this priority**: This complements label filtering and provides additional control over detection quality. It's independently testable and delivers immediate value by reducing false positives.

**Independent Test**: Can be fully tested by setting different confidence thresholds (e.g., 0.3, 0.5, 0.8) and verifying that only detections meeting the threshold display bounding boxes. Delivers quality control for object detection.

**Acceptance Scenarios**:

1. **Given** a new stream is created, **When** the user views the stream without changing confidence configuration, **Then** only detections with confidence ≥0.7 appear with bounding boxes (default behavior)
2. **Given** a stream is configured with a confidence threshold of 0.5, **When** the detection system finds objects with confidences of 0.6, 0.4, and 0.8, **Then** bounding boxes appear only for the 0.6 and 0.8 detections
3. **Given** a stream is configured with a confidence threshold of 0.9, **When** the detection system processes typical frames, **Then** only very high-confidence detections appear (reducing false positives)
4. **Given** a user is viewing the stream configuration UI, **When** they view the confidence threshold control, **Then** they see a slider or numeric input with current value displayed (0.0 to 1.0 or 0% to 100%), defaulting to 0.7 for new streams
5. **Given** a user sets a confidence threshold of 0.0, **When** detection runs, **Then** all detected objects appear regardless of confidence (no filtering)
6. **Given** a user sets a confidence threshold of 1.0, **When** detection runs, **Then** effectively no objects appear (only perfect 100% confidence would pass)

---

### User Story 4 - View Bounding Boxes on Live Stream (Priority: P1)

A user viewing a camera stream wants to see bounding boxes drawn around detected objects in real-time, with labels and confidence scores displayed, so they can visually identify what the system is detecting.

**Why this priority**: This is the primary deliverable - the visual feedback that object detection is working. Without this, users cannot see detection results.

**Independent Test**: Can be fully tested by starting a stream, verifying detection runs, and confirming that bounding boxes with labels and confidence scores appear overlaid on the MJPEG stream. Delivers the core user-facing feature.

**Acceptance Scenarios**:

1. **Given** a stream is configured with object detection enabled, **When** a user views the live MJPEG stream and an object is detected, **Then** a bounding box appears around the object with the label and confidence score displayed
2. **Given** multiple objects are detected in a frame, **When** the user views the stream, **Then** multiple bounding boxes appear, each with its own label and confidence score
3. **Given** an object moves across the frame, **When** the user watches the stream, **Then** the bounding box smoothly tracks the object's position across consecutive frames (at ≤5 FPS)
4. **Given** detection confidence is low (below the threshold), **When** the user views the stream, **Then** no bounding box appears for that object
5. **Given** the object detection processing encounters an error, **When** the user views the stream, **Then** the stream continues to display without bounding boxes and an error is logged (graceful degradation)

---

### User Story 5 - Manage Cached YOLO Models (Priority: P3)

A user wants to manage the YOLO models cached on their system to free up disk space, troubleshoot corrupted downloads, or force a fresh download of a model. They access a model management UI to view, delete, and re-download models.

**Why this priority**: This is maintenance/administrative functionality that supports the core detection features. It's not required for basic operation but provides operational control for troubleshooting and disk management.

**Independent Test**: Can be fully tested by downloading multiple models, viewing the list in the UI, deleting a model, and triggering a re-download. Delivers administrative control over cached model files.

**Acceptance Scenarios**:

1. **Given** multiple YOLO models have been downloaded and cached, **When** a user navigates to the model management UI, **Then** they see a list of all cached models with details (name, file size, download date)
2. **Given** a user views the model management UI, **When** they select a cached model and click delete, **Then** the model file is removed from /app/models and the list updates
3. **Given** a cached model has been deleted, **When** the container restarts with that model specified in YOLO_MODEL, **Then** the system re-downloads the model automatically
4. **Given** a user suspects a model file is corrupted, **When** they trigger a re-download/rebuild for that model in the UI, **Then** the system deletes the cached version and downloads a fresh copy
5. **Given** a model download is in progress, **When** the user views the model management UI, **Then** they see download progress indication (percentage or status message)

---

### Edge Cases

- What happens when the YOLO model file is corrupted or missing at container startup?
- How does the system handle frames that fail to decode before reaching the detection pipeline?
- What happens when the user selects an extremely high confidence threshold (e.g., 0.99) resulting in zero detections?
- How does the system handle very large numbers of detections in a single frame (e.g., 100+ objects)?
- What happens when the user changes detection configuration (labels or confidence) while actively viewing a stream?
- How does the system handle non-standard YOLO model formats or versions that are incompatible with the ONNX runtime?
- What happens when GPU acceleration is unavailable and inference is slower than the 5 FPS frame rate?
- What happens when internet connectivity is unavailable on first startup and the model needs to be downloaded?
- What happens when a cached model file becomes corrupted between container restarts?
- What happens when the /app/models volume runs out of disk space during model download?
- What happens when a user deletes the currently active model while the container is running?
- What happens when consecutive frames are skipped due to slow inference - does the user notice detection gaps?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Accept environment variables `YOLO_MODEL` (string, e.g., "yolo11n", "yolo9t") and `YOLO_IMAGE_SIZE` (integer, e.g., 320, 640) at container startup; default to "yolo11n" and 640 if not provided
- **FR-002**: Automatically download the specified YOLO model in ONNX format from Ultralytics/GitHub on first startup if not already cached; cache downloaded models locally to enable offline operation on subsequent starts; fail fast with clear error message if model download fails or model is invalid
- **FR-003**: Support YOLO model variants including: yolo11n, yolo11s, yolo11m, yolo11l, yolo11x, yolo9t, yolo9s, yolo9m, yolo9l (standard COCO-trained models)
- **FR-004**: Support image detection sizes: 320, 416, 512, 640, 1280 pixels (square input); reject invalid sizes at startup with error message
- **FR-005**: Integrate YOLO ONNX inference into the existing FFmpeg→MJPEG pipeline after frame extraction and before MJPEG encoding
- **FR-006**: Run YOLO inference on each frame at the configured frame rate (≤5 FPS as per existing system constraints)
- **FR-007**: Use GPU acceleration (NVIDIA/AMD/Intel) for YOLO inference when available, detected via existing `GPU_BACKEND_DETECTED` mechanism; fall back to CPU if GPU unavailable
- **FR-008**: Parse YOLO output to extract bounding boxes, class labels (COCO dataset), and confidence scores for each detection
- **FR-009**: Provide a stream configuration UI control for selecting which COCO class labels to detect (multi-select from 80 COCO classes); default to "person" label selected for new streams
- **FR-010**: Provide a stream configuration UI control for setting minimum confidence threshold (slider or numeric input, range 0.0 to 1.0); default to 0.7 for new streams
- **FR-011**: Store label selections and confidence threshold per stream in `config.yml` alongside existing stream configuration
- **FR-012**: Filter detections based on user-configured labels and confidence threshold before rendering bounding boxes
- **FR-013**: Draw bounding boxes on video frames using OpenCV or similar library before encoding to MJPEG
- **FR-014**: Display class label and confidence score (e.g., "person 0.87") near each bounding box in a readable font with contrasting background
- **FR-015**: Use distinct colors for bounding boxes of different object classes to improve visual distinction
- **FR-016**: Ensure bounding box rendering does not significantly impact frame rate (target: maintain ≤5 FPS)
- **FR-017**: Log YOLO model initialization details (model name, version, input size, backend) at container startup
- **FR-018**: Log detection performance metrics (inference time per frame, detections per frame) to existing Prometheus metrics endpoint
- **FR-019**: Handle inference errors gracefully: log error, skip bounding boxes for that frame, continue stream without crashing
- **FR-020**: Provide REST API endpoint to retrieve current YOLO model configuration (model name, image size, backend used)
- **FR-021**: Cache downloaded YOLO models in a dedicated persistent volume at /app/models (separate from config volume) to survive container restarts and enable offline operation after first successful download
- **FR-022**: Provide UI for model management including: list cached models, view model details (name, size, download date), delete cached models, trigger model re-download/rebuild
- **FR-023**: When inference takes longer than the frame time budget (200ms at 5 FPS), skip processing that frame and continue with the next frame to maintain target frame rate; log skipped frames as performance metric

### Key Entities *(include if feature involves data)*

- **YOLOConfig**: model_name (string), image_size (int), backend (string: nvidia/amd/intel/cpu), model_path (string)
- **Detection**: class_id (int), class_name (string), confidence (float), bbox (x, y, w, h)
- **StreamDetectionConfig** (extends existing Stream): enabled_labels (list of strings, default: ["person"]), min_confidence (float 0.0-1.0, default: 0.7)
- **DetectionMetrics**: inference_time_ms (float), detections_count (int), frames_processed (int), frames_skipped (int)
- **CachedModel**: model_name (string), file_path (string), file_size_bytes (int), download_date (datetime), is_active (bool)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Container successfully starts and initializes specified YOLO model within 30 seconds of startup for standard models (yolo11n, yolo9t)
- **SC-002**: YOLO inference completes in under 200ms per frame on NVIDIA GPU (T4 or better), 500ms on CPU for 640x640 input size
- **SC-003**: Frame rate maintains ≤5 FPS end-to-end including inference and bounding box rendering (no degradation from baseline)
- **SC-004**: Users can select from all 80 COCO class labels via multi-select UI control with search/filter capability
- **SC-005**: Users can set confidence threshold from 0.0 to 1.0 with 0.01 precision via slider or numeric input
- **SC-006**: Configuration changes (labels, confidence) apply to live stream within 1 second without requiring page refresh or stream restart
- **SC-007**: Bounding boxes appear on detected objects with label and confidence score in readable text (minimum 12px font size)
- **SC-008**: System handles up to 50 simultaneous detections per frame without significant performance degradation (latency <50ms overhead)
- **SC-009**: Detection configuration (labels, confidence) persists in `config.yml` and survives container restarts
- **SC-010**: Inference errors are logged and do not crash the stream; system recovers gracefully by skipping affected frames
- **SC-011**: Model loading supports models up to 1GB in size with appropriate startup timeout adjustments
- **SC-012**: Bounding box colors are visually distinct for at least 10 most common object classes
- **SC-013**: Memory usage increases by no more than 500MB when object detection is enabled (measured over 1-hour runtime)
- **SC-014**: YOLO model configuration endpoint returns model details in under 50ms
- **SC-015**: Model management UI displays all cached models with accurate metadata (name, size, date) and responds to user actions (delete, re-download) within 2 seconds
- **SC-016**: Skipped frame rate remains below 10% during normal operation (90%+ of frames processed successfully); skipped frames are logged to Prometheus metrics
- **SC-017**: New streams created without explicit configuration use default settings (person label, 0.7 confidence) and show detections immediately when objects are present

## Assumptions

- YOLO models are pre-trained on COCO dataset (80 classes) and available in ONNX format from Ultralytics official releases on GitHub
- Internet connectivity is available on first container startup to download the specified YOLO model; subsequent starts work offline using cached models
- Model cache persists across container restarts via dedicated mounted volume at /app/models (separate from config volume)
- Default detection configuration (person label only, 0.7 confidence threshold) is suitable for common home automation use cases (security/presence detection)
- Users deploying with GPU have appropriate drivers installed (as per existing GPU support requirements)
- The existing FFmpeg→OpenCV→MJPEG pipeline provides frames in a format compatible with YOLO inference (RGB/BGR numpy arrays)
- Object detection is desired on all streams; per-stream enable/disable can be added as future enhancement
- Bounding box rendering directly on frames before MJPEG encoding is acceptable (alternative: client-side rendering via separate detection API would require different approach)
- Users are familiar with COCO dataset class names (no need for custom class name mapping)
- Real-time detection at ≤5 FPS is sufficient for home automation use cases (not aiming for 30 FPS real-time tracking)
- Occasional skipped frames during inference slowdowns are acceptable; continuous real-time detection on every frame is not required
- ONNX Runtime is compatible with existing Python 3.12 environment and GPU backends

## Out of Scope

- Custom YOLO model training or fine-tuning
- Non-COCO datasets or custom class labels
- Video recording with baked-in bounding boxes
- Historical detection data storage or playback
- Detection alerts, notifications, or automation triggers (future enhancement)
- Multi-object tracking across frames (object IDs, trajectories)
- Advanced post-processing (Non-Maximum Suppression parameter tuning, tracking algorithms)
- Client-side bounding box rendering (all rendering is server-side on MJPEG frames)
- Model quantization or optimization beyond what ONNX Runtime provides
- Support for non-YOLO models (e.g., SSD, Faster R-CNN)