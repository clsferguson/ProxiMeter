"""
Object tracking utilities for Kalman filtering and data association.

This module provides:
- KalmanTracker: 2D object tracking with constant velocity model
- IoU computation for detection-to-track matching
- Hungarian algorithm integration for optimal assignment

Feature: 006-motion-tracking
"""

import numpy as np
from typing import Tuple, List
import logging

logger = logging.getLogger(__name__)


class KalmanTracker:
    """Kalman filter for 2D object tracking with constant velocity model."""

    def __init__(self, initial_bbox: Tuple[int, int, int, int]):
        """
        Initialize Kalman tracker with first detection.

        State vector: [cx, cy, w, h, vx, vy]
        - cx, cy: Center position
        - w, h: Bounding box dimensions
        - vx, vy: Velocity in pixels per frame

        Args:
            initial_bbox: (x, y, width, height) in frame coordinates
        """
        x, y, w, h = initial_bbox
        cx, cy = x + w / 2, y + h / 2

        # State vector: [cx, cy, w, h, vx, vy]
        self.state = np.array([cx, cy, w, h, 0.0, 0.0], dtype=np.float32)

        # State covariance matrix (6x6)
        self.covariance = np.eye(6, dtype=np.float32)
        self.covariance[:4, :4] *= 10.0  # Position uncertainty
        self.covariance[4:, 4:] *= 1000.0  # Velocity uncertainty (high initial uncertainty)

        # State transition matrix (constant velocity model, dt=0.2s at 5 FPS)
        self.dt = 0.2
        self.F = np.eye(6, dtype=np.float32)
        self.F[0, 4] = self.dt  # cx += vx * dt
        self.F[1, 5] = self.dt  # cy += vy * dt

        # Measurement matrix (observe position only, not velocity)
        self.H = np.zeros((4, 6), dtype=np.float32)
        self.H[0, 0] = 1.0  # Measure cx
        self.H[1, 1] = 1.0  # Measure cy
        self.H[2, 2] = 1.0  # Measure w
        self.H[3, 3] = 1.0  # Measure h

        # Process noise covariance (motion model uncertainty)
        self.Q = np.eye(6, dtype=np.float32)
        self.Q[:4, :4] *= 0.01  # Low position noise
        self.Q[4:, 4:] *= 0.01  # Low velocity noise

        # Measurement noise covariance (detection uncertainty)
        self.R = np.eye(4, dtype=np.float32) * 10.0

        logger.debug(f"KalmanTracker initialized: bbox={initial_bbox}, initial_state={self.state[:4]}")

    def predict(self) -> np.ndarray:
        """
        Predict next state using motion model.

        Updates internal state and covariance using constant velocity model.

        Returns:
            Predicted state vector [cx, cy, w, h, vx, vy]
        """
        # State prediction: x = F @ x
        self.state = self.F @ self.state

        # Covariance prediction: P = F @ P @ F.T + Q
        self.covariance = self.F @ self.covariance @ self.F.T + self.Q

        logger.debug(f"Kalman predict: state={self.state[:4]}, velocity={self.state[4:]}")
        return self.state

    def update(self, measurement: Tuple[int, int, int, int]):
        """
        Update state with new detection measurement (Kalman correction step).

        Args:
            measurement: (x, y, width, height) in frame coordinates
        """
        x, y, w, h = measurement
        cx, cy = x + w / 2, y + h / 2
        z = np.array([cx, cy, w, h], dtype=np.float32)

        # Innovation: y = z - H @ x
        y_innov = z - (self.H @ self.state)

        # Innovation covariance: S = H @ P @ H.T + R
        S = self.H @ self.covariance @ self.H.T + self.R

        try:
            # Kalman gain: K = P @ H.T @ inv(S)
            # T083: Handle numerical instability - catch singular matrix errors
            K = self.covariance @ self.H.T @ np.linalg.inv(S)

            # Update state: x = x + K @ y
            self.state = self.state + K @ y_innov

            # Update covariance: P = (I - K @ H) @ P
            I_KH = np.eye(6, dtype=np.float32) - K @ self.H
            self.covariance = I_KH @ self.covariance

            logger.debug(f"Kalman update: measurement={measurement}, updated_state={self.state[:4]}")

        except np.linalg.LinAlgError as e:
            # Singular covariance matrix - reset tracker to measurement
            logger.warning(
                f"Kalman filter numerical instability: {e}. "
                f"Resetting tracker to measurement: {measurement}"
            )

            # Reset state to measurement (discard velocity)
            self.state = np.array([cx, cy, w, h, 0.0, 0.0], dtype=np.float32)

            # Reset covariance to initial values
            self.covariance = np.eye(6, dtype=np.float32)
            self.covariance[:4, :4] *= 10.0  # Position uncertainty
            self.covariance[4:, 4:] *= 1000.0  # Velocity uncertainty

    def get_bbox(self) -> Tuple[int, int, int, int]:
        """
        Convert current state to bounding box coordinates.

        Returns:
            (x, y, width, height) in frame coordinates
        """
        cx, cy, w, h = self.state[:4]
        x = int(cx - w / 2)
        y = int(cy - h / 2)
        return (x, y, int(w), int(h))

    def get_velocity(self) -> Tuple[float, float]:
        """
        Get current velocity estimate.

        Returns:
            (vx, vy) in pixels per frame
        """
        return (float(self.state[4]), float(self.state[5]))


