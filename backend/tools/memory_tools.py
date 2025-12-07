"""
Memory tools for drone control.
Simplified - only keeps target management for facial recognition.

Entity tracking removed - use focused_search tools for person search.
"""

from .base import BaseTool, ToolResult
from core.logger import get_logger
from core.memory import get_memory
from core.targets import get_target_manager
from core.face_recognition_service import get_face_service


class RememberPersonTool(BaseTool):
    """Remember the current person as a search target for future missions."""
    
    name = "remember_person"
    description = "Save the person I'm looking at as a search target - creates a target from the current view for facial recognition"
    parameters = {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Name to give this target"
            },
            "description": {
                "type": "string",
                "description": "Optional description (clothing, features)"
            }
        },
        "required": ["name"]
    }
    
    def __init__(self, drone_controller):
        super().__init__()
        self.drone = drone_controller
        self.log = get_logger('tools.remember_person')
    
    def execute(self, name: str, description: str = "", **kwargs) -> ToolResult:
        try:
            if not self.drone.video or not self.drone.video.is_running:
                return ToolResult(success=False, message="Video stream not available")
            
            # Capture current frame
            frame = self.drone.video.capture_snapshot()
            if frame is None:
                return ToolResult(success=False, message="Could not capture frame")
            
            # Check for face in frame
            face_service = get_face_service()
            if not face_service.is_available:
                return ToolResult(
                    success=False,
                    message="Face recognition is not available. Cannot create target."
                )
            
            faces = face_service.extract_all_faces(frame)
            if not faces:
                return ToolResult(
                    success=False,
                    message="No face detected in current view. Please make sure a person's face is visible."
                )
            
            # Save frame as reference photo
            import tempfile
            import cv2
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
            cv2.imwrite(temp_file.name, frame)
            
            # Create target
            target_manager = get_target_manager()
            target = target_manager.add_target(
                name=name,
                description=description,
                photo_paths=[temp_file.name]
            )
            
            # Clean up temp file
            import os
            os.unlink(temp_file.name)
            
            return ToolResult(
                success=True,
                message=f"Got it! I'll remember '{name}' and can find them using facial recognition.",
                data={
                    "target_id": target.id,
                    "name": target.name,
                    "has_face_embedding": len(target.face_embeddings) > 0
                }
            )
            
        except Exception as e:
            self.log.error(f"Remember person failed: {e}")
            return ToolResult(success=False, message=f"Could not remember person: {str(e)}")


class ListTargetsTool(BaseTool):
    """List all registered search targets."""
    
    name = "list_targets"
    description = "List all registered search targets that I can find using facial recognition"
    parameters = {
        "type": "object",
        "properties": {},
        "required": []
    }
    
    def __init__(self):
        super().__init__()
        self.log = get_logger('tools.list_targets')
    
    def execute(self, **kwargs) -> ToolResult:
        try:
            target_manager = get_target_manager()
            targets = target_manager.get_all_targets()
            
            if not targets:
                return ToolResult(
                    success=True,
                    message="No search targets registered yet. Add targets via the web UI or by looking at someone and saying 'remember this person as [name]'.",
                    data={"targets": [], "count": 0}
                )
            
            # Format targets
            lines = [f"**Registered Targets ({len(targets)}):**"]
            for t in targets:
                status_emoji = "✅" if t.status == 'found' else "🔍"
                photos = len(t.reference_photos)
                lines.append(f"  {status_emoji} {t.name}: {t.description or 'No description'} ({photos} photo{'s' if photos != 1 else ''})")
            
            return ToolResult(
                success=True,
                message="\n".join(lines),
                data={
                    "targets": [t.to_dict() for t in targets],
                    "count": len(targets)
                }
            )
            
        except Exception as e:
            self.log.error(f"List targets failed: {e}")
            return ToolResult(success=False, message=f"Could not list targets: {str(e)}")


class DroneStatusTool(BaseTool):
    """Get current drone position and heading."""
    
    name = "drone_status"
    description = "Get my current position and heading"
    parameters = {
        "type": "object",
        "properties": {},
        "required": []
    }
    
    def __init__(self):
        super().__init__()
        self.log = get_logger('tools.drone_status')
    
    def execute(self, **kwargs) -> ToolResult:
        try:
            memory = get_memory()
            
            heading = memory.heading
            position = memory.position
            
            # Format direction
            direction_names = {
                0: "forward (original)",
                45: "front-right",
                90: "right",
                135: "back-right",
                180: "behind",
                225: "back-left",
                270: "left",
                315: "front-left"
            }
            
            closest_dir = min(direction_names.keys(), key=lambda x: abs((heading - x + 180) % 360 - 180))
            direction = direction_names[closest_dir]
            
            return ToolResult(
                success=True,
                message=f"Heading: {heading}° ({direction})\nPosition: x={position['x']}cm, y={position['y']}cm, height={position['z']}cm",
                data={
                    "heading": heading,
                    "direction": direction,
                    "position": position
                }
            )
            
        except Exception as e:
            self.log.error(f"Status failed: {e}")
            return ToolResult(success=False, message=f"Could not get status: {str(e)}")


def register_memory_tools(registry, drone_controller=None, grok_client=None):
    """
    Register memory tools.
    
    Args:
        registry: ToolRegistry instance
        drone_controller: DroneController instance (needed for remember_person)
        grok_client: GrokClient instance (not used in simplified version)
    """
    registry.register(ListTargetsTool())
    registry.register(DroneStatusTool())
    
    if drone_controller:
        registry.register(RememberPersonTool(drone_controller))
