"""
Session video recorder for drone footage.
Records clean video (no overlays) to MP4 files.
"""

import cv2
import json
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import numpy as np

from core.logger import get_logger

log = get_logger('recorder')


class SessionRecorder:
    """
    Records session video to MP4 format.
    
    Features:
    - Records clean frames (no overlays) for review
    - Auto-starts on takeoff, auto-stops on land
    - Manual start/stop also supported
    - Saves session metadata (duration, targets found, etc.)
    """
    
    # Video settings
    CODEC = 'mp4v'  # Good compatibility
    FPS = 30.0
    RESOLUTION = (960, 720)
    
    def __init__(self, base_dir: Optional[Path] = None):
        """
        Initialize recorder.
        
        Args:
            base_dir: Base directory for sessions (default: backend/data/sessions)
        """
        if base_dir is None:
            backend_dir = Path(__file__).parent.parent
            base_dir = backend_dir / "data" / "sessions"
        
        self.base_dir = Path(base_dir).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        # Current session state
        self.session_dir: Optional[Path] = None
        self.session_id: Optional[str] = None
        self.video_writer: Optional[cv2.VideoWriter] = None
        self.recording = False
        self.manual_mode = False  # True if manually started (won't auto-stop)
        
        # Session stats
        self.start_time: Optional[datetime] = None
        self.frame_count = 0
        self.targets_found: list = []
        self.events: list = []
        
        # Thread safety
        self._lock = threading.Lock()
        
        log.info(f"SessionRecorder initialized. Base dir: {self.base_dir}")
    
    def start(self, manual: bool = False) -> str:
        """
        Start a new recording session.
        
        Args:
            manual: If True, won't auto-stop on land
            
        Returns:
            Session ID (timestamp string)
        """
        with self._lock:
            if self.recording:
                log.warning("Already recording, stopping current session first")
                self._stop_internal()
            
            # Create session directory
            self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.session_dir = self.base_dir / self.session_id
            self.session_dir.mkdir(parents=True, exist_ok=True)
            
            # Create thumbnails directory for events
            (self.session_dir / "thumbnails").mkdir(exist_ok=True)
            
            # Initialize video writer
            video_path = self.session_dir / "video.mp4"
            fourcc = cv2.VideoWriter_fourcc(*self.CODEC)
            self.video_writer = cv2.VideoWriter(
                str(video_path),
                fourcc,
                self.FPS,
                self.RESOLUTION
            )
            
            if not self.video_writer.isOpened():
                log.error(f"Failed to open video writer for {video_path}")
                self.video_writer = None
                raise RuntimeError("Failed to initialize video recording")
            
            # Reset stats
            self.recording = True
            self.manual_mode = manual
            self.start_time = datetime.now()
            self.frame_count = 0
            self.targets_found = []
            self.events = []
            
            # Add start event
            self._add_event("session_start", {"manual": manual})
            
            log.success(f"Recording started: {self.session_id}")
            return self.session_id
    
    def stop(self) -> Optional[Dict[str, Any]]:
        """
        Stop recording and finalize session.
        
        Returns:
            Session metadata dict, or None if not recording
        """
        with self._lock:
            return self._stop_internal()
    
    def _stop_internal(self) -> Optional[Dict[str, Any]]:
        """Internal stop method (must hold lock)."""
        if not self.recording:
            return None
        
        # Add stop event
        self._add_event("session_stop", {})
        
        # Release video writer
        if self.video_writer:
            self.video_writer.release()
            self.video_writer = None
        
        # Calculate duration
        duration = 0
        if self.start_time:
            duration = (datetime.now() - self.start_time).total_seconds()
        
        # Build metadata
        metadata = {
            "session_id": self.session_id,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": datetime.now().isoformat(),
            "duration_seconds": duration,
            "frame_count": self.frame_count,
            "fps": self.FPS,
            "resolution": list(self.RESOLUTION),
            "targets_found": self.targets_found,
            "events": self.events,
            "video_file": "video.mp4"
        }
        
        # Save metadata
        if self.session_dir:
            metadata_path = self.session_dir / "session.json"
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
        
        # Reset state
        session_id = self.session_id
        self.recording = False
        self.session_id = None
        self.session_dir = None
        self.start_time = None
        self.frame_count = 0
        self.manual_mode = False
        
        log.success(f"Recording stopped: {session_id} ({duration:.1f}s, {metadata['frame_count']} frames)")
        return metadata
    
    def write_frame(self, frame: np.ndarray) -> bool:
        """
        Write a frame to the video.
        
        Args:
            frame: BGR frame (clean, no overlays)
            
        Returns:
            True if written successfully
        """
        with self._lock:
            if not self.recording or self.video_writer is None:
                return False
            
            try:
                # Ensure correct size
                if frame.shape[:2] != (self.RESOLUTION[1], self.RESOLUTION[0]):
                    frame = cv2.resize(frame, self.RESOLUTION)
                
                self.video_writer.write(frame)
                self.frame_count += 1
                return True
                
            except Exception as e:
                log.error(f"Error writing frame: {e}")
                return False
    
    def save_thumbnail(self, frame: np.ndarray, name: str) -> Optional[str]:
        """
        Save a thumbnail image for an event.
        
        Args:
            frame: BGR frame
            name: Thumbnail name (without extension)
            
        Returns:
            Path to saved thumbnail, or None
        """
        with self._lock:
            if not self.session_dir:
                return None
            
            try:
                thumb_path = self.session_dir / "thumbnails" / f"{name}.jpg"
                cv2.imwrite(str(thumb_path), frame)
                return str(thumb_path)
            except Exception as e:
                log.error(f"Error saving thumbnail: {e}")
                return None
    
    def record_target_found(
        self, 
        target_id: str, 
        target_name: str, 
        confidence: float,
        frame: Optional[np.ndarray] = None
    ) -> None:
        """
        Record that a target was found during this session.
        
        Args:
            target_id: Target ID
            target_name: Target name
            confidence: Match confidence (0-1)
            frame: Optional frame to save as thumbnail
        """
        with self._lock:
            timestamp = datetime.now().isoformat()
            
            # Save thumbnail if frame provided
            thumb_path = None
            if frame is not None and self.session_dir:
                thumb_name = f"found_{target_id}_{len(self.targets_found)}"
                thumb_path = self.save_thumbnail(frame, thumb_name)
            
            found_record = {
                "target_id": target_id,
                "target_name": target_name,
                "confidence": confidence,
                "timestamp": timestamp,
                "frame_number": self.frame_count,
                "thumbnail": thumb_path
            }
            
            self.targets_found.append(found_record)
            self._add_event("target_found", found_record)
            
            log.info(f"Recorded target found: {target_name} ({confidence:.1%})")
    
    def _add_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Add an event to the session log."""
        self.events.append({
            "type": event_type,
            "timestamp": datetime.now().isoformat(),
            "frame_number": self.frame_count,
            "data": data
        })
    
    def on_takeoff(self) -> None:
        """Called when drone takes off - auto-start recording if not manual."""
        if not self.recording:
            log.info("Auto-starting recording on takeoff")
            self.start(manual=False)
        else:
            self._add_event("takeoff", {})
    
    def on_land(self) -> None:
        """Called when drone lands - auto-stop recording if not manual."""
        if self.recording:
            self._add_event("land", {})
            if not self.manual_mode:
                log.info("Auto-stopping recording on land")
                self._stop_internal()
    
    # ==================== Session Management ====================
    
    def list_sessions(self) -> list:
        """List all recorded sessions."""
        sessions = []
        
        for session_dir in sorted(self.base_dir.iterdir(), reverse=True):
            if session_dir.is_dir():
                metadata_file = session_dir / "session.json"
                if metadata_file.exists():
                    try:
                        with open(metadata_file, 'r') as f:
                            metadata = json.load(f)
                        sessions.append(metadata)
                    except Exception as e:
                        log.warning(f"Could not read session {session_dir.name}: {e}")
                        # Add minimal info
                        sessions.append({
                            "session_id": session_dir.name,
                            "error": str(e)
                        })
        
        return sessions
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a specific session."""
        session_dir = self.base_dir / session_id
        metadata_file = session_dir / "session.json"
        
        if metadata_file.exists():
            with open(metadata_file, 'r') as f:
                return json.load(f)
        return None
    
    def get_session_video_path(self, session_id: str) -> Optional[Path]:
        """Get path to session video file."""
        video_path = self.base_dir / session_id / "video.mp4"
        if video_path.exists():
            return video_path
        return None
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session and all its files."""
        import shutil
        
        session_dir = self.base_dir / session_id
        if session_dir.exists() and session_dir.is_dir():
            try:
                shutil.rmtree(session_dir)
                log.info(f"Deleted session: {session_id}")
                return True
            except Exception as e:
                log.error(f"Error deleting session {session_id}: {e}")
                return False
        return False
    
    def delete_all_sessions(self) -> int:
        """Delete all sessions. Returns count of deleted sessions."""
        import shutil
        
        deleted = 0
        for session_dir in self.base_dir.iterdir():
            if session_dir.is_dir():
                try:
                    shutil.rmtree(session_dir)
                    deleted += 1
                except Exception as e:
                    log.error(f"Error deleting session {session_dir.name}: {e}")
        
        log.info(f"Deleted {deleted} sessions")
        return deleted
    
    # ==================== Properties ====================
    
    @property
    def is_recording(self) -> bool:
        """Check if currently recording."""
        return self.recording
    
    @property
    def current_session_id(self) -> Optional[str]:
        """Get current session ID."""
        return self.session_id
    
    @property
    def duration(self) -> float:
        """Get current recording duration in seconds."""
        if self.start_time and self.recording:
            return (datetime.now() - self.start_time).total_seconds()
        return 0.0
    
    def get_status(self) -> Dict[str, Any]:
        """Get current recorder status."""
        return {
            "recording": self.recording,
            "session_id": self.session_id,
            "manual_mode": self.manual_mode,
            "duration_seconds": self.duration,
            "frame_count": self.frame_count,
            "targets_found_count": len(self.targets_found)
        }


# Singleton instance
_recorder: Optional[SessionRecorder] = None
_recorder_lock = threading.Lock()


def get_recorder() -> SessionRecorder:
    """Get the singleton SessionRecorder instance."""
    global _recorder
    with _recorder_lock:
        if _recorder is None:
            _recorder = SessionRecorder()
        return _recorder


def init_recorder(base_dir: Optional[Path] = None) -> SessionRecorder:
    """Initialize the recorder with a specific base directory."""
    global _recorder
    with _recorder_lock:
        _recorder = SessionRecorder(base_dir)
        return _recorder
