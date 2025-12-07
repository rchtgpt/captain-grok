"""
Focused Person Search Tool.

A simplified, highly-focused tool for finding specific people
using dual verification (CV + Grok Vision).

Replaces the complex memory-based search tools with a streamlined approach.
"""

import time
from typing import Optional, TYPE_CHECKING

from tools.base import BaseTool, ToolResult
from core.logger import get_logger
from core.dual_verification import get_dual_verifier, VerificationResult
from core.targets import get_target_manager, Target
from drone.safety import ABORT_FLAG, smart_sleep
from drone.recorder import get_recorder

if TYPE_CHECKING:
    from drone.controller import DroneController
    from ai.grok_client import GrokClient

log = get_logger('focused_search')


class FindPersonTool(BaseTool):
    """
    Search for a specific registered target using facial recognition.
    
    Performs a 360-degree scan with dual verification (CV + Grok)
    at each angle. Stops and reports when target is found with
    high confidence.
    """
    
    name = "find_person"
    description = "Search for a specific person using facial recognition. Performs 360° scan with high-accuracy dual verification."
    
    parameters = {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Name of the registered target to find"
            }
        },
        "required": ["name"]
    }
    
    # Search configuration
    ANGLES_TO_CHECK = 8  # 360 / 8 = 45 degrees per step
    ROTATION_PER_STEP = 45
    SETTLE_TIME = 0.5  # Time to wait after rotation
    
    def __init__(self, drone: 'DroneController', grok: 'GrokClient'):
        self.drone = drone
        self.grok = grok
        self.target_manager = get_target_manager()
    
    def execute(self, name: str) -> ToolResult:
        """
        Execute the search for a specific person.
        
        Args:
            name: Name of the target to find
            
        Returns:
            ToolResult with search outcome
        """
        log.info(f"Starting focused search for: {name}")
        
        # Check abort flag
        if ABORT_FLAG.is_set():
            return ToolResult(
                success=False,
                message="Search aborted",
                data={"aborted": True}
            )
        
        # Find the target
        target = self.target_manager.get_target_by_name(name)
        
        if not target:
            # Target not registered
            return ToolResult(
                success=False,
                message=f"'{name}' is not a registered target. Please add them first with a photo.",
                data={
                    "error": "target_not_found",
                    "suggestion": "Add target via the web UI or say 'remember [name]'"
                }
            )
        
        if not target.face_embeddings:
            return ToolResult(
                success=False,
                message=f"'{name}' has no face photo. Please add a clear face photo first.",
                data={
                    "error": "no_face_data",
                    "target_id": target.id
                }
            )
        
        if target.status == 'found':
            return ToolResult(
                success=True,
                message=f"'{name}' was already found! Use 'tail' to follow them.",
                data={
                    "already_found": True,
                    "target_id": target.id,
                    "target_name": target.name,
                    "confidence": target.match_confidence
                }
            )
        
        # Get dual verifier
        verifier = get_dual_verifier()
        if not verifier:
            # Initialize it
            from core.face_recognition_service import get_face_service
            from core.dual_verification import init_dual_verifier
            face_service = get_face_service()
            verifier = init_dual_verifier(face_service, self.grok)
        
        # Perform 360° search
        log.info(f"Scanning 360° for {name} ({self.ANGLES_TO_CHECK} positions)")
        
        best_result: Optional[VerificationResult] = None
        best_angle = 0
        best_frame = None
        
        for i in range(self.ANGLES_TO_CHECK):
            # Check abort
            if ABORT_FLAG.is_set():
                log.warning("Search aborted by user")
                return ToolResult(
                    success=False,
                    message="Search aborted",
                    data={"aborted": True, "angles_checked": i}
                )
            
            current_angle = i * self.ROTATION_PER_STEP
            log.debug(f"Checking angle {current_angle}°")
            
            # Capture frame
            frame = self._capture_frame()
            if frame is None:
                log.warning("Could not capture frame")
                continue
            
            # Run dual verification
            result = verifier.verify(frame, target)
            
            log.debug(
                f"Angle {current_angle}°: match={result.is_match}, "
                f"cv={result.cv_confidence:.1%}, grok={result.grok_confidence:.1%}, "
                f"level={result.confidence_level}"
            )
            
            # Check for match
            if result.is_match and result.confidence_level in ('high', 'medium'):
                log.success(f"TARGET FOUND at {current_angle}°! Confidence: {result.confidence:.1%}")
                
                # Save the match
                return self._handle_found(
                    target, result, frame, current_angle
                )
            
            # Track best result even if not a match
            if best_result is None or result.confidence > best_result.confidence:
                best_result = result
                best_angle = current_angle
                best_frame = frame
            
            # Rotate to next position (except on last iteration)
            if i < self.ANGLES_TO_CHECK - 1:
                try:
                    self.drone.rotate(self.ROTATION_PER_STEP)
                    smart_sleep(self.SETTLE_TIME)
                except Exception as e:
                    log.error(f"Rotation failed: {e}")
        
        # Search complete - target not found
        log.info(f"Search complete. '{name}' not found.")
        
        # Return best partial match info if any
        data = {
            "found": False,
            "target_name": name,
            "angles_checked": self.ANGLES_TO_CHECK
        }
        
        if best_result and best_result.confidence > 0.3:
            data["best_match"] = {
                "angle": best_angle,
                "confidence": best_result.confidence,
                "grok_description": best_result.grok_description
            }
        
        return ToolResult(
            success=True,  # Search completed successfully, just didn't find target
            message=f"Completed 360° search. '{name}' not found in the area.",
            data=data
        )
    
    def _capture_frame(self):
        """Capture a frame from the drone camera."""
        if not self.drone.video:
            return None
        
        return self.drone.video.capture_snapshot()
    
    def _handle_found(
        self, 
        target: Target, 
        result: VerificationResult,
        frame,
        angle: int
    ) -> ToolResult:
        """Handle when target is found."""
        # Record the find in session
        recorder = get_recorder()
        if recorder.is_recording:
            recorder.record_target_found(
                target.id,
                target.name,
                result.confidence,
                frame
            )
        
        # Mark target as found
        self.target_manager.mark_found(
            target.id,
            entity_id=None,  # No memory entity anymore
            frame=frame,
            confidence=result.confidence
        )
        
        # Build response
        direction = self._angle_to_direction(angle)
        
        return ToolResult(
            success=True,
            message=f"FOUND: {target.name}! {result.confidence:.0%} confidence. Location: {direction}",
            data={
                "found": True,
                "target_id": target.id,
                "target_name": target.name,
                "confidence": result.confidence,
                "confidence_level": result.confidence_level,
                "angle": angle,
                "direction": direction,
                "cv_confidence": result.cv_confidence,
                "grok_confidence": result.grok_confidence,
                "grok_description": result.grok_description,
                "bbox": result.bbox
            }
        )
    
    def _angle_to_direction(self, angle: int) -> str:
        """Convert angle to human-readable direction."""
        # Normalize angle to 0-360
        angle = angle % 360
        
        if angle < 22.5 or angle >= 337.5:
            return "directly ahead"
        elif angle < 67.5:
            return "slightly to your right"
        elif angle < 112.5:
            return "to your right"
        elif angle < 157.5:
            return "behind and to your right"
        elif angle < 202.5:
            return "behind you"
        elif angle < 247.5:
            return "behind and to your left"
        elif angle < 292.5:
            return "to your left"
        else:
            return "slightly to your left"


