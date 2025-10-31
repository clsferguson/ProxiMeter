"""
YOLO model management and ONNX Runtime inference setup.

This module handles:
- YOLO model downloading and caching
- ONNX export from PyTorch models
- ONNX Runtime session creation with GPU backend selection
- Fail-fast GPU backend validation

Feature: 005-yolo-object-detection
"""

import os
from pathlib import Path
from typing import Optional
import onnxruntime as ort
from ultralytics import YOLO


def load_yolo_model(model_name: str, model_dir: str = "/app/models") -> Path:
    """
    Download and cache YOLO model to specified directory.

    Args:
        model_name: YOLO model variant (e.g., "yolo11n", "yolo11s")
        model_dir: Directory to store downloaded models

    Returns:
        Path to downloaded .pt model file

    Raises:
        RuntimeError: If model download fails
    """
    model_dir_path = Path(model_dir)
    model_dir_path.mkdir(parents=True, exist_ok=True)

    model_pt = model_dir_path / f"{model_name}.pt"

    if model_pt.exists():
        print(f"✅ Model already cached: {model_pt}")
        return model_pt

    try:
        print(f"📥 Downloading {model_name}.pt...")
        model = YOLO(f"{model_name}.pt")
        # Model auto-downloads to ~/.ultralytics by default
        # We need to move it to our cache directory
        default_model = Path.home() / ".ultralytics" / "models" / f"{model_name}.pt"
        if default_model.exists():
            import shutil
            shutil.move(str(default_model), str(model_pt))
            print(f"✅ Model downloaded and cached: {model_pt}")
        return model_pt
    except Exception as e:
        raise RuntimeError(f"Failed to download YOLO model {model_name}: {e}")


def export_to_onnx(
    model_name: str,
    image_size: int,
    model_dir: str = "/app/models",
    simplify: bool = True,
    dynamic: bool = False
) -> Path:
    """
    Export YOLO model to ONNX format.

    Args:
        model_name: YOLO model variant (e.g., "yolo11n")
        image_size: Square input size (e.g., 640 for 640x640)
        model_dir: Directory containing .pt model
        simplify: Enable ONNX simplification (recommended)
        dynamic: Enable dynamic input shapes (not recommended for production)

    Returns:
        Path to exported .onnx model file

    Raises:
        RuntimeError: If ONNX export fails
    """
    model_dir_path = Path(model_dir)
    model_pt = model_dir_path / f"{model_name}.pt"
    model_onnx = model_dir_path / f"{model_name}_{image_size}.onnx"

    if model_onnx.exists():
        print(f"✅ ONNX model already exists: {model_onnx}")
        return model_onnx

    if not model_pt.exists():
        raise RuntimeError(f"PyTorch model not found: {model_pt}")

    try:
        print(f"⏳ Exporting {model_name}.pt to ONNX format (size={image_size})...")
        model = YOLO(str(model_pt))
        model.export(
            format="onnx",
            imgsz=image_size,
            simplify=simplify,
            dynamic=dynamic
        )

        # Ultralytics exports to same directory as .pt file with name model_name.onnx
        # We need to rename to include image size
        exported_onnx = model_dir_path / f"{model_name}.onnx"
        if exported_onnx.exists():
            exported_onnx.rename(model_onnx)
            print(f"✅ ONNX export complete: {model_onnx}")
            print(f"📦 Model size: {model_onnx.stat().st_size / (1024*1024):.1f} MB")
        else:
            raise RuntimeError(f"ONNX export succeeded but file not found: {exported_onnx}")

        return model_onnx
    except Exception as e:
        raise RuntimeError(f"Failed to export YOLO model to ONNX: {e}")


def create_onnx_session(
    model_path: str,
    gpu_backend: str,
    fail_fast: bool = True
) -> ort.InferenceSession:
    """
    Create ONNX Runtime inference session with GPU backend selection.

    Args:
        model_path: Path to ONNX model file
        gpu_backend: GPU backend ("nvidia", "amd", "intel", "none")
        fail_fast: Raise error if GPU backend unavailable (default: True)

    Returns:
        ONNX Runtime InferenceSession

    Raises:
        RuntimeError: If GPU backend requested but unavailable (when fail_fast=True)
        FileNotFoundError: If model file doesn't exist
    """
    model_path_obj = Path(model_path)
    if not model_path_obj.exists():
        raise FileNotFoundError(f"ONNX model not found: {model_path}")

    providers = []

    # Configure GPU execution provider based on backend
    if gpu_backend == "nvidia":
        providers.append(('CUDAExecutionProvider', {
            'device_id': 0,
            'arena_extend_strategy': 'kNextPowerOfTwo',
            'gpu_mem_limit': 2 * 1024 * 1024 * 1024,  # 2 GB
            'cudnn_conv_algo_search': 'EXHAUSTIVE',
        }))
    elif gpu_backend == "amd":
        providers.append(('ROCmExecutionProvider', {
            'device_id': 0
        }))
    elif gpu_backend == "intel":
        providers.append(('OpenVINOExecutionProvider', {
            'device_type': 'GPU_FP32'
        }))

    # Always add CPU as fallback (unless fail_fast prevents it)
    providers.append('CPUExecutionProvider')

    # Create session with optimizations
    session_options = ort.SessionOptions()
    session_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

    try:
        session = ort.InferenceSession(
            str(model_path),
            sess_options=session_options,
            providers=providers
        )
    except Exception as e:
        raise RuntimeError(f"Failed to create ONNX Runtime session: {e}")

    # Fail-fast GPU backend validation
    active_provider = session.get_providers()[0]
    if fail_fast and gpu_backend != "none" and active_provider == "CPUExecutionProvider":
        raise RuntimeError(
            f"GPU backend '{gpu_backend}' unavailable. "
            f"ONNX Runtime fell back to CPU. "
            f"Available providers: {ort.get_available_providers()}"
        )

    print(f"✅ ONNX Runtime session created")
    print(f"   Active provider: {active_provider}")
    print(f"   Model: {model_path}")

    return session


def list_cached_models(model_dir: str = "/app/models") -> list[dict]:
    """
    Scan model cache directory and return metadata for all .onnx files.

    Args:
        model_dir: Directory containing cached models

    Returns:
        List of model metadata dictionaries
    """
    model_dir_path = Path(model_dir)
    if not model_dir_path.exists():
        return []

    models = []
    for onnx_file in model_dir_path.glob("*.onnx"):
        stat = onnx_file.stat()
        models.append({
            "model_name": onnx_file.stem,
            "file_path": str(onnx_file),
            "file_size_bytes": stat.st_size,
            "download_date": stat.st_ctime,
        })

    return models


def delete_cached_model(model_name: str, model_dir: str = "/app/models") -> int:
    """
    Delete a cached ONNX model file.

    Args:
        model_name: Name of model to delete (without extension)
        model_dir: Directory containing cached models

    Returns:
        Number of bytes freed

    Raises:
        FileNotFoundError: If model file doesn't exist
    """
    model_path = Path(model_dir) / f"{model_name}.onnx"
    if not model_path.exists():
        raise FileNotFoundError(f"Model not found: {model_path}")

    file_size = model_path.stat().st_size
    model_path.unlink()
    print(f"🗑️ Deleted model: {model_path} ({file_size / (1024*1024):.1f} MB)")

    return file_size
