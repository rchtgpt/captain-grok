"""
Vision tools for Grok-Pilot.
Simplified to just basic look/analyze without entity tracking.

For person search with facial recognition, use focused_search tools instead.
"""

from typing import Optional
from .base import BaseTool, ToolResult
from core.logger import get_logger
from core.exceptions import AbortException
from drone.safety import smart_sleep, ABORT_FLAG


class LookTool(BaseTool):
    """Capture and describe what the drone sees."""
    
    name = "look"
    description = "Take a photo and describe what I see"
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
            
            # Simple scene description
            self.log.info("Analyzing scene...")
            try:
                analysis = self.grok.analyze_image(
                    frame,
                    "Describe what you see. Focus on people, objects, and the environment. Be concise."
                )
                
                return ToolResult(
                    success=True,
                    message=analysis if isinstance(analysis, str) else str(analysis),
                    data={"type": "observation"}
                )
            except Exception as e:
                return ToolResult(
                    success=False,
                    message=f"Vision analysis failed: {e}"
                )
                
        except Exception as e:
            self.log.error(f"Look failed: {e}")
            return ToolResult(success=False, message=f"Look failed: {str(e)}")


class AnalyzeTool(BaseTool):
    """Analyze the current view with a specific question."""
    
    name = "analyze"
    description = "Analyze what I see and answer a specific question"
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
            
            # Analyze with specific question
            self.log.info(f"Analyzing: {question}")
            try:
                analysis = self.grok.analyze_image(
                    frame,
                    question
                )
                
                return ToolResult(
                    success=True,
                    message=analysis if isinstance(analysis, str) else str(analysis),
                    data={"question": question}
                )
            except Exception as e:
                return ToolResult(
                    success=False,
                    message=f"Analysis failed: {e}"
                )
                
        except Exception as e:
            self.log.error(f"Analyze failed: {e}")
            return ToolResult(success=False, message=f"Analysis failed: {str(e)}")


class LookAroundTool(BaseTool):
    """
    360° panoramic survey - quick scan of surroundings.
    For person search, use find_person tool instead.
    """
    
    name = "look_around"
    description = "Do a quick 360° scan to see what's around. For finding specific people, use find_person instead."
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
                return ToolResult(success=False, message="Need to be flying to look around")
            
            self.log.info("Starting 360° panoramic survey...")
            
            observations = []
            num_steps = 8
            rotation_step = 45
            directions = ["ahead", "front-right", "right", "back-right", 
                         "behind", "back-left", "left", "front-left"]
            
            for i in range(num_steps):
                if ABORT_FLAG.is_set():
                    raise AbortException("Survey aborted")
                
                # Rotate (except first position)
                if i > 0:
                    self.drone.rotate(rotation_step, smooth=False)
                    smart_sleep(0.5)
                
                # Capture and analyze
                frame = self.drone.video.capture_snapshot()
                if frame is None:
                    continue
                
                direction = directions[i]
                self.log.debug(f"Analyzing {direction}...")
                
                try:
                    description = self.grok.analyze_image(
                        frame,
                        f"Briefly describe what you see (this is looking {direction}). Focus on people and key objects. 1-2 sentences max."
                    )
                    observations.append(f"**{direction}**: {description}")
                except Exception as e:
                    self.log.warning(f"Analysis failed for {direction}: {e}")
                    observations.append(f"**{direction}**: (analysis failed)")
            
            # Complete the rotation
            self.drone.rotate(rotation_step, smooth=True)
            
            # Build summary
            message = "360° Survey Complete:\n\n" + "\n\n".join(observations)
            
            return ToolResult(
                success=True,
                message=message,
                data={
                    "type": "survey",
                    "directions_scanned": len(observations)
                }
            )
        
        except AbortException as e:
            return ToolResult(success=False, message=str(e))
        except Exception as e:
            self.log.error(f"Look around failed: {e}")
            return ToolResult(success=False, message=f"Survey failed: {str(e)}")


def register_vision_tools(registry, drone_controller, grok_client):
    """
    Register vision tools.
    
    Note: For person search with facial recognition, use register_focused_search_tools.
    """
    registry.register(LookTool(drone_controller, grok_client))
    registry.register(AnalyzeTool(drone_controller, grok_client))
    registry.register(LookAroundTool(drone_controller, grok_client))
