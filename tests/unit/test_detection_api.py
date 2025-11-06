"""
Unit tests for detection API endpoints.

Tests GET /api/yolo/config, GET /api/models, DELETE /api/models/{name},
GET/PUT /api/streams/{id}/detection endpoints.

Feature: 005-yolo-object-detection
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock
from app.main import app
from app.models.detection import YOLOConfig, StreamDetectionConfig


client = TestClient(app)


class TestYoloConfigEndpoint:
    """Tests for GET /api/yolo/config endpoint."""

    def test_returns_yolo_config_when_initialized(self):
        """Should return YOLOConfig when model is initialized."""
        config = YOLOConfig(
            model_name="yolo11n",
            image_size=640,
            backend="nvidia",
            model_path="/app/models/yolo11n_640.onnx"
        )

        with patch('app.api.detection._yolo_config', config):
            response = client.get("/api/yolo/config")

        assert response.status_code == 200
        data = response.json()
        assert data["model_name"] == "yolo11n"
        assert data["image_size"] == 640
        assert data["backend"] == "nvidia"

    def test_returns_503_when_not_initialized(self):
        """Should return 503 Service Unavailable if model not initialized."""
        with patch('app.api.detection._yolo_config', None):
            response = client.get("/api/yolo/config")

        assert response.status_code == 503
        assert "not initialized" in response.json()["detail"]


class TestListModelsEndpoint:
    """Tests for GET /api/models endpoint."""

    @patch('app.api.detection.list_cached_models')
    def test_returns_list_of_cached_models(self, mock_list):
        """Should return list of cached models with metadata."""
        mock_list.return_value = [
            {
                "model_name": "yolo11n_640",
                "file_path": "/app/models/yolo11n_640.onnx",
                "file_size_bytes": 6291456,
                "download_date": 1234567890,
            }
        ]

        config = YOLOConfig(
            model_name="yolo11n",
            image_size=640,
            backend="nvidia",
            model_path="/app/models/yolo11n_640.onnx"
        )

        with patch('app.api.detection._yolo_config', config):
            response = client.get("/api/models")

        assert response.status_code == 200
        data = response.json()
        assert len(data["models"]) == 1
        assert data["active_model"] == "yolo11n_640"
        assert data["models"][0]["is_active"] is True

    @patch('app.api.detection.list_cached_models')
    def test_handles_empty_model_list(self, mock_list):
        """Should handle empty model list gracefully."""
        mock_list.return_value = []

        response = client.get("/api/models")

        assert response.status_code == 200
        data = response.json()
        assert data["models"] == []


class TestDeleteModelEndpoint:
    """Tests for DELETE /api/models/{model_name} endpoint."""

    @patch('app.api.detection.delete_cached_model')
    def test_deletes_model_successfully(self, mock_delete):
        """Should delete model and return freed bytes."""
        mock_delete.return_value = 6291456

        config = YOLOConfig(
            model_name="yolo11n",
            image_size=640,
            backend="nvidia",
            model_path="/app/models/yolo11n_640.onnx"
        )

        with patch('app.api.detection._yolo_config', config):
            response = client.delete("/api/models/yolo11s_640")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["freed_bytes"] == 6291456

    def test_returns_409_when_deleting_active_model(self):
        """Should return 409 Conflict when trying to delete active model."""
        config = YOLOConfig(
            model_name="yolo11n",
            image_size=640,
            backend="nvidia",
            model_path="/app/models/yolo11n_640.onnx"
        )

        with patch('app.api.detection._yolo_config', config):
            response = client.delete("/api/models/yolo11n_640")

        assert response.status_code == 409
        assert "active model" in response.json()["detail"].lower()

    @patch('app.api.detection.delete_cached_model')
    def test_returns_404_when_model_not_found(self, mock_delete):
        """Should return 404 Not Found if model doesn't exist."""
        mock_delete.side_effect = FileNotFoundError("Model not found")

        response = client.delete("/api/models/nonexistent")

        assert response.status_code == 404


class TestGetStreamDetectionConfigEndpoint:
    """Tests for GET /api/streams/{stream_id}/detection endpoint."""

    @patch('app.api.detection.load_streams')
    def test_returns_detection_config_for_stream(self, mock_load):
        """Should return StreamDetectionConfig for given stream."""
        mock_load.return_value = {
            "streams": [
                {
                    "id": "test-stream-id",
                    "detection": {
                        "enabled": True,
                        "enabled_labels": ["person", "car"],
                        "min_confidence": 0.75
                    }
                }
            ]
        }

        response = client.get("/api/streams/test-stream-id/detection")

        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] is True
        assert data["enabled_labels"] == ["person", "car"]
        assert data["min_confidence"] == 0.75

    @patch('app.api.detection.load_streams')
    def test_returns_404_for_nonexistent_stream(self, mock_load):
        """Should return 404 if stream not found."""
        mock_load.return_value = {"streams": []}

        response = client.get("/api/streams/nonexistent/detection")

        assert response.status_code == 404


class TestUpdateStreamDetectionConfigEndpoint:
    """Tests for PUT /api/streams/{stream_id}/detection endpoint."""

    @patch('app.api.detection.save_streams')
    @patch('app.api.detection.load_streams')
    @patch('app.api.detection.container')
    def test_updates_detection_config_successfully(self, mock_container, mock_load, mock_save):
        """Should update detection config and save to file."""
        mock_load.return_value = {
            "streams": [{"id": "test-stream-id", "detection": {}}]
        }
        mock_container.streams_service = None

        new_config = {
            "enabled": True,
            "enabled_labels": ["person"],
            "min_confidence": 0.8
        }

        response = client.put("/api/streams/test-stream-id/detection", json=new_config)

        assert response.status_code == 200
        assert mock_save.called

    @patch('app.api.detection.load_streams')
    def test_validates_enabled_labels_against_coco_classes(self, mock_load):
        """Should return 422 for invalid COCO class labels."""
        mock_load.return_value = {
            "streams": [{"id": "test-stream-id", "detection": {}}]
        }

        invalid_config = {
            "enabled": True,
            "enabled_labels": ["invalid_class", "not_a_class"],
            "min_confidence": 0.7
        }

        response = client.put("/api/streams/test-stream-id/detection", json=invalid_config)

        assert response.status_code == 422
        assert "invalid_labels" in response.json()["detail"]

    @patch('app.api.detection.save_streams')
    @patch('app.api.detection.load_streams')
    @patch('app.api.detection.container')
    def test_applies_config_immediately_to_running_stream(self, mock_container, mock_load, mock_save):
        """Should update active_processes if stream is running."""
        mock_load.return_value = {
            "streams": [{"id": "test-stream-id", "detection": {}}]
        }

        mock_service = Mock()
        mock_service.active_processes = {"test-stream-id": {}}
        mock_container.streams_service = mock_service

        new_config = {
            "enabled": True,
            "enabled_labels": ["person"],
            "min_confidence": 0.8
        }

        response = client.put("/api/streams/test-stream-id/detection", json=new_config)

        assert response.status_code == 200
        data = response.json()
        assert data["applied_immediately"] is True
        assert "detection_config" in mock_service.active_processes["test-stream-id"]