class QuickLookTool(BaseTool):
    """
    Quick look at what's in frame without full search.
    Detects faces and matches against registered targets.
    """
    
    name = "look"
    description = "Look at what's currently in view. Detects faces and identifies registered targets."
    
    parameters = {
        "type": "object",
        "properties": {},
        "required": []
    }
    
    def __init__(self, drone: 'DroneController', grok: 'GrokClient'):
        self.drone = drone
        self.grok = grok
        self.target_manager = get_target_manager()
    
    def execute(self) -> ToolResult:
        """Look at current frame and identify any faces/targets."""
        log.info("Quick look - analyzing current view")
        
        # Capture frame
        if not self.drone.video:
            return ToolResult(
                success=False,
                message="Video stream not available",
                data={}
            )
        
        frame = self.drone.video.capture_snapshot()
        if frame is None:
            return ToolResult(
                success=False,
                message="Could not capture frame",
                data={}
            )
        
        # Get face detections from video stream cache
        faces = self.drone.video.get_cached_faces()
        
        if not faces:
            # No cached faces, do a quick Grok analysis
            try:
                analysis = self.grok.analyze_image(
                    frame,
                    "Describe what you see in this image. Focus on any people present, their appearance, and what they're doing. Keep it brief."
                )
                
                return ToolResult(
                    success=True,
                    message=analysis if isinstance(analysis, str) else str(analysis),
                    data={"faces_detected": 0}
                )
            except Exception as e:
                return ToolResult(
                    success=False,
                    message=f"Vision analysis failed: {e}",
                    data={}
                )
        
        # Report on detected faces
        known_targets = [f for f in faces if f.get('target_name')]
        unknown_faces = [f for f in faces if not f.get('target_name')]
        
        parts = []
        
        if known_targets:
            names = [f['target_name'] for f in known_targets]
            parts.append(f"Recognized: {', '.join(names)}")
        
        if unknown_faces:
            parts.append(f"{len(unknown_faces)} unknown face(s)")
        
        if not parts:
            parts.append("No faces detected")
        
        return ToolResult(
            success=True,
            message=" | ".join(parts),
            data={
                "faces_detected": len(faces),
                "known_targets": [f['target_name'] for f in known_targets],
                "unknown_count": len(unknown_faces)
            }
        )


def register_focused_search_tools(registry, drone: 'DroneController', grok: 'GrokClient'):
    """Register focused search tools with the registry."""
    registry.register(FindPersonTool(drone, grok))
    registry.register(QuickLookTool(drone, grok))
    
    log.info("Registered focused search tools: find_person, look")
