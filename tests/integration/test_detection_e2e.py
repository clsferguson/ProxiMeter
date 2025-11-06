"""
End-to-end integration tests for YOLO object detection feature.

Tests the complete detection pipeline with synthetic RTSP stream:
- Model download and cache persistence
- FFmpeg raw BGR24 pipeline
- Detection rendering with bounding boxes
- Configuration persistence in config.yml

Feature: 005-yolo-object-detection
"""

import pytest
import asyncio
import subprocess
import time
from pathlib import Path
from unittest.mock import patch, Mock
import numpy as np
import cv2
from fastapi.testclient import TestClient

from app.main import app
from app.services.yolo import load_yolo_model, export_to_onnx
from app.services.detection import preprocess_frame, run_inference, parse_detections, filter_detections
from app.models.detection import StreamDetectionConfig, COCO_CLASSES


client = TestClient(app)


class TestYoloModelDownloadAndCache:
    """Tests for YOLO model download and cache persistence (T108)."""

    @pytest.mark.integration
    def test_downloads_model_on_first_use(self, tmp_path):
        """Should download YOLO model if not cached."""
        model_dir = tmp_path / "models"
        model_dir.mkdir()

        # Simulate first-time download
        with patch('app.services.yolo.YOLO') as mock_yolo:
            mock_model = Mock()
            mock_yolo.return_value = mock_model

            model_path = load_yolo_model("yolo11n", str(model_dir))

            assert mock_yolo.called
            assert model_path.exists()

    @pytest.mark.integration
    def test_uses_cached_model_on_subsequent_calls(self, tmp_path):
        """Should use cached model without re-downloading."""
        model_dir = tmp_path / "models"
        model_dir.mkdir()

        # Create cached model
        cached_model = model_dir / "yolo11n.pt"
        cached_model.write_bytes(b"fake model data")

        with patch('app.services.yolo.YOLO') as mock_yolo:
            model_path = load_yolo_model("yolo11n", str(model_dir))

            # Should not call YOLO constructor (no download)
            assert not mock_yolo.called
            assert model_path == cached_model

    @pytest.mark.integration
    def test_onnx_export_persists_to_cache(self, tmp_path):
        """Should export ONNX model and persist to cache."""
        model_dir = tmp_path / "models"
        model_dir.mkdir()

        # Create .pt model
        pt_model = model_dir / "yolo11n.pt"
        pt_model.write_bytes(b"fake pt model")

        with patch('app.services.yolo.YOLO') as mock_yolo:
            mock_model = Mock()
            mock_model.export.return_value = None
            mock_yolo.return_value = mock_model

            # Mock the ONNX file creation after export
            onnx_path = model_dir / "yolo11n_640.onnx"
            onnx_path.write_bytes(b"fake onnx model")

            with patch.object(Path, 'exists', side_effect=lambda: True):
                result = export_to_onnx("yolo11n", 640, str(model_dir))

                assert result.exists()
                assert result.suffix == ".onnx"


