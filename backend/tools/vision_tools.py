"""
Vision and search tools for Grok-Pilot.
Uses Grok Vision for object detection and analysis.
"""

from typing import Optional
from .base import BaseTool, ToolResult
from core.logger import get_logger
from core.exceptions import AbortException
from drone.safety import smart_sleep, ABORT_FLAG


class LookTool(BaseTool):
    """Capture and describe what the drone sees."""
    
    name = "look"
    description = "Take a photo and describe what the drone sees"
    parameters = {
        "type": "object",
        "properties": {},
        "required": []
    }
    
    def __init__(self, drone_controller, grok_client):
        super().__init__()
        self.drone = drone_controller
        self.grok = grok_client
        self.log = get_logger('tools.look')
    
    def execute(self, **kwargs) -> ToolResult:
        try:
            if not self.drone.video or not self.drone.video.is_running:
                return ToolResult(
                    success=False,
                    message="Video stream not available"
                )
            
            # Capture current frame
            frame = self.drone.video.capture_snapshot()
            if frame is None:
                return ToolResult(success=False, message="Could not capture frame")
            
            # Analyze with Grok Vision (structured output)
            self.log.info("🔍 Analyzing scene with Grok Vision (structured output)...")
            analysis = self.grok.analyze_image_structured(frame, "What do you see?")
            
            # Format the response
            message = f"{analysis.summary}\n\n"
            if analysis.objects_detected:
                message += "Objects detected:\n"
                for obj in analysis.objects_detected:
                    message += f"  • {obj.name}: {obj.description}"
                    if obj.estimated_distance:
                        message += f" ({obj.estimated_distance})"
                    message += "\n"
            
            if analysis.hazards:
                message += f"\n⚠️ Hazards: {', '.join(analysis.hazards)}"
            
            return ToolResult(
                success=True,
                message=message.strip(),
                data={
                    "summary": analysis.summary,
                    "objects": [obj.model_dump() for obj in analysis.objects_detected],
                    "hazards": analysis.hazards,
                    "scene_description": analysis.scene_description
                }
            )
        except Exception as e:
            return ToolResult(success=False, message=f"Vision analysis failed: {str(e)}")


class AnalyzeTool(BaseTool):
    """Analyze the current view with a specific question."""
    
    name = "analyze"
    description = "Analyze what the drone sees and answer a specific question"
    parameters = {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "What to analyze or look for"
            }
        },
        "required": ["question"]
    }
    
    def __init__(self, drone_controller, grok_client):
        super().__init__()
        self.drone = drone_controller
        self.grok = grok_client
        self.log = get_logger('tools.analyze')
    
    def execute(self, question: str, **kwargs) -> ToolResult:
        try:
            if not self.drone.video or not self.drone.video.is_running:
                return ToolResult(success=False, message="Video stream not available")
            
            frame = self.drone.video.capture_snapshot()
            if frame is None:
                return ToolResult(success=False, message="Could not capture frame")
            
            # Analyze with specific question (structured output)
            self.log.info(f"🔍 Analyzing: {question}")
            analysis = self.grok.analyze_image_structured(frame, question, detailed=True)
            
            # Format response
            message = f"Q: {question}\n\nA: {analysis.summary}\n\n{analysis.scene_description}"
            
            return ToolResult(
                success=True,
                message=message,
                data={
                    "question": question,
                    "summary": analysis.summary,
                    "objects": [obj.model_dump() for obj in analysis.objects_detected],
                    "scene_description": analysis.scene_description
                }
            )
        except Exception as e:
            return ToolResult(success=False, message=f"Analysis failed: {str(e)}")


