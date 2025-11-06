"""
Unit tests for YOLO model management service.

Tests model loading, ONNX export, session creation, and cache management.
Feature: 005-yolo-object-detection
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from app.services.yolo import (
    load_yolo_model,
    export_to_onnx,
    create_onnx_session,
    list_cached_models,
    delete_cached_model,
)


class TestLoadYoloModel:
    """Tests for load_yolo_model() function."""

    def test_returns_cached_model_if_exists(self, tmp_path):
        """Should return existing model without downloading."""
        model_path = tmp_path / "yolo11n.pt"
        model_path.touch()

        result = load_yolo_model("yolo11n", str(tmp_path))
        assert result == model_path

    @patch('app.services.yolo.YOLO')
    def test_downloads_model_if_not_cached(self, mock_yolo, tmp_path):
        """Should download model if not in cache."""
        result = load_yolo_model("yolo11n", str(tmp_path))
        assert mock_yolo.called

    def test_raises_runtime_error_on_download_failure(self, tmp_path):
        """Should raise RuntimeError if download fails."""
        with patch('app.services.yolo.YOLO', side_effect=Exception("Network error")):
            with pytest.raises(RuntimeError, match="Failed to download"):
                load_yolo_model("yolo11n", str(tmp_path))


class TestExportToOnnx:
    """Tests for export_to_onnx() function."""

    def test_returns_cached_onnx_if_exists(self, tmp_path):
        """Should return existing ONNX model without re-exporting."""
        onnx_path = tmp_path / "yolo11n_640.onnx"
        onnx_path.touch()

        result = export_to_onnx("yolo11n", 640, str(tmp_path))
        assert result == onnx_path

    def test_raises_error_if_pt_model_missing(self, tmp_path):
        """Should raise RuntimeError if .pt model doesn't exist."""
        with pytest.raises(RuntimeError, match="PyTorch model not found"):
            export_to_onnx("yolo11n", 640, str(tmp_path))

    @patch('app.services.yolo.YOLO')
    def test_exports_with_correct_parameters(self, mock_yolo, tmp_path):
        """Should call export with correct format and size."""
        pt_path = tmp_path / "yolo11n.pt"
        pt_path.touch()

        mock_model = Mock()
        mock_yolo.return_value = mock_model

        with patch.object(Path, 'exists', return_value=True):
            with patch.object(Path, 'rename'):
                export_to_onnx("yolo11n", 640, str(tmp_path), simplify=True, dynamic=False)

        mock_model.export.assert_called_once_with(
            format="onnx",
            imgsz=640,
            simplify=True,
            dynamic=False
        )


class TestCreateOnnxSession:
    """Tests for create_onnx_session() function."""

    def test_raises_file_not_found_if_model_missing(self):
        """Should raise FileNotFoundError if model doesn't exist."""
        with pytest.raises(FileNotFoundError):
            create_onnx_session("/nonexistent/model.onnx", "none")

    @patch('app.services.yolo.ort.InferenceSession')
    @patch('app.services.yolo.Path')
    def test_uses_cuda_provider_for_nvidia_backend(self, mock_path, mock_session):
        """Should configure CUDAExecutionProvider for NVIDIA GPU."""
        mock_path.return_value.exists.return_value = True
        mock_session_instance = Mock()
        mock_session_instance.get_providers.return_value = ['CUDAExecutionProvider']
        mock_session.return_value = mock_session_instance

        session = create_onnx_session("/path/model.onnx", "nvidia", fail_fast=False)

        # Verify CUDA provider was requested
        call_args = mock_session.call_args
        providers = call_args.kwargs.get('providers', [])
        assert any('CUDAExecutionProvider' in str(p) for p in providers)

    @patch('app.services.yolo.ort.InferenceSession')
    @patch('app.services.yolo.Path')
    def test_fails_fast_if_gpu_unavailable(self, mock_path, mock_session):
        """Should raise RuntimeError if GPU requested but unavailable."""
        mock_path.return_value.exists.return_value = True
        mock_session_instance = Mock()
        mock_session_instance.get_providers.return_value = ['CPUExecutionProvider']
        mock_session.return_value = mock_session_instance

        with pytest.raises(RuntimeError, match="GPU backend .* unavailable"):
            create_onnx_session("/path/model.onnx", "nvidia", fail_fast=True)


class TestListCachedModels:
    """Tests for list_cached_models() function."""

    def test_returns_empty_list_if_directory_missing(self):
        """Should return empty list if model directory doesn't exist."""
        result = list_cached_models("/nonexistent")
        assert result == []

    def test_lists_all_onnx_files(self, tmp_path):
        """Should list all .onnx files with metadata."""
        (tmp_path / "yolo11n_640.onnx").touch()
        (tmp_path / "yolo11s_640.onnx").touch()
        (tmp_path / "other.txt").touch()  # Should be ignored

        result = list_cached_models(str(tmp_path))

        assert len(result) == 2
        assert all('model_name' in m for m in result)
        assert all('file_size_bytes' in m for m in result)
        assert all('download_date' in m for m in result)

    def test_includes_file_size_and_timestamp(self, tmp_path):
        """Should include file size and modification time."""
        model_path = tmp_path / "yolo11n_640.onnx"
        model_path.write_bytes(b"x" * 1000)

        result = list_cached_models(str(tmp_path))

        assert result[0]['file_size_bytes'] == 1000
        assert isinstance(result[0]['download_date'], (int, float))


class TestDeleteCachedModel:
    """Tests for delete_cached_model() function."""

    def test_raises_file_not_found_if_model_missing(self, tmp_path):
        """Should raise FileNotFoundError if model doesn't exist."""
        with pytest.raises(FileNotFoundError):
            delete_cached_model("nonexistent", str(tmp_path))

    def test_deletes_model_and_returns_size(self, tmp_path):
        """Should delete model file and return freed bytes."""
        model_path = tmp_path / "yolo11n_640.onnx"
        model_path.write_bytes(b"x" * 1000)

        freed_bytes = delete_cached_model("yolo11n_640", str(tmp_path))

        assert freed_bytes == 1000
        assert not model_path.exists()
