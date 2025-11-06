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
import warnings
from pathlib import Path
from typing import Optional
import onnxruntime as ort
import logging

# Suppress Ultralytics and PyTorch warnings
os.environ['YOLO_VERBOSE'] = 'False'
warnings.filterwarnings('ignore', category=UserWarning, module='ultralytics')
warnings.filterwarnings('ignore', category=FutureWarning, module='torch')

from ultralytics import YOLO

logger = logging.getLogger(__name__)


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
        logger.info(f"Model already cached: {model_pt}")
        print(f"✅ Model already cached: {model_pt}")
        return model_pt

    try:
        logger.info(f"Downloading {model_name}.pt...")
        print(f"📥 Downloading {model_name}.pt...")
        # YOLO() auto-downloads model to ~/.ultralytics/models
        # We pass the target path to export later, but the .pt file stays in default location
        model = YOLO(f"{model_name}.pt")

        # Check if model was downloaded to default location
        default_model = Path.home() / ".ultralytics" / "models" / f"{model_name}.pt"
        if default_model.exists():
            # Create symlink or copy to our cache directory for consistency
            import shutil
            if not model_pt.exists():
                logger.debug(f"Copying model from {default_model} to {model_pt}")
                shutil.copy2(str(default_model), str(model_pt))
            logger.info(f"Model downloaded and cached: {model_pt}")
            print(f"✅ Model downloaded and cached: {model_pt}")
            return model_pt

        # If not in default location, model might already be at target
        if model_pt.exists():
            logger.info(f"Model found at: {model_pt}")
            print(f"✅ Model found at: {model_pt}")
            return model_pt

        raise FileNotFoundError(f"Model download succeeded but file not found at expected locations")
    except Exception as e:
        logger.error(f"Failed to download YOLO model {model_name}: {e}", exc_info=True)
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
        logger.info(f"ONNX model already exists: {model_onnx}")
        print(f"✅ ONNX model already exists: {model_onnx}")
        return model_onnx

    if not model_pt.exists():
        logger.error(f"PyTorch model not found: {model_pt}")
        raise RuntimeError(f"PyTorch model not found: {model_pt}")

    try:
        logger.info(f"Exporting {model_name}.pt to ONNX format (size={image_size})...")
        print(f"⏳ Exporting {model_name}.pt to ONNX format (size={image_size})...")
        model = YOLO(str(model_pt))
        model.export(
            format="onnx",
            imgsz=image_size,
            simplify=simplify,
            dynamic=dynamic
        )

        # Ultralytics exports to current working directory with name model_name.onnx
        # We need to copy to model_dir with image size in name
        import shutil
        import os

        # Check current directory first (where export happens)
        cwd_onnx = Path.cwd() / f"{model_name}.onnx"
        exported_onnx = model_dir_path / f"{model_name}.onnx"

        source_file = None
        if cwd_onnx.exists() and cwd_onnx != model_onnx:
            source_file = cwd_onnx
        elif exported_onnx.exists() and exported_onnx != model_onnx:
            source_file = exported_onnx
        elif model_onnx.exists():
            # Already at target location
            print(f"✅ ONNX export complete: {model_onnx}")
            print(f"📦 Model size: {model_onnx.stat().st_size / (1024*1024):.1f} MB")
            return model_onnx

        if source_file:
            # Use copy + remove instead of move to handle cross-device links
            logger.debug(f"Copying ONNX from {source_file} to {model_onnx}")
            shutil.copy2(str(source_file), str(model_onnx))
            source_file.unlink()  # Remove source after successful copy
            logger.info(f"ONNX export complete: {model_onnx} ({model_onnx.stat().st_size / (1024*1024):.1f} MB)")
            print(f"✅ ONNX export complete: {model_onnx}")
            print(f"📦 Model size: {model_onnx.stat().st_size / (1024*1024):.1f} MB")
        else:
            logger.error(f"ONNX export succeeded but file not found at {cwd_onnx} or {exported_onnx}")
            raise RuntimeError(f"ONNX export succeeded but file not found at {cwd_onnx} or {exported_onnx}")

        return model_onnx
    except Exception as e:
        logger.error(f"Failed to export YOLO model to ONNX: {e}", exc_info=True)
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
    logger.info(f"Creating ONNX Runtime session: model={model_path}, backend={gpu_backend}, fail_fast={fail_fast}")
    model_path_obj = Path(model_path)
    if not model_path_obj.exists():
        logger.error(f"ONNX model not found: {model_path}")
        raise FileNotFoundError(f"ONNX model not found: {model_path}")

    providers = []

    # Configure GPU execution provider based on backend
    if gpu_backend == "nvidia":
        logger.debug("Configuring CUDA execution provider")
        providers.append(('CUDAExecutionProvider', {
            'device_id': 0,
            'arena_extend_strategy': 'kNextPowerOfTwo',
            'gpu_mem_limit': 2 * 1024 * 1024 * 1024,  # 2 GB
            'cudnn_conv_algo_search': 'EXHAUSTIVE',
        }))
    elif gpu_backend == "amd":
        logger.debug("Configuring ROCm execution provider")
        providers.append(('ROCmExecutionProvider', {
            'device_id': 0
        }))
    elif gpu_backend == "intel":
        logger.debug("Configuring OpenVINO execution provider")
        providers.append(('OpenVINOExecutionProvider', {
            'device_type': 'GPU_FP32'
        }))

    # Always add CPU as fallback (unless fail_fast prevents it)
    providers.append('CPUExecutionProvider')
    logger.debug(f"Execution providers configured: {[p if isinstance(p, str) else p[0] for p in providers]}")

    # Create session with optimizations
    session_options = ort.SessionOptions()
    session_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

    try:
        logger.debug("Creating ONNX Runtime inference session...")
        session = ort.InferenceSession(
            str(model_path),
            sess_options=session_options,
            providers=providers
        )
        logger.debug(f"Session created successfully")
    except Exception as e:
        logger.error(f"Failed to create ONNX Runtime session: {e}", exc_info=True)
        raise RuntimeError(f"Failed to create ONNX Runtime session: {e}")

    # Fail-fast GPU backend validation
    active_provider = session.get_providers()[0]
    logger.info(f"Active execution provider: {active_provider}")

    if fail_fast and gpu_backend != "none" and active_provider == "CPUExecutionProvider":
        logger.error(f"GPU backend '{gpu_backend}' unavailable - fell back to CPU")
        logger.error(f"Available providers: {ort.get_available_providers()}")
        raise RuntimeError(
            f"GPU backend '{gpu_backend}' unavailable. "
            f"ONNX Runtime fell back to CPU. "
            f"Available providers: {ort.get_available_providers()}"
        )

    logger.info(f"ONNX Runtime session created successfully")
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
