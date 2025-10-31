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
from app.models.detection import Detection, COCO_CLASSES


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
    h, w = frame_bgr.shape[:2]
    scale = min(target_size / h, target_size / w)
    new_h, new_w = int(h * scale), int(w * scale)

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

    return batch, scale, (top, left)


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
    input_name = session.get_inputs()[0].name
    outputs = session.run(None, {input_name: preprocessed_frame})
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
    detections = []
    top, left = padding
    orig_h, orig_w = original_shape

    # YOLO11 output format: (batch, 84, num_detections)
    # 84 = [x_center, y_center, width, height, class_0_prob, ..., class_79_prob]
    # Note: YOLO11 removed the objectness score - only class probabilities remain

    # Remove batch dimension if present
    if len(outputs.shape) == 3:
        outputs = outputs[0]  # Shape becomes (84, num_detections)

    # Transpose to (num_detections, 84) for easier iteration
    outputs = outputs.T

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

    return detections


def filter_detections(
    detections: List[Detection],
    enabled_labels: List[str],
    min_confidence: float
) -> List[Detection]:
    """
    Filter detections by label and confidence threshold.

    Args:
        detections: List of Detection objects
        enabled_labels: List of allowed COCO class names
        min_confidence: Minimum confidence threshold (0.0-1.0)

    Returns:
        Filtered list of Detection objects
    """
    return [
        det for det in detections
        if det.class_name in enabled_labels and det.confidence >= min_confidence
    ]


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
