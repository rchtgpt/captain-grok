"""
Video stream handler for drone camera feed.
Supports both OpenCV window display and MJPEG streaming.

Features:
- Real-time face detection with bounding boxes
- Session video recording
- Tailing overlay when following a target

NOTE: OpenCV GUI operations (imshow, namedWindow) MUST run on the main thread on macOS.
This module handles frame capture in a background thread for web streaming,
but window display should be handled separately on the main thread if needed.
"""

import cv2
import threading
import time
from typing import Optional, List, Dict, Any, TYPE_CHECKING
import numpy as np

from core.logger import get_logger
from core.events import EventBus
from core.exceptions import VideoStreamError

if TYPE_CHECKING:
    from drone.recorder import SessionRecorder
    from core.tailing import TailingController

log = get_logger('video')


class VideoStream:
    """
    Manages the drone's video stream with face detection overlay.
    
    Features:
    - Captures frames in background thread for web streaming
    - Draws bounding boxes around ALL detected faces
    - Highlights target faces (yellow) and tailing target (green)
    - Records clean video (no overlays) to session files
    """
    
    # Face detection settings
    FACE_DETECTION_INTERVAL = 5  # Run detection every N frames (~6 FPS)
    
    # Bounding box colors (BGR format)
    COLOR_UNKNOWN_FACE = (255, 100, 100)   # Blue - unknown face
    COLOR_TARGET_FACE = (0, 255, 255)       # Yellow - registered target
    COLOR_TAILING_FACE = (0, 255, 0)        # Green - actively tailing
    COLOR_FOUND_FACE = (0, 255, 0)          # Green - just found
    
    def __init__(self, drone, event_bus: EventBus, show_window: bool = False):
        """
        Initialize video stream.
        
        Args:
            drone: The drone object (Tello or MockDrone)
            event_bus: Event bus for publishing frame events
            show_window: Whether to show OpenCV window (disabled by default - requires main thread)
        """
        self.drone = drone
        self.event_bus = event_bus
        self.show_window_enabled = show_window
        
        # State
        self.running = False
        self.window_active = False
        self.stream_initialized = False
        
        # Frame buffer
        self.current_frame: Optional[np.ndarray] = None  # Frame WITH overlays for display
        self.clean_frame: Optional[np.ndarray] = None     # Frame WITHOUT overlays for vision AI
        self.frame_lock = threading.Lock()
        self.frame_read = None  # Cached frame reader
        
        # Thread
        self.thread: Optional[threading.Thread] = None
        
        # Face detection cache (persists between frames for smooth display)
        self._cached_faces: List[Dict[str, Any]] = []
        self._face_service = None  # Lazy loaded
        self._target_manager = None  # Lazy loaded
        
        # Recorder integration (set via set_recorder)
        self._recorder: Optional['SessionRecorder'] = None
        
        # Tailing controller (set via set_tailing_controller)
        self._tailing_controller: Optional['TailingController'] = None
        self._tailing_bbox: Optional[Dict[str, float]] = None  # Current tailing bbox
        
        log.info("VideoStream initialized with face detection overlay")
    
    def set_recorder(self, recorder: 'SessionRecorder') -> None:
        """Set the session recorder for video capture."""
        self._recorder = recorder
        log.info("Session recorder attached to video stream")
    
    def set_tailing_controller(self, controller: 'TailingController') -> None:
        """Set the tailing controller for target tracking."""
        self._tailing_controller = controller
        log.info("Tailing controller attached to video stream")
    
    def _get_face_service(self):
        """Lazy load face recognition service."""
        if self._face_service is None:
            try:
                from core.face_recognition_service import get_face_service
                self._face_service = get_face_service()
            except Exception as e:
                log.warning(f"Could not load face service: {e}")
        return self._face_service
    
    def _get_target_manager(self):
        """Lazy load target manager."""
        if self._target_manager is None:
            try:
                from core.targets import get_target_manager
                self._target_manager = get_target_manager()
            except Exception as e:
                log.warning(f"Could not load target manager: {e}")
        return self._target_manager
    
    def start(self) -> None:
        """Start the video stream."""
        if self.running:
            log.warning("Video stream already running")
            return
        
        try:
            log.info("Starting video stream...")
            self.drone.streamon()
            time.sleep(2)  # Let stream stabilize
            
            # Initialize frame reader on main thread
            try:
                self.frame_read = self.drone.get_frame_read()
                self.stream_initialized = True
                log.info("Frame reader initialized")
            except Exception as e:
                log.warning(f"Could not initialize frame reader: {e}")
                self.stream_initialized = False
            
            self.running = True
            self.thread = threading.Thread(target=self._stream_loop, daemon=True)
            self.thread.start()
            
            log.success("Video stream started")
        
        except Exception as e:
            log.error(f"Failed to start video stream: {e}")
            raise VideoStreamError(f"Could not start video stream: {e}")
    
    def stop(self) -> None:
        """Stop the video stream."""
        if not self.running:
            return
        
        log.info("Stopping video stream...")
        self.running = False
        
        if self.thread:
            self.thread.join(timeout=3)
        
        try:
            self.drone.streamoff()
        except:
            pass
        
        # Clean up window if it was active (must be called from main thread)
        if self.window_active:
            try:
                cv2.destroyAllWindows()
            except:
                pass
            self.window_active = False
        
        self.frame_read = None
        log.info("Video stream stopped")
    
    def run_display_loop(self, window_name: str = "Grok-Pilot Camera") -> None:
        """
        Run OpenCV display loop on the MAIN THREAD.
        
        This method blocks and should be called from the main thread
        if you want to display video in an OpenCV window.
        Press 'q' to exit the display loop.
        
        For server mode, use get_frame() or the MJPEG endpoint instead.
        
        Args:
            window_name: Name for the OpenCV window
        """
        if not self.running:
            log.warning("Cannot show window - stream not running")
            return
        
        try:
            cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
            cv2.resizeWindow(window_name, 960, 720)
            self.window_active = True
            log.info(f"Display window '{window_name}' opened")
        except Exception as e:
            log.error(f"Could not create window: {e}")
            return
        
        try:
            while self.running:
                frame = self.get_frame()
                if frame is not None:
                    cv2.imshow(window_name, frame)
                
                # Check for 'q' key to quit
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    log.info("User closed video window")
                    break
        finally:
            cv2.destroyAllWindows()
            self.window_active = False
    
    def _stream_loop(self) -> None:
        """
        Main loop for capturing frames.
        
        Pipeline:
        1. Capture frame from drone
        2. Color correction
        3. Store clean frame (for AI / recording)
        4. Run face detection (every N frames)
        5. Draw face bounding boxes
        6. Add status overlay (battery, height)
        7. Store display frame
        8. Write to recorder (clean frame)
        """
        frame_count = 0
        error_count = 0
        max_errors_before_log = 50
        consecutive_errors = 0
        
        log.info("Frame capture loop started")
        
        while self.running:
            try:
                # Use cached frame reader, or get a new one
                if self.frame_read is None:
                    try:
                        self.frame_read = self.drone.get_frame_read()
                    except Exception as e:
                        consecutive_errors += 1
                        if consecutive_errors <= 3:
                            log.warning(f"Could not get frame reader: {e}")
                        time.sleep(0.5)
                        continue
                
                # Get frame from the reader
                frame = self.frame_read.frame
                
                # Convert from RGB to BGR (drone sends RGB, OpenCV expects BGR)
                if frame is not None:
                    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                
                if frame is None:
                    time.sleep(0.05)
                    consecutive_errors += 1
                    if consecutive_errors > 30:
                        log.warning("No frames received for extended period")
                        consecutive_errors = 0
                    continue
                
                # Reset error counts on success
                error_count = 0
                consecutive_errors = 0
                
                # Resize frame if needed
                try:
                    if frame.shape[0] != 720 or frame.shape[1] != 960:
                        frame = cv2.resize(frame, (960, 720))
                except Exception:
                    pass
                
                # Apply color correction to fix blue tint
                frame = self._correct_colors(frame)
                
                # Store clean frame for vision AI (NO overlays)
                with self.frame_lock:
                    self.clean_frame = frame.copy()
                
                # Write clean frame to recorder
                if self._recorder and self._recorder.is_recording:
                    self._recorder.write_frame(frame)
                
                # Run face detection periodically
                frame_count += 1
                if frame_count % self.FACE_DETECTION_INTERVAL == 0:
                    self._detect_faces(frame)
                    
                    # Process frame for tailing (if active)
                    if self._tailing_controller and self._tailing_controller.active:
                        tailing_result = self._tailing_controller.process_frame(frame)
                        if tailing_result and tailing_result.get('bbox'):
                            # Update tailing bbox for overlay
                            self._tailing_bbox = tailing_result.get('bbox')
                        elif tailing_result and tailing_result.get('gave_up'):
                            self._tailing_bbox = None
                
                # Build display frame with overlays
                display_frame = frame.copy()
                
                # Draw face bounding boxes
                display_frame = self._draw_face_boxes(display_frame)
                
                # Add tailing indicator if active
                display_frame = self._add_tailing_overlay(display_frame)
                
                # Add status overlay (battery, height, branding)
                display_frame = self._add_overlay(display_frame)
                
                # Update current frame (thread-safe)
                with self.frame_lock:
                    self.current_frame = display_frame
                
                # Publish clean frame event for vision processing (every 10 frames)
                if frame_count % 10 == 0:
                    self.event_bus.publish('vision.frame', self.clean_frame)
                
                # Control frame rate (~30 FPS)
                time.sleep(0.033)
            
            except Exception as e:
                error_count += 1
                consecutive_errors += 1
                
                if error_count == 1 or error_count % max_errors_before_log == 0:
                    log.warning(f"Frame capture error: {e} (total: {error_count})")
                
                time.sleep(0.1)
                
                if consecutive_errors >= 10:
                    log.warning("Resetting frame reader due to repeated errors")
                    self.frame_read = None
                    consecutive_errors = 0
        
        log.info("Frame capture loop stopped")
    
    def _detect_faces(self, frame: np.ndarray) -> None:
        """
        Detect faces in frame and match against registered targets.
        Updates self._cached_faces for overlay drawing.
        """
        face_service = self._get_face_service()
        target_manager = self._get_target_manager()
        
        if face_service is None or not face_service.is_available:
            self._cached_faces = []
            return
        
        try:
            # Detect all faces in frame
            detections = face_service.extract_all_faces(frame)
            
            faces = []
            for detection in detections:
                face_info = {
                    'bbox': detection.bbox,
                    'target_id': None,
                    'target_name': None,
                    'is_tailing': False,
                    'confidence': 0.0
                }
                
                # Try to match against registered targets
                if target_manager and detection.embedding:
                    targets = target_manager.get_all_targets()
                    for target in targets:
                        if target.face_embeddings:
                            # Check if this face matches the target
                            for target_embedding in target.face_embeddings:
                                distance = face_service.compare_embeddings(
                                    detection.embedding, 
                                    target_embedding
                                )
                                if distance < 0.5:  # Match threshold
                                    face_info['target_id'] = target.id
                                    face_info['target_name'] = target.name
                                    face_info['confidence'] = 1.0 - distance
                                    
                                    # Check if this is the tailing target
                                    if self._tailing_controller and self._tailing_controller.active:
                                        if self._tailing_controller.target_id == target.id:
                                            face_info['is_tailing'] = True
                                    break
                        if face_info['target_id']:
                            break
                
                faces.append(face_info)
            
            self._cached_faces = faces
            
        except Exception as e:
            log.debug(f"Face detection error: {e}")
            # Keep cached faces on error for smooth display
    
    def _draw_face_boxes(self, frame: np.ndarray) -> np.ndarray:
        """Draw bounding boxes around all detected faces."""
        h, w = frame.shape[:2]
        
        for face in self._cached_faces:
            bbox = face['bbox']
            
            # Convert normalized coordinates to pixels
            x1 = int(bbox['x'] * w)
            y1 = int(bbox['y'] * h)
            x2 = int((bbox['x'] + bbox['width']) * w)
            y2 = int((bbox['y'] + bbox['height']) * h)
            
            # Choose color based on status
            if face['is_tailing']:
                color = self.COLOR_TAILING_FACE
                label = f"TAILING: {face['target_name']}"
                thickness = 3
            elif face['target_name']:
                color = self.COLOR_TARGET_FACE
                label = f"{face['target_name']} ({face['confidence']:.0%})"
                thickness = 2
            else:
                color = self.COLOR_UNKNOWN_FACE
                label = None
                thickness = 2
            
            # Draw bounding box
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness)
            
            # Draw label if present
            if label:
                # Background for text
                label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
                cv2.rectangle(
                    frame,
                    (x1, y1 - label_size[1] - 10),
                    (x1 + label_size[0] + 10, y1),
                    color,
                    -1  # Filled
                )
                # Text
                cv2.putText(
                    frame,
                    label,
                    (x1 + 5, y1 - 5),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 0, 0),  # Black text on colored background
                    2
                )
        
        return frame
    
    def _add_tailing_overlay(self, frame: np.ndarray) -> np.ndarray:
        """Add tailing status indicator when following someone."""
        if not self._tailing_controller or not self._tailing_controller.active:
            return frame
        
        h, w = frame.shape[:2]
        target_name = self._tailing_controller.target_name or "Unknown"
        
        # Draw "TAILING MODE" indicator at bottom
        label = f"TAILING: {target_name}"
        label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)[0]
        
        # Background bar
        cv2.rectangle(
            frame,
            (0, h - 40),
            (w, h),
            self.COLOR_TAILING_FACE,
            -1
        )
        
        # Text centered
        text_x = (w - label_size[0]) // 2
        cv2.putText(
            frame,
            label,
            (text_x, h - 12),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 0, 0),
            2
        )
        
        return frame
    
    def _correct_colors(self, frame: np.ndarray) -> np.ndarray:
        """
        Correct blue color tint from Tello camera.
        """
        try:
            corrected = frame.copy()
            
            # Blue channel - Reduce by 12%
            corrected[:, :, 0] = np.clip(corrected[:, :, 0] * 0.88, 0, 255).astype(np.uint8)
            # Green channel - Increase by 5%
            corrected[:, :, 1] = np.clip(corrected[:, :, 1] * 1.05, 0, 255).astype(np.uint8)
            # Red channel - Increase by 15%
            corrected[:, :, 2] = np.clip(corrected[:, :, 2] * 1.15, 0, 255).astype(np.uint8)
            
            return corrected
        
        except Exception as e:
            log.debug(f"Color correction failed: {e}")
            return frame
    
    def _add_overlay(self, frame: np.ndarray) -> np.ndarray:
        """Add status overlay (battery, height, branding)."""
        try:
            # Get drone status
            battery = self.drone.get_battery()
            
            # Battery color
            if battery > 50:
                color = (0, 255, 0)  # Green
            elif battery > 20:
                color = (0, 255, 255)  # Yellow
            else:
                color = (0, 0, 255)  # Red
            
            # Battery indicator
            cv2.putText(
                frame,
                f"Battery: {battery}%",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                color,
                2
            )
            
            # Height if flying
            if hasattr(self.drone, 'get_height'):
                try:
                    height = self.drone.get_height()
                    cv2.putText(
                        frame,
                        f"Height: {height}cm",
                        (10, 60),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        (255, 255, 255),
                        2
                    )
                except:
                    pass
            
            # Recording indicator
            if self._recorder and self._recorder.is_recording:
                cv2.circle(frame, (frame.shape[1] - 30, 30), 10, (0, 0, 255), -1)  # Red dot
                cv2.putText(
                    frame,
                    "REC",
                    (frame.shape[1] - 70, 35),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 0, 255),
                    2
                )
            
            # Branding
            cv2.putText(
                frame,
                "GROK-PILOT",
                (frame.shape[1] - 200, 60 if self._recorder and self._recorder.is_recording else 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 255),
                2
            )
        
        except Exception as e:
            log.debug(f"Error adding overlay: {e}")
        
        return frame
    
    def get_frame(self) -> Optional[np.ndarray]:
        """Get the current display frame (with overlays)."""
        with self.frame_lock:
            if self.current_frame is not None:
                return self.current_frame.copy()
            return None
    
    def capture_snapshot(self) -> Optional[np.ndarray]:
        """Capture a clean snapshot WITHOUT overlays for vision AI."""
        with self.frame_lock:
            if self.clean_frame is not None:
                return self.clean_frame.copy()
            return None
    
    def get_cached_faces(self) -> List[Dict[str, Any]]:
        """Get the current cached face detections."""
        return self._cached_faces.copy()
    
    def show_window(self) -> None:
        """Enable the OpenCV window (must be main thread on macOS)."""
        if not self.running:
            log.warning("Cannot show window - stream not running")
            return
        
        self.show_window_enabled = True
        if not self.window_active:
            try:
                cv2.namedWindow("Grok-Pilot Camera", cv2.WINDOW_NORMAL)
                cv2.resizeWindow("Grok-Pilot Camera", 960, 720)
                self.window_active = True
            except Exception as e:
                log.error(f"Cannot create window (must be main thread): {e}")
    
    def hide_window(self) -> None:
        """Disable the OpenCV window (must be main thread on macOS)."""
        self.show_window_enabled = False
        if self.window_active:
            try:
                cv2.destroyAllWindows()
            except:
                pass
            self.window_active = False
    
    @property
    def is_running(self) -> bool:
        """Check if stream is running."""
        return self.running
