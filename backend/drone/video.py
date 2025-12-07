"""
Video stream handler for drone camera feed.
Supports both OpenCV window display and MJPEG streaming.

NOTE: OpenCV GUI operations (imshow, namedWindow) MUST run on the main thread on macOS.
This module handles frame capture in a background thread for web streaming,
but window display should be handled separately on the main thread if needed.
"""

import cv2
import threading
import time
from typing import Optional
import numpy as np

from core.logger import get_logger
from core.events import EventBus
from core.exceptions import VideoStreamError


class VideoStream:
    """
    Manages the drone's video stream.
    Captures frames in background thread for web streaming.
    Window display is disabled by default (use main thread display if needed).
    """
    
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
        self.log = get_logger('video')
        
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
    
    def start(self) -> None:
        """Start the video stream."""
        if self.running:
            self.log.warning("Video stream already running")
            return
        
        try:
            self.log.info("Starting video stream...")
            self.drone.streamon()
            time.sleep(2)  # Let stream stabilize (increased from 1s)
            
            # Initialize frame reader on main thread
            try:
                self.frame_read = self.drone.get_frame_read()
                self.stream_initialized = True
                self.log.info("Frame reader initialized")
            except Exception as e:
                self.log.warning(f"Could not initialize frame reader: {e}")
                self.stream_initialized = False
            
            self.running = True
            self.thread = threading.Thread(target=self._stream_loop, daemon=True)
            self.thread.start()
            
            self.log.success("Video stream started")
        
        except Exception as e:
            self.log.error(f"Failed to start video stream: {e}")
            raise VideoStreamError(f"Could not start video stream: {e}")
    
    def stop(self) -> None:
        """Stop the video stream."""
        if not self.running:
            return
        
        self.log.info("Stopping video stream...")
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
        self.log.info("Video stream stopped")
    
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
            self.log.warning("Cannot show window - stream not running")
            return
        
        try:
            cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
            cv2.resizeWindow(window_name, 960, 720)
            self.window_active = True
            self.log.info(f"Display window '{window_name}' opened")
        except Exception as e:
            self.log.error(f"Could not create window: {e}")
            return
        
        try:
            while self.running:
                frame = self.get_frame()
                if frame is not None:
                    cv2.imshow(window_name, frame)
                
                # Check for 'q' key to quit
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    self.log.info("User closed video window")
                    break
        finally:
            cv2.destroyAllWindows()
            self.window_active = False
    
    def _stream_loop(self) -> None:
        """
        Main loop for capturing frames.
        
        NOTE: This runs in a background thread. OpenCV GUI operations
        (imshow, namedWindow, waitKey) are NOT used here because they
        require the main thread on macOS.
        
        For window display, use run_display_loop() on the main thread.
        """
        frame_count = 0
        error_count = 0
        max_errors_before_log = 50  # Reduced logging frequency
        consecutive_errors = 0
        
        self.log.info("Frame capture loop started")
        
        while self.running:
            try:
                # Use cached frame reader, or get a new one
                if self.frame_read is None:
                    try:
                        self.frame_read = self.drone.get_frame_read()
                    except Exception as e:
                        consecutive_errors += 1
                        if consecutive_errors <= 3:
                            self.log.warning(f"Could not get frame reader: {e}")
                        time.sleep(0.5)
                        continue
                
                # Get frame from the reader
                frame = self.frame_read.frame
                
                if frame is None:
                    time.sleep(0.05)  # Wait a bit longer for frame
                    consecutive_errors += 1
                    if consecutive_errors > 30:
                        self.log.warning("No frames received for extended period")
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
                    pass  # Use frame as-is if resize fails
                
                # Apply color correction to fix blue tint
                frame = self._correct_colors(frame)
                
                # Store clean frame for vision AI (NO overlays)
                with self.frame_lock:
                    self.clean_frame = frame.copy()
                
                # Add overlay info for display
                frame_with_overlay = self._add_overlay(frame)
                
                # Update current frame (thread-safe) - WITH overlays for display
                with self.frame_lock:
                    self.current_frame = frame_with_overlay.copy()
                
                # Publish CLEAN frame event for vision (every 10 frames)
                frame_count += 1
                if frame_count % 10 == 0:
                    self.event_bus.publish('vision.frame', self.clean_frame)
                
                # Control frame rate (~30 FPS)
                time.sleep(0.033)
            
            except Exception as e:
                error_count += 1
                consecutive_errors += 1
                
                # Only log periodically to avoid spam
                if error_count == 1 or error_count % max_errors_before_log == 0:
                    self.log.warning(f"Frame capture error: {e} (total: {error_count})")
                
                # Back off on errors
                time.sleep(0.1)
                
                # Reset frame reader on repeated errors
                if consecutive_errors >= 10:
                    self.log.warning("Resetting frame reader due to repeated errors")
                    self.frame_read = None
                    consecutive_errors = 0
        
        self.log.info("Frame capture loop stopped")
    
    def _correct_colors(self, frame: np.ndarray) -> np.ndarray:
        """
        Correct blue color tint from Tello camera.
        Uses BGR channel adjustment (OpenCV native format).
        
        Args:
            frame: BGR frame from camera (Blue, Green, Red order)
            
        Returns:
            Color-corrected BGR frame
        """
        try:
            # Create a copy to avoid modifying original
            corrected = frame.copy()
            
            # OpenCV uses BGR format:
            # frame[:, :, 0] = Blue channel
            # frame[:, :, 1] = Green channel  
            # frame[:, :, 2] = Red channel
            
            # To fix blue tint: reduce Blue, increase Red/Green
            
            # Blue channel (index 0) - Reduce by 12% to remove blue tint
            corrected[:, :, 0] = np.clip(corrected[:, :, 0] * 0.88, 0, 255).astype(np.uint8)
            
            # Green channel (index 1) - Increase by 5% for balance
            corrected[:, :, 1] = np.clip(corrected[:, :, 1] * 1.05, 0, 255).astype(np.uint8)
            
            # Red channel (index 2) - Increase by 15% to add warmth
            corrected[:, :, 2] = np.clip(corrected[:, :, 2] * 1.15, 0, 255).astype(np.uint8)
            
            return corrected
        
        except Exception as e:
            self.log.debug(f"Color correction failed: {e}")
            return frame  # Return original if correction fails
    
    def _add_overlay(self, frame: np.ndarray) -> np.ndarray:
        """
        Add informational overlay to frame.
        
        Args:
            frame: The frame to add overlay to
            
        Returns:
            Frame with overlay
        """
        try:
            # Get drone status
            battery = self.drone.get_battery()
            
            # Battery color (green -> yellow -> red)
            if battery > 50:
                color = (0, 255, 0)  # Green
            elif battery > 20:
                color = (0, 255, 255)  # Yellow
            else:
                color = (0, 0, 255)  # Red
            
            # Add battery indicator
            cv2.putText(
                frame,
                f"Battery: {battery}%",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                color,
                2
            )
            
            # Add height if flying
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
            
            # Add "GROK-PILOT" branding
            cv2.putText(
                frame,
                "GROK-PILOT",
                (frame.shape[1] - 200, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 255),
                2
            )
        
        except Exception as e:
            self.log.debug(f"Error adding overlay: {e}")
        
        return frame
    
    def get_frame(self) -> Optional[np.ndarray]:
        """
        Get the current frame (thread-safe).
        
        Returns:
            The latest frame, or None if not available
        """
        with self.frame_lock:
            if self.current_frame is not None:
                return self.current_frame.copy()
            return None
    
    def capture_snapshot(self) -> Optional[np.ndarray]:
        """
        Capture a clean snapshot WITHOUT overlays for vision AI.
        
        Returns:
            The clean frame (no battery/height overlays), or None
        """
        with self.frame_lock:
            if self.clean_frame is not None:
                return self.clean_frame.copy()
            return None
    
    def show_window(self) -> None:
        """
        Enable the OpenCV window.
        
        WARNING: This must be called from the main thread on macOS!
        Consider using run_display_loop() instead.
        """
        if not self.running:
            self.log.warning("Cannot show window - stream not running")
            return
        
        self.show_window_enabled = True
        if not self.window_active:
            try:
                cv2.namedWindow("Grok-Pilot Camera", cv2.WINDOW_NORMAL)
                cv2.resizeWindow("Grok-Pilot Camera", 960, 720)
                self.window_active = True
            except Exception as e:
                self.log.error(f"Cannot create window (must be main thread): {e}")
    
    def hide_window(self) -> None:
        """
        Disable the OpenCV window.
        
        WARNING: This must be called from the main thread on macOS!
        """
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
