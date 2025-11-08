"""
YOLO detection pipeline: preprocessing, inference, parsing, and rendering.

This module handles:
- Frame preprocessing (letterbox resize, normalize, transpose)
- YOLO inference via ONNX Runtime
- Detection parsing and filtering
- Bounding box rendering with OpenCV

Feature: 005-yolo-object-detection
"""

import numpy as np
import cv2
from typing import List, Tuple
import onnxruntime as ort
import logging
from app.models.detection import Detection, COCO_CLASSES

logger = logging.getLogger(__name__)


# Pre-generated class colors (80 COCO classes, fixed seed for consistency)
np.random.seed(42)
CLASS_COLORS = np.random.randint(0, 255, size=(80, 3), dtype=np.uint8)


def preprocess_frame(
    frame_bgr: np.ndarray,
    target_size: int = 640
) -> Tuple[np.ndarray, float, Tuple[int, int]]:
    """
    Preprocess frame for YOLO inference.

    Steps:
    1. Letterbox resize (maintain aspect ratio, pad to square)
    2. BGR→RGB conversion
    3. Normalize to [0.0, 1.0]
    4. Transpose HWC→CHW
    5. Add batch dimension (NCHW)

    Args:
        frame_bgr: Input frame in BGR format (OpenCV native)
        target_size: Target square size for YOLO input

    Returns:
        Tuple of (preprocessed_array, scale_factor, padding)
        - preprocessed_array: shape (1, 3, target_size, target_size), dtype float32
        - scale_factor: Resize scale applied
        - padding: (top, left) padding in pixels
    """
    logger.debug(f"Preprocessing frame: input_shape={frame_bgr.shape}, target_size={target_size}")
    h, w = frame_bgr.shape[:2]
    scale = min(target_size / h, target_size / w)
    new_h, new_w = int(h * scale), int(w * scale)
    logger.debug(f"Resize params: original=({w}x{h}), scaled=({new_w}x{new_h}), scale={scale:.3f}")

    # Letterbox resize
    resized = cv2.resize(frame_bgr, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

    # Create padded canvas (114 is YOLO standard padding value)
    canvas = np.full((target_size, target_size, 3), 114, dtype=np.uint8)
    top = (target_size - new_h) // 2
    left = (target_size - new_w) // 2
    canvas[top:top+new_h, left:left+new_w] = resized

    # BGR→RGB, transpose HWC→CHW, normalize, add batch dimension
    rgb = canvas[:, :, ::-1]
    chw = rgb.transpose((2, 0, 1))
    normalized = chw.astype(np.float32) / 255.0
    batch = np.expand_dims(normalized, axis=0)

    logger.debug(f"Preprocessing complete: output_shape={batch.shape}, padding=({top},{left})")
    return batch, scale, (top, left)


def preprocess_region(
    frame_bgr: np.ndarray,
    region_bbox: Tuple[int, int, int, int],
    target_size: int = 640
) -> Tuple[np.ndarray, float, Tuple[int, int], Tuple[int, int]]:
    """
    Preprocess a cropped region for YOLO inference.

    Steps:
    1. Crop region from full frame (already padded in MotionDetector)
    2. Apply letterbox resize to target_size
    3. BGR→RGB conversion
    4. Normalize to [0.0, 1.0]
    5. Transpose HWC→CHW
    6. Add batch dimension (NCHW)

    Args:
        frame_bgr: Full frame in BGR format (OpenCV native)
        region_bbox: Region bounding box (x, y, width, height) in frame coordinates
        target_size: Target square size for YOLO input

    Returns:
        Tuple of (preprocessed_array, scale_factor, padding, region_offset)
        - preprocessed_array: shape (1, 3, target_size, target_size), dtype float32
        - scale_factor: Resize scale applied to region
        - padding: (top, left) padding added during letterbox
        - region_offset: (x, y) offset of region in original frame
    """
    x, y, w, h = region_bbox
    logger.debug(f"Preprocessing region: bbox=({x},{y},{w},{h}), target_size={target_size}")

    # Step 1: Crop region from frame
    region = frame_bgr[y:y+h, x:x+w]
    if region.size == 0:
        logger.warning(f"Empty region after crop: bbox=({x},{y},{w},{h}), frame_shape={frame_bgr.shape}")
        # Return empty batch as fallback
        empty_batch = np.zeros((1, 3, target_size, target_size), dtype=np.float32)
        return empty_batch, 1.0, (0, 0), (x, y)

    # Step 2-6: Apply same preprocessing as full frame
    region_h, region_w = region.shape[:2]
    scale = min(target_size / region_h, target_size / region_w)
    new_h, new_w = int(region_h * scale), int(region_w * scale)

    # Letterbox resize
    resized = cv2.resize(region, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

    # Create padded canvas
    canvas = np.full((target_size, target_size, 3), 114, dtype=np.uint8)
    top = (target_size - new_h) // 2
    left = (target_size - new_w) // 2
    canvas[top:top+new_h, left:left+new_w] = resized

    # BGR→RGB, transpose HWC→CHW, normalize, add batch dimension
    rgb = canvas[:, :, ::-1]
    chw = rgb.transpose((2, 0, 1))
    normalized = chw.astype(np.float32) / 255.0
    batch = np.expand_dims(normalized, axis=0)

    logger.debug(
        f"Region preprocessing complete: region_shape=({region_w}x{region_h}), "
        f"scale={scale:.3f}, padding=({top},{left}), offset=({x},{y})"
    )
    return batch, scale, (top, left), (x, y)


def map_detections_to_frame(
    detections: List[Detection],
    scale: float,
    padding: Tuple[int, int],
    region_offset: Tuple[int, int],
    frame_shape: Tuple[int, int]
) -> List[Detection]:
    """
    Map detection coordinates from region space to full frame space.

    Steps:
    1. Inverse letterbox transform (remove padding and scale)
    2. Add region offset to coordinates
    3. Clamp to frame boundaries per FR-023

    Args:
        detections: List of Detection objects in region coordinates
        scale: Scale factor from preprocess_region()
        padding: (top, left) padding from preprocess_region()
        region_offset: (x, y) offset of region in original frame
        frame_shape: (height, width) of full frame for boundary checking

    Returns:
        List of Detection objects with coordinates in full frame space
    """
    if not detections:
        return []

    top, left = padding
    offset_x, offset_y = region_offset
    frame_height, frame_width = frame_shape

    logger.debug(
        f"Mapping {len(detections)} detections: scale={scale:.3f}, "
        f"padding=({top},{left}), offset=({offset_x},{offset_y})"
    )

    mapped_detections = []
    for det in detections:
        x1, y1, x2, y2 = det.bbox

        # Step 1: Inverse letterbox transform
        # Convert from model space to region space
        x1_region = int((x1 - left) / scale)
        y1_region = int((y1 - top) / scale)
        x2_region = int((x2 - left) / scale)
        y2_region = int((y2 - top) / scale)

        # Step 2: Add region offset to get full frame coordinates
        x1_frame = x1_region + offset_x
        y1_frame = y1_region + offset_y
        x2_frame = x2_region + offset_x
        y2_frame = y2_region + offset_y

        # Step 3: Clamp to frame boundaries per FR-023
        x1_frame = max(0, min(x1_frame, frame_width))
        y1_frame = max(0, min(y1_frame, frame_height))
        x2_frame = max(0, min(x2_frame, frame_width))
        y2_frame = max(0, min(y2_frame, frame_height))

        # Skip invalid boxes after clamping
        if x2_frame <= x1_frame or y2_frame <= y1_frame:
            logger.debug(f"Skipping invalid box after mapping: ({x1_frame},{y1_frame},{x2_frame},{y2_frame})")
            continue

        # Create new Detection with mapped coordinates
        mapped_detections.append(Detection(
            class_id=det.class_id,
            class_name=det.class_name,
            confidence=det.confidence,
            bbox=(x1_frame, y1_frame, x2_frame, y2_frame)
        ))

    logger.info(f"Mapped {len(mapped_detections)} detections to full frame coordinates")
    return mapped_detections


def run_inference(
    session: ort.InferenceSession,
    preprocessed_frame: np.ndarray
) -> np.ndarray:
    """
    Run YOLO inference via ONNX Runtime.

    Args:
        session: ONNX Runtime inference session
        preprocessed_frame: Preprocessed frame from preprocess_frame()

    Returns:
        Raw YOLO output array (detections before NMS)
    """
    import time
    input_name = session.get_inputs()[0].name
    logger.debug(f"Running YOLO inference: input_name={input_name}, input_shape={preprocessed_frame.shape}")

    start_time = time.perf_counter()
    outputs = session.run(None, {input_name: preprocessed_frame})
    inference_time_ms = (time.perf_counter() - start_time) * 1000

    logger.info(f"YOLO inference complete: time={inference_time_ms:.1f}ms, output_shape={outputs[0].shape}")
    return outputs[0]


def parse_detections(
    outputs: np.ndarray,
    scale: float,
    padding: Tuple[int, int],
    original_shape: Tuple[int, int]
) -> List[Detection]:
    """
    Parse YOLO output into Detection objects.

    Args:
        outputs: Raw YOLO output from run_inference()
        scale: Scale factor from preprocess_frame()
        padding: (top, left) padding from preprocess_frame()
        original_shape: (height, width) of original frame

    Returns:
        List of Detection objects with bounding boxes in original frame coordinates
    """
    logger.debug(f"Parsing detections: output_shape={outputs.shape}, scale={scale:.3f}, padding={padding}, original_shape={original_shape}")
    detections = []
    top, left = padding
    orig_h, orig_w = original_shape

    # YOLO11 output format: (batch, 84, num_detections)
    # 84 = [x_center, y_center, width, height, class_0_prob, ..., class_79_prob]
    # Note: YOLO11 removed the objectness score - only class probabilities remain

    # Remove batch dimension if present
    if len(outputs.shape) == 3:
        outputs = outputs[0]  # Shape becomes (84, num_detections)
        logger.debug(f"Removed batch dimension: new_shape={outputs.shape}")

    # Transpose to (num_detections, 84) for easier iteration
    outputs = outputs.T
    logger.debug(f"Transposed to (num_detections, 84): shape={outputs.shape}")

    for detection in outputs:
        if len(detection) < 84:
            continue

        # Extract coordinates (first 4 values)
        x_center, y_center, width, height = detection[:4]

        # Extract class probabilities (remaining 80 values)
        class_probs = detection[4:]

        # Get class with highest probability
        class_id = int(np.argmax(class_probs))
        confidence = float(class_probs[class_id])

        # Filter low-confidence detections early (before coordinate conversion)
        if confidence < 0.01:  # Skip very low confidence detections
            continue

        # Convert to bounding box coordinates (x1, y1, x2, y2)
        # Remove padding and scale back to original size
        x1 = int((x_center - width / 2 - left) / scale)
        y1 = int((y_center - height / 2 - top) / scale)
        x2 = int((x_center + width / 2 - left) / scale)
        y2 = int((y_center + height / 2 - top) / scale)

        # Skip detections at edge boundaries before clamping (B7 optimization)
        # These create invalid boxes after mapping to full frame in region-based detection
        if x1 >= orig_w or x2 >= orig_w or y1 >= orig_h or y2 >= orig_h or x1 < 0 or y1 < 0:
            continue

        # Clamp to original frame bounds
        x1 = max(0, min(x1, orig_w))
        y1 = max(0, min(y1, orig_h))
        x2 = max(0, min(x2, orig_w))
        y2 = max(0, min(y2, orig_h))

        # Skip invalid boxes
        if x2 <= x1 or y2 <= y1:
            continue

        detections.append(Detection(
            class_id=class_id,
            class_name=COCO_CLASSES[class_id],
            confidence=confidence,
            bbox=(x1, y1, x2, y2)
        ))

    logger.info(f"Parsed {len(detections)} raw detections from {outputs.shape[0]} candidates")
    return detections


def calculate_iou(box1: Tuple[int, int, int, int], box2: Tuple[int, int, int, int]) -> float:
    """
    Calculate Intersection over Union (IoU) between two bounding boxes.

    Args:
        box1: First bounding box (x1, y1, x2, y2)
        box2: Second bounding box (x1, y1, x2, y2)

    Returns:
        IoU value between 0.0 and 1.0
    """
    x1_1, y1_1, x2_1, y2_1 = box1
    x1_2, y1_2, x2_2, y2_2 = box2

    # Calculate intersection area
    x1_inter = max(x1_1, x1_2)
    y1_inter = max(y1_1, y1_2)
    x2_inter = min(x2_1, x2_2)
    y2_inter = min(y2_1, y2_2)

    # Check if boxes intersect
    if x2_inter <= x1_inter or y2_inter <= y1_inter:
        return 0.0

    intersection = (x2_inter - x1_inter) * (y2_inter - y1_inter)

    # Calculate union area
    area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
    area2 = (x2_2 - x1_2) * (y2_2 - y1_2)
    union = area1 + area2 - intersection

    # Avoid division by zero
    if union == 0:
        return 0.0

    return intersection / union


def apply_nms(
    detections: List[Detection],
    iou_threshold: float = 0.5
) -> List[Detection]:
    """
    Apply Non-Maximum Suppression to remove duplicate/overlapping detections.

    NMS Algorithm:
    1. Sort detections by confidence (descending)
    2. For each detection, suppress all lower-confidence detections
       that overlap with it (IoU > threshold)
    3. Process separately for each class to preserve multi-class detections

    Args:
        detections: List of Detection objects
        iou_threshold: IoU threshold for suppression (default: 0.5)

    Returns:
        Filtered list of Detection objects with duplicates removed
    """
    if not detections:
        return []

    # Group detections by class to apply NMS separately per class
    detections_by_class: dict[str, List[Detection]] = {}
    for det in detections:
        if det.class_name not in detections_by_class:
            detections_by_class[det.class_name] = []
        detections_by_class[det.class_name].append(det)

    kept_detections = []
    suppressed_count = 0

    # Apply NMS for each class independently
    for class_name, class_dets in detections_by_class.items():
        # Sort by confidence (descending)
        class_dets_sorted = sorted(class_dets, key=lambda d: d.confidence, reverse=True)

        # Track which detections to keep
        keep_flags = [True] * len(class_dets_sorted)

        for i in range(len(class_dets_sorted)):
            if not keep_flags[i]:
                continue

            # Compare with all subsequent detections
            for j in range(i + 1, len(class_dets_sorted)):
                if not keep_flags[j]:
                    continue

                # Calculate IoU between boxes
                iou = calculate_iou(class_dets_sorted[i].bbox, class_dets_sorted[j].bbox)

                # Suppress lower confidence detection if IoU exceeds threshold
                if iou > iou_threshold:
                    keep_flags[j] = False
                    suppressed_count += 1

        # Keep only non-suppressed detections
        for i, det in enumerate(class_dets_sorted):
            if keep_flags[i]:
                kept_detections.append(det)

    if suppressed_count > 0:
        logger.info(f"NMS suppressed {suppressed_count} duplicate detections (IoU threshold: {iou_threshold})")

    return kept_detections


def filter_detections(
    detections: List[Detection],
    enabled_labels: List[str],
    min_confidence: float,
    apply_nms_filter: bool = True,
    nms_iou_threshold: float = 0.5
) -> List[Detection]:
    """
    Filter detections by label, confidence threshold, and NMS.

    Args:
        detections: List of Detection objects
        enabled_labels: List of allowed COCO class names
        min_confidence: Minimum confidence threshold (0.0-1.0)
        apply_nms_filter: Whether to apply NMS (default: True)
        nms_iou_threshold: IoU threshold for NMS (default: 0.5)

    Returns:
        Filtered list of Detection objects
    """
    logger.debug(f"Filtering detections: input_count={len(detections)}, enabled_labels={enabled_labels}, min_confidence={min_confidence}")

    # Step 1: Filter by label and confidence
    filtered = [
        det for det in detections
        if det.class_name in enabled_labels and det.confidence >= min_confidence
    ]

    # Step 2: Apply NMS to remove duplicates
    if apply_nms_filter and filtered:
        pre_nms_count = len(filtered)
        filtered = apply_nms(filtered, nms_iou_threshold)
        logger.debug(f"NMS: {pre_nms_count} detections → {len(filtered)} detections")

    if filtered:
        class_counts = {}
        for det in filtered:
            class_counts[det.class_name] = class_counts.get(det.class_name, 0) + 1
        logger.info(f"Filtered to {len(filtered)} detections: {class_counts}")
    else:
        logger.debug("No detections after filtering")

    return filtered


def render_bounding_boxes(
    frame: np.ndarray,
    detections: List[Detection]
) -> np.ndarray:
    """
    Render bounding boxes with labels on frame.

    Args:
        frame: Frame in BGR format (modified in-place)
        detections: List of Detection objects to render

    Returns:
        Frame with rendered bounding boxes (same as input, modified in-place)
    """
    logger.debug(f"Rendering {len(detections)} bounding boxes on frame")
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.6
    font_thickness = 2
    box_thickness = 2

    for detection in detections:
        x1, y1, x2, y2 = detection.bbox
        class_id = detection.class_id
        confidence = detection.confidence
        class_name = detection.class_name

        # Get color for this class
        color = tuple([int(c) for c in CLASS_COLORS[class_id]])

        # Draw bounding box
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, box_thickness)

        # Create label: "person 0.87"
        label = f"{class_name} {confidence:.2f}"
        (text_w, text_h), baseline = cv2.getTextSize(
            label, font, font_scale, font_thickness
        )

        # Draw filled background for text (above box if space, below if not)
        label_y = y1 - 10 if y1 - 10 > text_h else y1 + text_h + 10
        cv2.rectangle(
            frame,
            (x1, label_y - text_h - baseline),
            (x1 + text_w, label_y + baseline),
            color,
            -1  # Filled
        )

        # Draw white text on colored background
        cv2.putText(
            frame,
            label,
            (x1, label_y),
            font,
            font_scale,
            (255, 255, 255),
            font_thickness,
            cv2.LINE_AA
        )

    return frame


def render_motion_boxes(
    frame: np.ndarray,
    motion_regions: List
) -> np.ndarray:
    """
    Render motion region bounding boxes on frame.

    Args:
        frame: Frame in BGR format (modified in-place)
        motion_regions: List of MotionRegion objects to render

    Returns:
        Frame with rendered motion boxes (same as input, modified in-place)
    """
    logger.debug(f"Rendering {len(motion_regions)} motion boxes on frame")

    for region in motion_regions:
        x, y, w, h = region.bounding_box
        # Red color, thin line (1px) for motion regions (FR-025)
        cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 0, 255), 1)

    return frame