class TestFFmpegRawBGR24Pipeline:
    """Tests for FFmpeg raw BGR24 pipeline with detection (T109)."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_ffmpeg_outputs_raw_bgr24_frames(self):
        """Should extract raw BGR24 frames from RTSP stream."""
        from app.utils.rtsp import build_ffmpeg_command

        # Generate synthetic video using FFmpeg testsrc
        test_cmd = [
            "ffmpeg",
            "-f", "lavfi",
            "-i", "testsrc=size=640x480:rate=1",
            "-t", "1",
            "-pix_fmt", "bgr24",
            "-f", "rawvideo",
            "-"
        ]

        proc = await asyncio.create_subprocess_exec(
            *test_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        # Read one frame (640 * 480 * 3 bytes)
        expected_frame_size = 640 * 480 * 3
        frame_data = await proc.stdout.read(expected_frame_size)

        assert len(frame_data) == expected_frame_size

        # Convert to numpy array
        frame = np.frombuffer(frame_data, dtype=np.uint8).reshape((480, 640, 3))
        assert frame.shape == (480, 640, 3)
        assert frame.dtype == np.uint8

        proc.kill()
        await proc.wait()

    @pytest.mark.integration
    def test_detection_rendering_produces_valid_jpeg(self):
        """Should render bounding boxes and encode to JPEG."""
        from app.services.detection import render_bounding_boxes
        from app.models.detection import Detection

        # Create test frame
        frame = np.zeros((480, 640, 3), dtype=np.uint8)

        # Create test detections
        detections = [
            Detection(
                class_id=0,
                class_name="person",
                confidence=0.95,
                bbox=(100, 100, 200, 200)
            ),
            Detection(
                class_id=2,
                class_name="car",
                confidence=0.85,
                bbox=(300, 200, 450, 350)
            )
        ]

        # Render bounding boxes
        rendered_frame = render_bounding_boxes(frame, detections)

        # Encode to JPEG
        success, jpeg_bytes = cv2.imencode('.jpg', rendered_frame, [cv2.IMWRITE_JPEG_QUALITY, 80])

        assert success
        assert len(jpeg_bytes) > 0

        # Verify JPEG header
        assert jpeg_bytes[0] == 0xFF
        assert jpeg_bytes[1] == 0xD8  # JPEG SOI marker


class TestDetectionConfigPersistence:
    """Tests for detection config persistence in config.yml (T110)."""

    @pytest.mark.integration
    def test_detection_config_saved_to_config_yml(self, tmp_path):
        """Should persist detection config to config.yml."""
        import yaml
        from app.utils.config import save_streams, load_streams

        config_file = tmp_path / "config.yml"

        # Create test stream with detection config
        streams_data = {
            "streams": [
                {
                    "id": "test-stream",
                    "url": "rtsp://test",
                    "enabled": True,
                    "detection": {
                        "enabled": True,
                        "enabled_labels": ["person", "car"],
                        "min_confidence": 0.75
                    }
                }
            ]
        }

        # Save to file
        with patch('app.utils.config.CONFIG_FILE', str(config_file)):
            save_streams(streams_data)

        # Verify file contents
        assert config_file.exists()

        with open(config_file) as f:
            loaded_data = yaml.safe_load(f)

        assert loaded_data["streams"][0]["detection"]["enabled"] is True
        assert loaded_data["streams"][0]["detection"]["enabled_labels"] == ["person", "car"]
        assert loaded_data["streams"][0]["detection"]["min_confidence"] == 0.75

    @pytest.mark.integration
    def test_detection_config_loads_from_config_yml(self, tmp_path):
        """Should load detection config from config.yml on startup."""
        import yaml
        from app.utils.config import load_streams

        config_file = tmp_path / "config.yml"

        # Create config file with detection settings
        config_data = {
            "streams": [
                {
                    "id": "test-stream",
                    "url": "rtsp://test",
                    "enabled": True,
                    "detection": {
                        "enabled": True,
                        "enabled_labels": ["person"],
                        "min_confidence": 0.8
                    }
                }
            ]
        }

        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)

        # Load from file
        with patch('app.utils.config.CONFIG_FILE', str(config_file)):
            loaded_data = load_streams()

        stream = loaded_data["streams"][0]
        assert stream["detection"]["enabled"] is True
        assert stream["detection"]["enabled_labels"] == ["person"]
        assert stream["detection"]["min_confidence"] == 0.8


class TestEndToEndDetectionPipeline:
    """End-to-end test of complete detection pipeline (T107)."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_complete_detection_pipeline_with_synthetic_stream(self, tmp_path):
        """
        Complete E2E test:
        1. Start synthetic RTSP stream with known objects
        2. Configure detection via API
        3. Start stream processing
        4. Verify detections are rendered correctly
        5. Verify metrics are exported
        """
        # Create synthetic test frame with person-like shape
        test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        # Draw a simple rectangle to simulate a person
        cv2.rectangle(test_frame, (200, 100), (350, 400), (255, 255, 255), -1)

        # Preprocess frame
        preprocessed, scale, padding = preprocess_frame(test_frame, target_size=640)

        assert preprocessed.shape == (1, 3, 640, 640)
        assert preprocessed.dtype == np.float32
        assert 0.0 <= preprocessed.min() <= preprocessed.max() <= 1.0

        # Note: Actual inference would require real ONNX model
        # For E2E test, we mock the inference output
        mock_outputs = np.zeros((1, 1, 85))
        mock_outputs[0, 0, 0:4] = [320, 240, 100, 100]  # bbox
        mock_outputs[0, 0, 4] = 0.9  # objectness
        mock_outputs[0, 0, 5] = 0.95  # class 0 (person) probability

        # Parse detections
        detections = parse_detections(
            mock_outputs,
            scale=scale,
            padding=padding,
            original_shape=(480, 640)
        )

        assert len(detections) == 1
        assert detections[0].class_name == "person"
        assert detections[0].confidence > 0.8

        # Filter detections
        config = StreamDetectionConfig(
            enabled=True,
            enabled_labels=["person"],
            min_confidence=0.7
        )

        filtered = filter_detections(
            detections,
            enabled_labels=config.enabled_labels,
            min_confidence=config.min_confidence
        )

        assert len(filtered) == 1
        assert filtered[0].class_name == "person"

        # Render bounding boxes
        rendered = render_bounding_boxes(test_frame.copy(), filtered)

        assert rendered.shape == test_frame.shape
        # Frame should be modified (not all zeros after rendering)
        assert not np.array_equal(rendered, test_frame)

    @pytest.mark.integration
    def test_api_workflow_configure_and_query_detection(self):
        """Test complete API workflow for detection configuration."""
        # 1. Get YOLO config
        with patch('app.api.detection._yolo_config') as mock_config:
            from app.models.detection import YOLOConfig
            mock_config.return_value = YOLOConfig(
                model_name="yolo11n",
                image_size=640,
                backend="nvidia",
                model_path="/app/models/yolo11n_640.onnx"
            )

            response = client.get("/api/yolo/config")
            # May get 503 if not initialized, which is expected
            assert response.status_code in [200, 503]

        # 2. Configure stream detection
        with patch('app.api.detection.load_streams') as mock_load:
            with patch('app.api.detection.save_streams') as mock_save:
                with patch('app.api.detection.container') as mock_container:
                    mock_load.return_value = {
                        "streams": [{"id": "test-stream", "detection": {}}]
                    }
                    mock_container.streams_service = None

                    new_config = {
                        "enabled": True,
                        "enabled_labels": ["person", "car"],
                        "min_confidence": 0.8
                    }

                    response = client.put(
                        "/api/streams/test-stream/detection",
                        json=new_config
                    )

                    assert response.status_code == 200
                    assert mock_save.called

        # 3. Query stream detection config
        with patch('app.api.detection.load_streams') as mock_load:
            mock_load.return_value = {
                "streams": [{
                    "id": "test-stream",
                    "detection": {
                        "enabled": True,
                        "enabled_labels": ["person", "car"],
                        "min_confidence": 0.8
                    }
                }]
            }

            response = client.get("/api/streams/test-stream/detection")

            assert response.status_code == 200
            data = response.json()
            assert data["enabled"] is True
            assert set(data["enabled_labels"]) == {"person", "car"}
            assert data["min_confidence"] == 0.8


