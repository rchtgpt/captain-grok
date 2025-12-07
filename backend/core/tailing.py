"""
Tailing Controller - Real-time person following.

After finding a target, the tailing controller:
1. Continuously tracks their face in the video stream
2. Rotates the drone to keep them centered in frame
3. Maintains a bounding box overlay on the video
4. Can be stopped at any time

Rotation-only following (no forward/back movement for safety).
"""

import threading
import time
from dataclasses import dataclass
from typing import Optional, Dict, Any, TYPE_CHECKING
import numpy as np

from core.logger import get_logger
from drone.safety import ABORT_FLAG

if TYPE_CHECKING:
    from drone.controller import DroneController
    from core.face_recognition_service import FaceRecognitionService
    from core.targets import TargetManager, Target

log = get_logger('tailing')


@dataclass
class TailingStatus:
    """Current tailing status."""
    active: bool
    target_id: Optional[str]
    target_name: Optional[str]
    bbox: Optional[Dict[str, float]]
    confidence: float
    last_seen: float  # Timestamp
    frames_tracked: int
    frames_lost: int
    rotation_queued: int  # Last rotation command queued


class TailingController:
    """
    Controls real-time person following via rotation.
    
    When active:
    - Processes each video frame to locate target
    - Calculates if drone needs to rotate to center target
    - Queues rotation commands (non-blocking)
    - Updates bbox for video overlay
    
    Rotation Logic:
    - If target is left of center → rotate counter-clockwise
    - If target is right of center → rotate clockwise
    - Dead zone in center to prevent oscillation
    """
    
    # Frame geometry
    FRAME_WIDTH = 960
    FRAME_CENTER_X = 480  # Center of frame
    
    # Rotation thresholds
    DEAD_ZONE = 100  # Pixels from center - no rotation
    SLOW_ZONE = 200  # Pixels from center - slow rotation
    
    # Rotation speeds (degrees)
    ROTATION_SLOW = 10
    ROTATION_FAST = 20
    
    # Timing
    MIN_ROTATION_INTERVAL = 0.5  # Seconds between rotations
    LOST_TIMEOUT = 3.0  # Seconds before starting re-acquisition
    GIVE_UP_TIMEOUT = 10.0  # Seconds before stopping tailing
    
    def __init__(
        self,
        drone: 'DroneController',
        face_service: 'FaceRecognitionService',
        target_manager: 'TargetManager'
    ):
        self.drone = drone
        self.face_service = face_service
        self.target_manager = target_manager
        
        # State
        self.active = False
        self.target_id: Optional[str] = None
        self.target_name: Optional[str] = None
        self.target: Optional['Target'] = None
        
        # Tracking state
        self.last_bbox: Optional[Dict[str, float]] = None
        self.last_seen: float = 0
        self.last_rotation_time: float = 0
        self.frames_tracked: int = 0
        self.frames_lost: int = 0
        
        # Threading
        self._lock = threading.Lock()
        self._rotation_lock = threading.Lock()  # Prevent concurrent rotations
        
        log.info("TailingController initialized")
    
    def start(self, target_id: str) -> bool:
        """
        Start tailing a target.
        
        Args:
            target_id: ID of target to follow
            
        Returns:
            True if tailing started successfully
        """
        with self._lock:
            if self.active:
                log.warning("Already tailing - stop first")
                return False
            
            # Get target
            target = self.target_manager.get_target(target_id)
            if not target:
                log.error(f"Target not found: {target_id}")
                return False
            
            if not target.face_embeddings:
                log.error(f"Target has no face data: {target.name}")
                return False
            
            self.target_id = target_id
            self.target_name = target.name
            self.target = target
            self.active = True
            
            # Reset tracking state
            self.last_bbox = None
            self.last_seen = time.time()
            self.last_rotation_time = 0
            self.frames_tracked = 0
            self.frames_lost = 0
            
            log.success(f"Started tailing: {target.name}")
            return True
    
    def stop(self) -> None:
        """Stop tailing."""
        with self._lock:
            if not self.active:
                return
            
            name = self.target_name
            self.active = False
            self.target_id = None
            self.target_name = None
            self.target = None
            self.last_bbox = None
            
            log.info(f"Stopped tailing: {name}")
    
    def process_frame(self, frame: np.ndarray) -> Optional[Dict[str, Any]]:
        """
        Process a video frame for tailing.
        Called from the video stream loop.
        
        Args:
            frame: BGR frame from camera
            
        Returns:
            Dict with bbox and status, or None if not tailing
        """
        if not self.active:
            return None
        
        with self._lock:
            if not self.active or not self.target:
                return None
            
            target = self.target
        
        # Check abort
        if ABORT_FLAG.is_set():
            self.stop()
            return None
        
        try:
            # Detect faces in frame
            detections = self.face_service.extract_all_faces(frame)
            
            # Find our target among detections
            target_detection = None
            best_distance = float('inf')
            
            for detection in detections:
                if detection.embedding is None:
                    continue
                
                # Compare against target's embeddings
                for target_embedding in target.face_embeddings:
                    distance = self.face_service.compare_embeddings(
                        detection.embedding,
                        target_embedding
                    )
                    
                    if distance < 0.5 and distance < best_distance:
                        best_distance = distance
                        target_detection = detection
            
            now = time.time()
            
            if target_detection:
                # Target found!
                self.last_bbox = target_detection.bbox
                self.last_seen = now
                self.frames_tracked += 1
                
                # Calculate rotation needed
                rotation = self._calculate_rotation(target_detection.bbox)
                
                # Queue rotation if needed and enough time has passed
                if rotation != 0 and (now - self.last_rotation_time) > self.MIN_ROTATION_INTERVAL:
                    self._queue_rotation(rotation)
                    self.last_rotation_time = now
                
                return {
                    'tracking': True,
                    'bbox': target_detection.bbox,
                    'confidence': 1.0 - best_distance,
                    'rotation_queued': rotation
                }
            
            else:
                # Target not in frame
                self.frames_lost += 1
                time_since_seen = now - self.last_seen
                
                if time_since_seen > self.GIVE_UP_TIMEOUT:
                    log.warning(f"Lost target for {time_since_seen:.1f}s - stopping tailing")
                    self.stop()
                    return {'tracking': False, 'lost': True, 'gave_up': True}
                
                elif time_since_seen > self.LOST_TIMEOUT:
                    # Start slow spin to re-acquire
                    if (now - self.last_rotation_time) > self.MIN_ROTATION_INTERVAL:
                        self._queue_rotation(self.ROTATION_SLOW)
                        self.last_rotation_time = now
                    
                    return {
                        'tracking': False,
                        'searching': True,
                        'bbox': self.last_bbox,  # Keep last known position
                        'time_lost': time_since_seen
                    }
                
                else:
                    # Brief loss - keep last bbox
                    return {
                        'tracking': False,
                        'bbox': self.last_bbox,
                        'time_lost': time_since_seen
                    }
        
        except Exception as e:
            log.error(f"Tailing frame processing error: {e}")
            return None
    
    def _calculate_rotation(self, bbox: Dict[str, float]) -> int:
        """
        Calculate rotation needed to center target.
        
        Args:
            bbox: Bounding box with normalized coordinates
            
        Returns:
            Rotation in degrees (positive = clockwise)
        """
        # Calculate center of face in pixels
        face_center_x = (bbox['x'] + bbox['width'] / 2) * self.FRAME_WIDTH
        
        # Calculate offset from frame center
        offset = face_center_x - self.FRAME_CENTER_X
        
        # Check dead zone
        if abs(offset) < self.DEAD_ZONE:
            return 0
        
        # Determine rotation direction and speed
        if abs(offset) < self.SLOW_ZONE:
            rotation = self.ROTATION_SLOW
        else:
            rotation = self.ROTATION_FAST
        
        # Direction: positive offset = person is right of center = rotate right (CW)
        if offset > 0:
            return rotation
        else:
            return -rotation
    
    def _queue_rotation(self, degrees: int) -> None:
        """
        Queue a rotation command (non-blocking).
        Uses a separate thread to avoid blocking video processing.
        """
        def do_rotation():
            with self._rotation_lock:
                try:
                    if self.active and not ABORT_FLAG.is_set():
                        self.drone.rotate(degrees)
                except Exception as e:
                    log.error(f"Rotation failed: {e}")
        
        # Run in background thread
        thread = threading.Thread(target=do_rotation, daemon=True)
        thread.start()
    
    def get_status(self) -> TailingStatus:
        """Get current tailing status."""
        with self._lock:
            return TailingStatus(
                active=self.active,
                target_id=self.target_id,
                target_name=self.target_name,
                bbox=self.last_bbox,
                confidence=0.0 if not self.last_bbox else 0.9,
                last_seen=self.last_seen,
                frames_tracked=self.frames_tracked,
                frames_lost=self.frames_lost,
                rotation_queued=0
            )
    
    @property
    def is_active(self) -> bool:
        return self.active


# Singleton instance
_tailing_controller: Optional[TailingController] = None
_tailing_lock = threading.Lock()


def get_tailing_controller() -> Optional[TailingController]:
    """Get the singleton TailingController instance."""
    return _tailing_controller


def init_tailing_controller(
    drone: 'DroneController',
    face_service: 'FaceRecognitionService',
    target_manager: 'TargetManager'
) -> TailingController:
    """Initialize the tailing controller."""
    global _tailing_controller
    with _tailing_lock:
        _tailing_controller = TailingController(drone, face_service, target_manager)
        return _tailing_controller