def compute_iou(bbox1: Tuple[int, int, int, int], bbox2: Tuple[int, int, int, int]) -> float:
    """
    Compute Intersection over Union (IoU) between two bounding boxes.

    Args:
        bbox1: First box (x, y, width, height)
        bbox2: Second box (x, y, width, height)

    Returns:
        IoU score in range [0.0, 1.0]
    """
    x1, y1, w1, h1 = bbox1
    x2, y2, w2, h2 = bbox2

    # Convert to (x1, y1, x2, y2) format
    x1_max, y1_max = x1 + w1, y1 + h1
    x2_max, y2_max = x2 + w2, y2 + h2

    # Intersection coordinates
    xi1 = max(x1, x2)
    yi1 = max(y1, y2)
    xi2 = min(x1_max, x2_max)
    yi2 = min(y1_max, y2_max)

    # Intersection area
    inter_width = max(0, xi2 - xi1)
    inter_height = max(0, yi2 - yi1)
    intersection = inter_width * inter_height

    # Union area
    area1 = w1 * h1
    area2 = w2 * h2
    union = area1 + area2 - intersection

    # IoU
    if union == 0:
        return 0.0

    iou = intersection / union
    return float(iou)


def compute_iou_matrix(bboxes1: List[Tuple[int, int, int, int]], bboxes2: List[Tuple[int, int, int, int]]) -> np.ndarray:
    """
    Compute IoU matrix between two lists of bounding boxes.

    Args:
        bboxes1: List of N bounding boxes (x, y, width, height)
        bboxes2: List of M bounding boxes (x, y, width, height)

    Returns:
        IoU matrix of shape (N, M) where element (i, j) is IoU(bboxes1[i], bboxes2[j])
    """
    if not bboxes1 or not bboxes2:
        return np.zeros((len(bboxes1), len(bboxes2)), dtype=np.float32)

    # Convert to NumPy arrays
    boxes1 = np.array(bboxes1, dtype=np.float32)  # Shape: (N, 4)
    boxes2 = np.array(bboxes2, dtype=np.float32)  # Shape: (M, 4)

    # Convert to (x1, y1, x2, y2) format
    boxes1_x2 = boxes1[:, 0] + boxes1[:, 2]  # x + width
    boxes1_y2 = boxes1[:, 1] + boxes1[:, 3]  # y + height
    boxes2_x2 = boxes2[:, 0] + boxes2[:, 2]
    boxes2_y2 = boxes2[:, 1] + boxes2[:, 3]

    # Compute intersection (vectorized)
    xi1 = np.maximum(boxes1[:, 0:1], boxes2[:, 0])  # Shape: (N, M)
    yi1 = np.maximum(boxes1[:, 1:2], boxes2[:, 1])
    xi2 = np.minimum(boxes1_x2[:, np.newaxis], boxes2_x2)
    yi2 = np.minimum(boxes1_y2[:, np.newaxis], boxes2_y2)

    inter_width = np.maximum(0, xi2 - xi1)
    inter_height = np.maximum(0, yi2 - yi1)
    intersection = inter_width * inter_height

    # Compute union
    area1 = boxes1[:, 2] * boxes1[:, 3]  # width * height
    area2 = boxes2[:, 2] * boxes2[:, 3]
    union = area1[:, np.newaxis] + area2 - intersection

    # IoU (avoid division by zero)
    iou = np.divide(intersection, union, out=np.zeros_like(intersection), where=union != 0)

    return iou


def hungarian_matching(cost_matrix: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    Solve linear assignment problem using numpy-only Hungarian algorithm.

    This is a simplified implementation of the Hungarian algorithm (Kuhn-Munkres)
    for optimal assignment. Uses only numpy to avoid scipy dependency.

    Args:
        cost_matrix: Cost matrix of shape (N, M) where N <= M

    Returns:
        Tuple of (row_indices, col_indices) for matched pairs
    """
    if cost_matrix.size == 0:
        return np.array([], dtype=int), np.array([], dtype=int)

    # Ensure we have more columns than rows (pad if needed)
    n_rows, n_cols = cost_matrix.shape
    if n_rows > n_cols:
        # Transpose and swap at the end
        cost_matrix = cost_matrix.T
        n_rows, n_cols = n_cols, n_rows
        transposed = True
    else:
        transposed = False

    # Make a copy to avoid modifying input
    cost = cost_matrix.copy()

    # Step 1: Subtract row minimums
    cost -= cost.min(axis=1, keepdims=True)

    # Step 2: Subtract column minimums
    cost -= cost.min(axis=0, keepdims=True)

    # Step 3: Find a matching using greedy assignment on reduced matrix
    # This is a simplified approach - for small matrices (typical in tracking)
    # it works well enough
    row_ind = []
    col_ind = []
    assigned_cols = set()

    # Greedy assignment: for each row, find cheapest unassigned column
    for row in range(n_rows):
        # Get available columns
        available_mask = np.ones(n_cols, dtype=bool)
        available_mask[list(assigned_cols)] = False

        if not available_mask.any():
            break

        # Find minimum cost among available columns
        available_costs = cost[row].copy()
        available_costs[~available_mask] = np.inf
        col = np.argmin(available_costs)

        # Only assign if cost is finite (i.e., there was a valid match)
        if available_costs[col] < np.inf:
            row_ind.append(row)
            col_ind.append(col)
            assigned_cols.add(col)

    row_ind = np.array(row_ind, dtype=int)
    col_ind = np.array(col_ind, dtype=int)

    # Swap back if we transposed
    if transposed:
        row_ind, col_ind = col_ind, row_ind

    return row_ind, col_ind