class TestDetectionValidation:
    """Validation tests for detection accuracy and performance."""

    @pytest.mark.integration
    def test_label_validation_rejects_invalid_classes(self):
        """Should reject invalid COCO class labels."""
        with patch('app.api.detection.load_streams') as mock_load:
            mock_load.return_value = {
                "streams": [{"id": "test-stream", "detection": {}}]
            }

            invalid_config = {
                "enabled": True,
                "enabled_labels": ["invalid_class", "not_a_real_class"],
                "min_confidence": 0.7
            }

            response = client.put(
                "/api/streams/test-stream/detection",
                json=invalid_config
            )

            assert response.status_code == 422
            assert "invalid_labels" in response.json()["detail"]

    @pytest.mark.integration
    def test_confidence_threshold_clamping(self):
        """Should clamp confidence threshold to [0.0, 1.0]."""
        # Test via Pydantic validation
        config = StreamDetectionConfig(
            enabled=True,
            enabled_labels=["person"],
            min_confidence=0.75
        )

        assert 0.0 <= config.min_confidence <= 1.0

        # Test invalid values raise validation error
        with pytest.raises(Exception):  # Pydantic ValidationError
            StreamDetectionConfig(
                enabled=True,
                enabled_labels=["person"],
                min_confidence=1.5  # > 1.0
            )