class SearchTool(BaseTool):
    """Search for a target by rotating and using vision."""
    
    name = "search"
    description = "Actively search for a person or object by rotating 360° and using vision analysis"
    parameters = {
        "type": "object",
        "properties": {
            "target": {
                "type": "string",
                "description": "Detailed description of what to search for (e.g., 'person wearing red shirt with glasses')"
            },
            "rotation_step": {
                "type": "integer",
                "description": "Degrees to rotate between checks (default: 45)",
                "minimum": 30,
                "maximum": 90,
                "default": 45
            }
        },
        "required": ["target"]
    }
    
    def __init__(self, drone_controller, grok_client):
        super().__init__()
        self.drone = drone_controller
        self.grok = grok_client
        self.log = get_logger('tools.search')
    
    def execute(self, target: str, rotation_step: int = 45, **kwargs) -> ToolResult:
        try:
            if not self.drone.video or not self.drone.video.is_running:
                return ToolResult(success=False, message="Video stream not available")
            
            if not self.drone.state_machine.is_flying():
                return ToolResult(success=False, message="Drone must be flying to search")
            
            self.log.info(f"Starting search for: {target}")
            
            # Calculate rotation angles
            num_steps = 360 // rotation_step
            angles = [rotation_step * i for i in range(num_steps)]
            
            # Search at each angle
            for i, angle in enumerate(angles):
                # Check abort flag
                if ABORT_FLAG.is_set():
                    raise AbortException("Search aborted by user")
                
                self.log.debug(f"Checking angle {angle}° ({i+1}/{num_steps})")
                
                # Capture and analyze
                frame = self.drone.video.capture_snapshot()
                if frame is None:
                    continue
                
                # Use structured search
                result = self.grok.search_for_target_structured(frame, target)
                
                self.log.debug(f"Search result at {angle}°: {result.found} (confidence: {result.confidence})")
                
                if result.found and result.confidence in ["high", "medium"]:
                    self.log.success(f"Found {target} at angle {angle}°!")
                    return ToolResult(
                        success=True,
                        message=f"✅ Found {target}! {result.description}",
                        data={
                            "found": True,
                            "angle": angle,
                            "estimated_distance": result.estimated_distance,
                            "confidence": result.confidence,
                            "description": result.description,
                            "target": target,
                            "recommended_action": result.recommended_action
                        }
                    )
                
                # Rotate to next position (unless last iteration)
                if i < num_steps - 1:
                    self.drone.rotate(rotation_step)
                    smart_sleep(1)  # Wait for rotation to complete
            
            # Not found after full rotation
            self.log.info(f"Search complete - {target} not found")
            return ToolResult(
                success=False,
                message=f"Could not find {target} after searching 360°",
                data={"found": False, "target": target}
            )
        
        except AbortException as e:
            return ToolResult(success=False, message=str(e))
        except Exception as e:
            self.log.error(f"Search failed: {e}")
            return ToolResult(success=False, message=f"Search failed: {str(e)}")


class LookAroundTool(BaseTool):
    """Rotate 360° and describe the surroundings."""
    
    name = "look_around"
    description = "Rotate 360° and describe everything visible from all directions"
    parameters = {
        "type": "object",
        "properties": {},
        "required": []
    }
    
    def __init__(self, drone_controller, grok_client):
        super().__init__()
        self.drone = drone_controller
        self.grok = grok_client
        self.log = get_logger('tools.look_around')
    
    def execute(self, **kwargs) -> ToolResult:
        try:
            if not self.drone.video or not self.drone.video.is_running:
                return ToolResult(success=False, message="Video stream not available")
            
            if not self.drone.state_machine.is_flying():
                return ToolResult(success=False, message="Drone must be flying to look around")
            
            self.log.info("Starting 360° panorama")
            
            # Capture at 4 cardinal directions
            directions = [
                ("ahead", 0),
                ("right", 90),
                ("behind", 180),
                ("left", 270)
            ]
            
            descriptions = {}
            
            for direction_name, angle in directions:
                if ABORT_FLAG.is_set():
                    raise AbortException("Look around aborted")
                
                frame = self.drone.video.capture_snapshot()
                if frame is not None:
                    # Use structured analysis
                    analysis = self.grok.analyze_image_structured(
                        frame,
                        f"Briefly describe what you see in this direction",
                        detailed=False
                    )
                    descriptions[direction_name] = analysis.summary
                
                # Rotate to next direction (except last)
                if angle < 270:
                    self.drone.rotate(90)
                    smart_sleep(1)
            
            # Compile full description
            full_desc = "\n".join([
                f"{dir.capitalize()}: {desc}"
                for dir, desc in descriptions.items()
            ])
            
            return ToolResult(
                success=True,
                message=full_desc,
                data={"directions": descriptions}
            )
        
        except AbortException as e:
            return ToolResult(success=False, message=str(e))
        except Exception as e:
            return ToolResult(success=False, message=f"Look around failed: {str(e)}")


def register_vision_tools(registry, drone_controller, grok_client):
    """
    Register all vision tools.
    
    Args:
        registry: ToolRegistry instance
        drone_controller: DroneController instance
        grok_client: GrokClient instance
    """
    registry.register(LookTool(drone_controller, grok_client))
    registry.register(AnalyzeTool(drone_controller, grok_client))
    registry.register(SearchTool(drone_controller, grok_client))
    registry.register(LookAroundTool(drone_controller, grok_client))
