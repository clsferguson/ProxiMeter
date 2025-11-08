"""
Motion detection and object tracking services.

This module handles:
- Background subtraction with OpenCV MOG2
- Motion region extraction and merging
- Object tracking with Kalman filtering
- Track lifecycle management

Feature: 006-motion-tracking
"""

import cv2
import numpy as np
from typing import List, Tuple, Optional
import logging
from app.models.motion import MotionRegion, TrackedObject, ObjectState
from app.utils.tracking import KalmanTracker, compute_iou_matrix, hungarian_matching

logger = logging.getLogger(__name__)


class MotionDetector:
    """CPU-based motion detection using OpenCV background subtraction."""

    def __init__(
        self,
        history: int = 500,
        var_threshold: int = 16,
        detect_shadows: bool = True,
        learning_rate: float = 0.005,
        min_contour_area: int = 500,
        merge_distance_threshold: int = 40,
        nms_iou_threshold: float = 0.4
    ):
        """
        Initialize motion detector with MOG2 background subtractor.

        Args:
            history: Number of frames for background model history
            var_threshold: Variance threshold for motion detection (4 sigma)
            detect_shadows: Enable shadow detection
            learning_rate: Background model learning rate (0.005 for stable scenes)
            min_contour_area: Minimum contour area in pixels to filter noise
            merge_distance_threshold: Distance threshold for merging nearby regions (pixels)
            nms_iou_threshold: IoU threshold for Non-Maximum Suppression
        """
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=history,
            varThreshold=var_threshold,
            detectShadows=detect_shadows
        )
        self.learning_rate = learning_rate
        self.min_contour_area = min_contour_area
        self.merge_distance_threshold = merge_distance_threshold
        self.nms_iou_threshold = nms_iou_threshold

        # Morphological kernel for noise removal
        self.morph_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))

        # T091: False positive rate monitoring (rolling 1-minute window)
        from collections import deque
        self._motion_window = deque(maxlen=300)  # 300 frames = 60s at 5 FPS
        self._last_fps_check = 0
        self._fps_check_interval = 50  # Check every 50 frames (10 seconds)
        self._frame_count = 0

        logger.info(
            f"MotionDetector initialized: history={history}, "
            f"varThreshold={var_threshold}, detectShadows={detect_shadows}, "
            f"learning_rate={learning_rate}"
        )

    def extract_motion_regions(
        self,
        frame: np.ndarray,
        timestamp: float
    ) -> List[MotionRegion]:
        """
        Extract motion regions from frame using background subtraction.

        Steps:
        1. Convert frame to grayscale
        2. Apply background subtraction
        3. Morphological operations (erosion + dilation) to remove noise
        4. Find contours
        5. Filter by minimum area
        6. Merge nearby contours
        7. Apply Non-Maximum Suppression
        8. Add 15% padding with boundary clipping

        Args:
            frame: Input frame in BGR format (OpenCV native)
            timestamp: Frame timestamp in seconds

        Returns:
            List of MotionRegion objects with valid bounding boxes
        """
        frame_height, frame_width = frame.shape[:2]

        # Step 1: Convert to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Step 2: Background subtraction
        fg_mask = self.bg_subtractor.apply(gray, learningRate=self.learning_rate)

        # Step 3: Morphological operations (noise removal)
        # Opening: erosion followed by dilation
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, self.morph_kernel, iterations=1)
        # Dilation to close small gaps
        fg_mask = cv2.dilate(fg_mask, self.morph_kernel, iterations=1)

        # Step 4: Find contours
        contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        logger.debug(f"Background subtraction: found {len(contours)} raw contours")

        # Step 5: Filter by minimum area and get bounding boxes
        # Also filter out full-frame regions (light changes) per B7 optimization
        frame_area = frame_width * frame_height
        max_region_area = frame_area * 0.8  # Reject regions >80% of frame
        valid_bboxes = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area >= self.min_contour_area:
                # Skip full-frame regions (lighting changes, not actual motion)
                if area > max_region_area:
                    logger.debug(
                        f"Skipping full-frame motion region (lighting change): "
                        f"area={area} pixels ({area/frame_area*100:.1f}% of frame)"
                    )
                    continue

                x, y, w, h = cv2.boundingRect(contour)
                # Validate coordinates per FR-022
                if x >= 0 and y >= 0 and w > 0 and h > 0:
                    valid_bboxes.append((x, y, w, h, area))
                else:
                    logger.warning(
                        f"Invalid motion region detected: x={x}, y={y}, w={w}, h={h}. "
                        "Rejecting per FR-022."
                    )

        if not valid_bboxes:
            logger.debug("No valid motion regions after filtering")
            return []

        logger.debug(f"After filtering: {len(valid_bboxes)} valid regions (min_area={self.min_contour_area})")

        # Step 6: Merge nearby contours by distance
        merged_bboxes = self._merge_nearby_bboxes(valid_bboxes)
        logger.debug(f"After merging: {len(merged_bboxes)} regions (distance_threshold={self.merge_distance_threshold})")

        # Step 7: Apply NMS to remove overlapping boxes
        nms_bboxes = self._apply_nms(merged_bboxes)
        logger.debug(f"After NMS: {len(nms_bboxes)} regions (iou_threshold={self.nms_iou_threshold})")

        # Step 8: Add 15% padding with boundary clipping per FR-004
        motion_regions = []
        for (x, y, w, h, area, merged_count) in nms_bboxes:
            # Calculate 15% padding based on max dimension per FR-004
            padding = int(max(w, h) * 0.15)

            # Apply padding and clip to frame boundaries
            x_padded = max(0, x - padding)
            y_padded = max(0, y - padding)
            w_padded = min(frame_width - x_padded, w + 2 * padding)
            h_padded = min(frame_height - y_padded, h + 2 * padding)

            motion_regions.append(
                MotionRegion(
                    bounding_box=(x_padded, y_padded, w_padded, h_padded),
                    area=area,
                    timestamp=timestamp,
                    merged_count=merged_count
                )
            )

        # T091: False positive rate monitoring
        self._frame_count += 1
        has_motion = len(motion_regions) > 0
        self._motion_window.append(1 if has_motion else 0)

        # Check false positive rate every N frames
        if self._frame_count - self._last_fps_check >= self._fps_check_interval:
            self._last_fps_check = self._frame_count
            if len(self._motion_window) > 0:
                motion_frames = sum(self._motion_window)
                total_frames = len(self._motion_window)
                motion_rate = motion_frames / total_frames

                # Warn if >50% of frames have motion (possible false positive issue)
                if motion_rate > 0.50:
                    logger.warning(
                        f"High motion detection rate: {motion_rate*100:.1f}% of frames have motion "
                        f"(threshold: 50%). This may indicate background subtractor misconfiguration, "
                        f"constant scene changes, or camera instability. "
                        f"Motion frames: {motion_frames}/{total_frames}"
                    )

        logger.info(f"Motion detection complete: {len(motion_regions)} regions extracted")
        return motion_regions

    def _merge_nearby_bboxes(
        self,
        bboxes: List[Tuple[int, int, int, int, int]]
    ) -> List[Tuple[int, int, int, int, int, int]]:
        """
        Merge nearby bounding boxes based on distance threshold.

        Args:
            bboxes: List of (x, y, w, h, area) tuples

        Returns:
            List of (x, y, w, h, area, merged_count) tuples
        """
        if not bboxes:
            return []

        merged = []
        used = [False] * len(bboxes)

        for i in range(len(bboxes)):
            if used[i]:
                continue

            x1, y1, w1, h1, area1 = bboxes[i]
            cx1, cy1 = x1 + w1 / 2, y1 + h1 / 2
            merged_count = 1
            merged_area = area1

            # Find all nearby boxes and merge them
            for j in range(i + 1, len(bboxes)):
                if used[j]:
                    continue

                x2, y2, w2, h2, area2 = bboxes[j]
                cx2, cy2 = x2 + w2 / 2, y2 + h2 / 2

                # Check if centers are within merge distance
                distance = np.sqrt((cx1 - cx2)**2 + (cy1 - cy2)**2)
                if distance <= self.merge_distance_threshold:
                    # Merge bounding boxes
                    x1 = min(x1, x2)
                    y1 = min(y1, y2)
                    x1_max = max(x1 + w1, x2 + w2)
                    y1_max = max(y1 + h1, y2 + h2)
                    w1 = x1_max - x1
                    h1 = y1_max - y1

                    # Update center for next iteration
                    cx1, cy1 = x1 + w1 / 2, y1 + h1 / 2

                    merged_count += 1
                    merged_area += area2
                    used[j] = True

            merged.append((x1, y1, w1, h1, merged_area, merged_count))
            used[i] = True

        return merged

    def _apply_nms(
        self,
        bboxes: List[Tuple[int, int, int, int, int, int]]
    ) -> List[Tuple[int, int, int, int, int, int]]:
        """
        Apply Non-Maximum Suppression to remove overlapping boxes.

        Args:
            bboxes: List of (x, y, w, h, area, merged_count) tuples

        Returns:
            List of (x, y, w, h, area, merged_count) tuples after NMS
        """
        if not bboxes:
            return []

        # Convert to [x1, y1, x2, y2] format for IoU calculation
        boxes = np.array([
            [x, y, x + w, y + h, area, merged_count]
            for (x, y, w, h, area, merged_count) in bboxes
        ])

        # Sort by area (larger boxes first)
        indices = np.argsort(boxes[:, 4])[::-1]

        keep = []
        while len(indices) > 0:
            i = indices[0]
            keep.append(i)

            if len(indices) == 1:
                break

            # Compute IoU with remaining boxes
            ious = self._compute_iou(boxes[i], boxes[indices[1:]])

            # Keep only boxes with IoU below threshold
            indices = indices[1:][ious < self.nms_iou_threshold]

        # Convert back to (x, y, w, h, area, merged_count) format
        result = []
        for i in keep:
            x1, y1, x2, y2, area, merged_count = boxes[i]
            result.append((int(x1), int(y1), int(x2 - x1), int(y2 - y1), int(area), int(merged_count)))

        return result

    def _compute_iou(
        self,
        box: np.ndarray,
        boxes: np.ndarray
    ) -> np.ndarray:
        """
        Compute IoU between one box and multiple boxes.

        Args:
            box: Single box [x1, y1, x2, y2, area, merged_count]
            boxes: Multiple boxes (N, 6) array

        Returns:
            IoU scores array (N,)
        """
        # Intersection coordinates
        x1 = np.maximum(box[0], boxes[:, 0])
        y1 = np.maximum(box[1], boxes[:, 1])
        x2 = np.minimum(box[2], boxes[:, 2])
        y2 = np.minimum(box[3], boxes[:, 3])

        # Intersection area
        intersection = np.maximum(0, x2 - x1) * np.maximum(0, y2 - y1)

        # Union area
        box_area = (box[2] - box[0]) * (box[3] - box[1])
        boxes_area = (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1])
        union = box_area + boxes_area - intersection

        # IoU
        iou = intersection / (union + 1e-6)
        return iou

    def reset(self):
        """
        Reset background subtractor history.

        Useful when camera view changes significantly or stream is restarted.
        """
        # OpenCV MOG2 doesn't have a direct reset, so we recreate the subtractor
        history = self.bg_subtractor.getHistory()
        var_threshold = self.bg_subtractor.getVarThreshold()
        detect_shadows = self.bg_subtractor.getDetectShadows()

        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=history,
            varThreshold=var_threshold,
            detectShadows=detect_shadows
        )

        logger.info("MotionDetector reset: background model cleared")


