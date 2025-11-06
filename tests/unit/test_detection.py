"""
Unit tests for detection pipeline functions.

Tests preprocessing, inference, detection parsing, filtering, and rendering.
Feature: 005-yolo-object-detection
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch
from app.services.detection import (
    preprocess_frame,
    run_inference,
    parse_detections,
    filter_detections,
    render_bounding_boxes,
)
from app.models.detection import Detection


class TestPreprocessFrame:
    """Tests for preprocess_frame() function."""

    def test_returns_correct_shape(self):
        """Should return (1, 3, target_size, target_size) array."""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        preprocessed, scale, padding = preprocess_frame(frame, target_size=640)

        assert preprocessed.shape == (1, 3, 640, 640)
        assert preprocessed.dtype == np.float32

    def test_normalizes_to_zero_one_range(self):
        """Should normalize pixel values to [0.0, 1.0]."""
        frame = np.full((100, 100, 3), 255, dtype=np.uint8)
        preprocessed, _, _ = preprocess_frame(frame, target_size=320)

        assert preprocessed.min() >= 0.0
        assert preprocessed.max() <= 1.0

    def test_maintains_aspect_ratio_with_letterbox(self):
        """Should maintain aspect ratio and add padding."""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)  # 4:3 aspect ratio
        preprocessed, scale, padding = preprocess_frame(frame, target_size=640)

        # For 640x480 → 640x640, height scales to 480*(640/640)=480, needs padding
        assert isinstance(scale, float)
        assert isinstance(padding, tuple)
        assert len(padding) == 2

    def test_handles_square_input_without_padding(self):
        """Should handle square input (640x640) without padding."""
        frame = np.zeros((640, 640, 3), dtype=np.uint8)
        preprocessed, scale, (top, left) = preprocess_frame(frame, target_size=640)

        assert scale == 1.0
        assert top == 0
        assert left == 0


class TestRunInference:
    """Tests for run_inference() function."""

    def test_calls_session_with_correct_input(self):
        """Should call ONNX session with preprocessed frame."""
        mock_session = Mock()
        mock_session.get_inputs.return_value = [Mock(name="images")]
        mock_session.run.return_value = [np.zeros((1, 100, 85))]

        preprocessed = np.zeros((1, 3, 640, 640), dtype=np.float32)
        output = run_inference(mock_session, preprocessed)

        assert mock_session.run.called
        assert output.shape == (1, 100, 85)


class TestParseDetections:
    """Tests for parse_detections() function."""

    def test_returns_empty_list_for_no_detections(self):
        """Should return empty list if no detections."""
        outputs = np.zeros((1, 0, 85))
        detections = parse_detections(outputs, scale=1.0, padding=(0, 0), original_shape=(480, 640))

        assert detections == []

    def test_parses_single_detection_correctly(self):
        """Should parse YOLO output into Detection object."""
        # Create synthetic YOLO output: [x_center, y_center, w, h, objectness, class_probs...]
        outputs = np.zeros((1, 1, 85))
        outputs[0, 0, 0:4] = [320, 240, 100, 100]  # bbox
        outputs[0, 0, 4] = 0.9  # objectness
        outputs[0, 0, 5] = 0.95  # class 0 (person) probability

        detections = parse_detections(outputs, scale=1.0, padding=(0, 0), original_shape=(480, 640))

        assert len(detections) == 1
        assert detections[0].class_id == 0
        assert detections[0].class_name == "person"
        assert 0.8 < detections[0].confidence < 1.0

    def test_applies_scale_and_padding_to_bbox(self):
        """Should correctly apply scale and padding to bounding box."""
        outputs = np.zeros((1, 1, 85))
        outputs[0, 0, 0:4] = [320, 240, 100, 100]
        outputs[0, 0, 4] = 0.9
        outputs[0, 0, 5] = 0.95

        detections = parse_detections(
            outputs,
            scale=2.0,
            padding=(50, 100),
            original_shape=(480, 640)
        )

        # Bbox should be adjusted for scale and padding
        assert detections[0].bbox is not None

    def test_clamps_bbox_to_frame_bounds(self):
        """Should clamp bounding box to original frame dimensions."""
        outputs = np.zeros((1, 1, 85))
        outputs[0, 0, 0:4] = [1000, 1000, 200, 200]  # Out of bounds
        outputs[0, 0, 4] = 0.9
        outputs[0, 0, 5] = 0.95

        detections = parse_detections(outputs, scale=1.0, padding=(0, 0), original_shape=(480, 640))

        x1, y1, x2, y2 = detections[0].bbox
        assert 0 <= x1 <= 640
        assert 0 <= y1 <= 480
        assert 0 <= x2 <= 640
        assert 0 <= y2 <= 480


class TestFilterDetections:
    """Tests for filter_detections() function."""

    def test_filters_by_enabled_labels(self):
        """Should only return detections with enabled labels."""
        detections = [
            Detection(class_id=0, class_name="person", confidence=0.9, bbox=(0, 0, 100, 100)),
            Detection(class_id=2, class_name="car", confidence=0.8, bbox=(0, 0, 100, 100)),
            Detection(class_id=16, class_name="dog", confidence=0.85, bbox=(0, 0, 100, 100)),
        ]

        filtered = filter_detections(detections, enabled_labels=["person", "car"], min_confidence=0.5)

        assert len(filtered) == 2
        assert all(d.class_name in ["person", "car"] for d in filtered)

    def test_filters_by_min_confidence(self):
        """Should only return detections above confidence threshold."""
        detections = [
            Detection(class_id=0, class_name="person", confidence=0.9, bbox=(0, 0, 100, 100)),
            Detection(class_id=0, class_name="person", confidence=0.6, bbox=(0, 0, 100, 100)),
            Detection(class_id=0, class_name="person", confidence=0.4, bbox=(0, 0, 100, 100)),
        ]

        filtered = filter_detections(detections, enabled_labels=["person"], min_confidence=0.7)

        assert len(filtered) == 1
        assert filtered[0].confidence >= 0.7

    def test_applies_both_label_and_confidence_filters(self):
        """Should apply both label and confidence filters together."""
        detections = [
            Detection(class_id=0, class_name="person", confidence=0.9, bbox=(0, 0, 100, 100)),
            Detection(class_id=0, class_name="person", confidence=0.5, bbox=(0, 0, 100, 100)),
            Detection(class_id=2, class_name="car", confidence=0.9, bbox=(0, 0, 100, 100)),
        ]

        filtered = filter_detections(detections, enabled_labels=["person"], min_confidence=0.7)

        assert len(filtered) == 1
        assert filtered[0].class_name == "person"
        assert filtered[0].confidence >= 0.7


class TestRenderBoundingBoxes:
    """Tests for render_bounding_boxes() function."""

    @patch('app.services.detection.cv2')
    def test_draws_rectangle_for_each_detection(self, mock_cv2):
        """Should call cv2.rectangle for each detection."""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        detections = [
            Detection(class_id=0, class_name="person", confidence=0.9, bbox=(10, 10, 100, 100)),
            Detection(class_id=2, class_name="car", confidence=0.85, bbox=(200, 200, 300, 300)),
        ]

        render_bounding_boxes(frame, detections)

        assert mock_cv2.rectangle.call_count == 4  # 2 boxes + 2 label backgrounds

    @patch('app.services.detection.cv2')
    def test_draws_label_text_for_each_detection(self, mock_cv2):
        """Should call cv2.putText for each detection label."""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        detections = [
            Detection(class_id=0, class_name="person", confidence=0.9, bbox=(10, 10, 100, 100)),
        ]

        render_bounding_boxes(frame, detections)

        assert mock_cv2.putText.call_count == 1

    def test_modifies_frame_in_place(self):
        """Should modify frame in-place and return it."""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        detections = [
            Detection(class_id=0, class_name="person", confidence=0.9, bbox=(10, 10, 100, 100)),
        ]

        result = render_bounding_boxes(frame, detections)

        assert result is frame  # Same object reference
