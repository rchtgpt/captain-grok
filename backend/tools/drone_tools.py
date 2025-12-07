"""
Drone control tools for Grok-Pilot.
Provides movement commands as callable tools.
"""

from typing import Optional
from .base import BaseTool, ToolResult
from core.logger import get_logger
from core.exceptions import SafetyViolationError


class TakeoffTool(BaseTool):
    """Make the drone take off and hover."""
    
    name = "takeoff"
    description = "Make the drone take off and hover at a safe altitude"
    parameters = {
        "type": "object",
        "properties": {},
        "required": []
    }
    
    def __init__(self, drone_controller):
        super().__init__()
        self.drone = drone_controller
        self.log = get_logger('tools.takeoff')
    
    def execute(self, **kwargs) -> ToolResult:
        try:
            self.drone.takeoff()
            return ToolResult(
                success=True,
                message="Drone is now airborne and hovering!",
                data={"height": 50, "status": "hovering"}
            )
        except SafetyViolationError as e:
            return ToolResult(success=False, message=f"Safety check failed: {str(e)}")
        except Exception as e:
            return ToolResult(success=False, message=f"Takeoff failed: {str(e)}")


class LandTool(BaseTool):
    """Land the drone safely."""
    
    name = "land"
    description = "Land the drone safely on the ground"
    parameters = {
        "type": "object",
        "properties": {},
        "required": []
    }
    
    def __init__(self, drone_controller):
        super().__init__()
        self.drone = drone_controller
        self.log = get_logger('tools.land')
    
    def execute(self, **kwargs) -> ToolResult:
        try:
            self.drone.land()
            return ToolResult(
                success=True,
                message="Drone has landed safely!",
                data={"status": "grounded"}
            )
        except Exception as e:
            return ToolResult(success=False, message=f"Landing failed: {str(e)}")


class MoveTool(BaseTool):
    """Move the drone in a direction."""
    
    name = "move"
    description = "Move the drone in a specified direction (forward/back/left/right/up/down)"
    parameters = {
        "type": "object",
        "properties": {
            "direction": {
                "type": "string",
                "enum": ["forward", "back", "left", "right", "up", "down"],
                "description": "Direction to move"
            },
            "distance": {
                "type": "integer",
                "description": "Distance in centimeters (20-100)",
                "minimum": 20,
                "maximum": 100
            }
        },
        "required": ["direction", "distance"]
    }
    
    def __init__(self, drone_controller):
        super().__init__()
        self.drone = drone_controller
        self.log = get_logger('tools.move')
    
    def execute(self, direction: str, distance: int, **kwargs) -> ToolResult:
        try:
            # Clamp distance to safe range
            distance = max(20, min(100, distance))
            
            self.drone.move(direction, distance)
            return ToolResult(
                success=True,
                message=f"Moved {direction} {distance}cm",
                data={"direction": direction, "distance": distance}
            )
        except SafetyViolationError as e:
            return ToolResult(success=False, message=f"Movement blocked: {str(e)}")
        except Exception as e:
            return ToolResult(success=False, message=f"Movement failed: {str(e)}")


class RotateTool(BaseTool):
    """Rotate the drone."""
    
    name = "rotate"
    description = "Rotate the drone by a number of degrees (positive = clockwise, negative = counter-clockwise)"
    parameters = {
        "type": "object",
        "properties": {
            "degrees": {
                "type": "integer",
                "description": "Degrees to rotate (-360 to 360)",
                "minimum": -360,
                "maximum": 360
            }
        },
        "required": ["degrees"]
    }
    
    def __init__(self, drone_controller):
        super().__init__()
        self.drone = drone_controller
        self.log = get_logger('tools.rotate')
    
    def execute(self, degrees: int, **kwargs) -> ToolResult:
        try:
            self.drone.rotate(degrees)
            direction = "clockwise" if degrees > 0 else "counter-clockwise"
            return ToolResult(
                success=True,
                message=f"Rotated {abs(degrees)}° {direction}",
                data={"degrees": degrees, "direction": direction}
            )
        except Exception as e:
            return ToolResult(success=False, message=f"Rotation failed: {str(e)}")


class FlipTool(BaseTool):
    """Perform a flip maneuver."""
    
    name = "flip"
    description = "Perform a flip in the specified direction (forward/back/left/right)"
    parameters = {
        "type": "object",
        "properties": {
            "direction": {
                "type": "string",
                "enum": ["forward", "back", "left", "right"],
                "description": "Direction to flip"
            }
        },
        "required": ["direction"]
    }
    
    def __init__(self, drone_controller):
        super().__init__()
        self.drone = drone_controller
        self.log = get_logger('tools.flip')
    
    def execute(self, direction: str, **kwargs) -> ToolResult:
        try:
            self.drone.flip(direction)
            return ToolResult(
                success=True,
                message=f"Executed {direction} flip!",
                data={"direction": direction}
            )
        except SafetyViolationError as e:
            return ToolResult(success=False, message=f"Flip blocked: {str(e)}")
        except Exception as e:
            return ToolResult(success=False, message=f"Flip failed: {str(e)}")


class HoverTool(BaseTool):
    """Stop all movement and hover in place."""
    
    name = "hover"
    description = "Stop all movement and hover in place"
    parameters = {
        "type": "object",
        "properties": {},
        "required": []
    }
    
    def __init__(self, drone_controller):
        super().__init__()
        self.drone = drone_controller
        self.log = get_logger('tools.hover')
    
    def execute(self, **kwargs) -> ToolResult:
        try:
            self.drone.hover()
            return ToolResult(
                success=True,
                message="Hovering in place",
                data={"status": "hovering"}
            )
        except Exception as e:
            return ToolResult(success=False, message=f"Hover failed: {str(e)}")


def register_drone_tools(registry, drone_controller):
    """
    Register all drone control tools.
    
    Args:
        registry: ToolRegistry instance
        drone_controller: DroneController instance
    """
    registry.register(TakeoffTool(drone_controller))
    registry.register(LandTool(drone_controller))
    registry.register(MoveTool(drone_controller))
    registry.register(RotateTool(drone_controller))
    registry.register(FlipTool(drone_controller))
    registry.register(HoverTool(drone_controller))