class ObjectTracker:
    """SORT-style object tracker with Kalman filtering and IoU matching."""

    def __init__(
        self,
        max_age: int = 30,
        min_hits: int = 3,
        iou_threshold: float = 0.3,
        max_tracks: int = 15
    ):
        """
        Initialize object tracker.

        Args:
            max_age: Maximum frames without detection before deleting track (30 frames at 5 FPS = 6 seconds)
            min_hits: Minimum detection matches to confirm track (3 detections)
            iou_threshold: Minimum IoU for detection-to-track matching
            max_tracks: Maximum number of tracked objects per stream (T082: memory limit enforcement)
                       Reduced from 50 to 15 for single-camera deployments to prevent duplicate track overflow
        """
        self.tracks: List[TrackedObject] = []
        self.max_age = max_age
        self.min_hits = min_hits
        self.iou_threshold = iou_threshold
        self.max_tracks = max_tracks
        self.frame_count = 0

        # Internal Kalman trackers (not serialized)
        self._kalman_trackers: dict = {}  # {track_id: KalmanTracker}

        # T080: Track ID switching rate monitoring (rolling 1-minute window)
        from collections import deque
        self._switching_window = deque(maxlen=300)  # 300 frames = 60s at 5 FPS
        self._last_switching_check = 0
        self._switching_check_interval = 50  # Check every 50 frames (10 seconds)

        logger.info(
            f"ObjectTracker initialized: max_age={max_age}, "
            f"min_hits={min_hits}, iou_threshold={iou_threshold}, "
            f"max_tracks={max_tracks}"
        )

    def update(
        self,
        detections: List[Tuple[Tuple[int, int, int, int], str, float]],
        frame_count: int
    ) -> List[TrackedObject]:
        """
        Update tracker with new detections for current frame.

        Args:
            detections: List of (bbox, class_name, confidence) tuples
                       where bbox is (x, y, width, height)
            frame_count: Current frame number

        Returns:
            List of TrackedObject instances (all states)
        """
        self.frame_count = frame_count
        logger.debug(f"ObjectTracker update: frame={frame_count}, detections={len(detections)}")

        # Step 1: Predict all existing tracks using Kalman filter
        predicted_bboxes = []
        for track in self.tracks:
            kalman = self._kalman_trackers.get(str(track.id))
            if kalman:
                kalman.predict()
                predicted_bbox = kalman.get_bbox()
                predicted_bboxes.append(predicted_bbox)
                # Update track bounding box with prediction
                track.bounding_box = predicted_bbox
                track.velocity = kalman.get_velocity()
            else:
                # No Kalman tracker (shouldn't happen, but handle gracefully)
                predicted_bboxes.append(track.bounding_box)

        # Step 2: Compute IoU cost matrix between detections and predictions
        detection_bboxes = [det[0] for det in detections] if detections else []
        if detection_bboxes and predicted_bboxes:
            iou_matrix = compute_iou_matrix(detection_bboxes, predicted_bboxes)
            # Convert IoU to cost (1 - IoU, lower is better)
            cost_matrix = 1.0 - iou_matrix
        else:
            cost_matrix = np.array([])

        # Step 3: Hungarian matching to associate detections with tracks
        matched_det_indices = []
        matched_track_indices = []
        if cost_matrix.size > 0:
            det_indices, track_indices = hungarian_matching(cost_matrix)

            # Filter matches by IoU threshold
            for det_idx, track_idx in zip(det_indices, track_indices):
                if iou_matrix[det_idx, track_idx] >= self.iou_threshold:
                    matched_det_indices.append(det_idx)
                    matched_track_indices.append(track_idx)

        logger.debug(f"Matching: {len(matched_det_indices)} matches, {len(detections)} detections, {len(self.tracks)} tracks")

        # Step 4: Update matched tracks with detections
        for det_idx, track_idx in zip(matched_det_indices, matched_track_indices):
            det_bbox, det_class, det_conf = detections[det_idx]
            track = self.tracks[track_idx]

            # Update Kalman filter with measurement
            kalman = self._kalman_trackers.get(str(track.id))
            if kalman:
                kalman.update(det_bbox)
                updated_bbox = kalman.get_bbox()
                updated_velocity = kalman.get_velocity()
            else:
                updated_bbox = det_bbox
                updated_velocity = (0.0, 0.0)

            # Update track attributes
            track.bounding_box = updated_bbox
            track.confidence = det_conf
            track.velocity = updated_velocity
            track.last_seen_frame = frame_count
            track.frames_since_detection = 0
            track.hits += 1
            track.age += 1

            # Update bounding box history (keep last 50)
            track.bounding_box_history.append(updated_bbox)
            if len(track.bounding_box_history) > 50:
                track.bounding_box_history = track.bounding_box_history[-50:]

            # Check if stationary (compare movement over last 50 frames)
            if len(track.bounding_box_history) >= 10:
                # Calculate movement from 10 frames ago
                old_bbox = track.bounding_box_history[-10]
                old_cx, old_cy = old_bbox[0] + old_bbox[2] / 2, old_bbox[1] + old_bbox[3] / 2
                new_cx, new_cy = updated_bbox[0] + updated_bbox[2] / 2, updated_bbox[1] + updated_bbox[3] / 2
                movement = np.sqrt((new_cx - old_cx)**2 + (new_cy - old_cy)**2)

                # Threshold: 5 pixels movement over 10 frames (2 seconds at 5 FPS)
                if movement < 5:
                    track.frames_stationary += 1
                else:
                    track.frames_stationary = 0

            # Update state based on history
            track.update_state()

        # Step 5: Create new tracks from unmatched detections
        unmatched_det_indices = set(range(len(detections))) - set(matched_det_indices)
        for det_idx in unmatched_det_indices:
            det_bbox, det_class, det_conf = detections[det_idx]

            # T082: Enforce memory limit - evict oldest LOST track if at max_tracks
            if len(self.tracks) >= self.max_tracks:
                # Find oldest LOST track to evict
                lost_tracks = [(i, t) for i, t in enumerate(self.tracks) if t.state == ObjectState.LOST]

                if lost_tracks:
                    # Sort by age (oldest first) and evict the oldest
                    lost_tracks.sort(key=lambda x: x[1].age, reverse=True)
                    evict_idx, evict_track = lost_tracks[0]

                    logger.warning(
                        f"Memory limit reached ({self.max_tracks} tracks). "
                        f"Evicting oldest LOST track: id={evict_track.id.hex[:8]}, age={evict_track.age}"
                    )

                    # Clean up Kalman tracker
                    kalman_id = str(evict_track.id)
                    if kalman_id in self._kalman_trackers:
                        self._kalman_trackers[kalman_id].cleanup()  # Explicit resource cleanup
                        del self._kalman_trackers[kalman_id]
                    del self.tracks[evict_idx]
                else:
                    # No LOST tracks to evict, skip creating new track
                    logger.warning(
                        f"Memory limit reached ({self.max_tracks} tracks) with no LOST tracks to evict. "
                        f"Skipping new track for {det_class}"
                    )
                    continue

            # Create new track
            new_track = TrackedObject(
                class_name=det_class,
                confidence=det_conf,
                bounding_box=det_bbox,
                last_seen_frame=frame_count,
                hits=1,
                age=1,
                state=ObjectState.TENTATIVE
            )

            # Create Kalman tracker for this new track
            kalman = KalmanTracker(det_bbox)
            self._kalman_trackers[str(new_track.id)] = kalman

            self.tracks.append(new_track)
            logger.info(f"New track created: id={new_track.id.hex[:8]}, class={det_class}, bbox={det_bbox}")

        # Step 6: Update unmatched tracks (prediction-only, increment age)
        unmatched_track_indices = set(range(len(self.tracks))) - set(matched_track_indices)
        for track_idx in unmatched_track_indices:
            track = self.tracks[track_idx]
            track.frames_since_detection += 1
            track.age += 1
            track.update_state()

        # Step 7: Delete old tracks (max_age exceeded)
        tracks_to_delete = []
        for i, track in enumerate(self.tracks):
            if track.frames_since_detection > self.max_age:
                tracks_to_delete.append(i)
                logger.info(f"Track deleted: id={track.id.hex[:8]}, age={track.age}, no detection for {track.frames_since_detection} frames")

        # Remove in reverse order to preserve indices
        for i in sorted(tracks_to_delete, reverse=True):
            track = self.tracks[i]
            # Clean up Kalman tracker
            kalman_id = str(track.id)
            if kalman_id in self._kalman_trackers:
                self._kalman_trackers[kalman_id].cleanup()  # Explicit resource cleanup
                del self._kalman_trackers[kalman_id]
            del self.tracks[i]

        # T080: Track ID switching rate monitoring
        num_new_tracks = len(unmatched_det_indices)
        num_deleted_tracks = len(tracks_to_delete)
        switching_events = num_new_tracks + num_deleted_tracks
        self._switching_window.append(switching_events)

        # Check switching rate every N frames
        if frame_count - self._last_switching_check >= self._switching_check_interval:
            self._last_switching_check = frame_count
            if len(self._switching_window) > 0:
                # Calculate switching rate over the window
                total_switches = sum(self._switching_window)
                window_frames = len(self._switching_window)
                avg_tracks = len(self.tracks) if self.tracks else 1  # Avoid division by zero

                # Switching rate = total switches / (window frames * avg tracks)
                switching_rate = total_switches / (window_frames * avg_tracks)

                # Warn if switching rate exceeds 5% (0.05)
                if switching_rate > 0.05:
                    logger.warning(
                        f"High track ID switching rate detected: {switching_rate*100:.1f}% "
                        f"(threshold: 5%). Total switches: {total_switches} over {window_frames} frames. "
                        f"This may indicate tracking instability or rapid scene changes."
                    )

        logger.debug(f"ObjectTracker: {len(self.tracks)} active tracks after update")
        return self.tracks

    def reset(self):
        """Reset tracker state (clear all tracks)."""
        # Clean up all Kalman trackers before clearing
        for kalman in self._kalman_trackers.values():
            kalman.cleanup()

        self.tracks.clear()
        self._kalman_trackers.clear()
        self.frame_count = 0
        logger.info("ObjectTracker reset: all tracks cleared")

    def get_active_objects(self) -> List[TrackedObject]:
        """Get all tracked objects that are not stationary.

        Returns objects in TENTATIVE, ACTIVE, and LOST states.
        Used for identifying objects that need full-frequency detection.

        Returns:
            List of TrackedObject instances with state != STATIONARY
        """
        from ..models.motion import ObjectState
        return [track for track in self.tracks if track.state != ObjectState.STATIONARY]

    def get_stationary_objects(self) -> List[TrackedObject]:
        """Get all tracked objects that are stationary.

        Returns objects in STATIONARY state that should receive
        reduced-frequency detection (1 frame per 50 = every 10 seconds at 5 FPS).

        Returns:
            List of TrackedObject instances with state == STATIONARY
        """
        from ..models.motion import ObjectState
        return [track for track in self.tracks if track.state == ObjectState.STATIONARY]