def render_tracking_boxes(
    frame: np.ndarray,
    tracked_objects: List
) -> np.ndarray:
    """
    Render tracked object bounding boxes with IDs and states.

    Args:
        frame: Frame in BGR format (modified in-place)
        tracked_objects: List of TrackedObject instances to render

    Returns:
        Frame with rendered tracking boxes (same as input, modified in-place)
    """
    logger.debug(f"Rendering {len(tracked_objects)} tracking boxes on frame")
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.5
    font_thickness = 1
    box_thickness = 2

    for obj in tracked_objects:
        x, y, w, h = obj.bounding_box

        # Color based on state (FR-026, FR-027)
        if obj.state.value == "stationary":
            color = (0, 255, 255)  # Yellow for stationary objects
        elif obj.state.value == "active":
            color = (0, 255, 0)  # Green for active tracking
        elif obj.state.value == "tentative":
            color = (255, 165, 0)  # Orange for tentative tracks
        else:  # lost
            color = (128, 128, 128)  # Gray for lost tracks

        # Draw bounding box
        cv2.rectangle(frame, (x, y), (x+w, y+h), color, box_thickness)

        # Create label: "{id_short} {class} ({state})"
        id_short = str(obj.id).split('-')[0][:8]  # First 8 chars of UUID
        label = f"{id_short} {obj.class_name} ({obj.state.value})"

        # Draw label background
        (text_w, text_h), baseline = cv2.getTextSize(
            label, font, font_scale, font_thickness
        )

        # Position label above box if space, below if not
        label_y = y - 5 if y - 5 > text_h else y + h + text_h + 5

        cv2.rectangle(
            frame,
            (x, label_y - text_h - baseline),
            (x + text_w, label_y + baseline),
            color,
            -1  # Filled
        )

        # Draw white text on colored background
        cv2.putText(
            frame,
            label,
            (x, label_y),
            font,
            font_scale,
            (255, 255, 255),
            font_thickness,
            cv2.LINE_AA
        )

    return frame
