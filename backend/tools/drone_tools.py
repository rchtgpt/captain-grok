"""
Drone control tools for Grok-Pilot.
Provides movement commands as callable tools.
All risky maneuvers include vision-based safety checks.
"""

from typing import Optional
from .base import BaseTool, ToolResult
from core.logger import get_logger
from core.exceptions import SafetyViolationError


# Minimum requirements for flip maneuvers
FLIP_MIN_BATTERY = 50  # Tello requires ~50% battery for flips
FLIP_MIN_HEIGHT_CM = 100  # Need at least 1m altitude
FLIP_MIN_CLEARANCE_CM = 200  # Need 2m clearance all around


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
    """Move the drone in a direction with optional safety checks."""
    
    name = "move"
    description = "Move the drone in a specified direction (forward/back/left/right/up/down). Large movements auto-check for obstacles."
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
            },
            "check_obstacles": {
                "type": "boolean",
                "description": "Run obstacle check before moving (auto for distance > 50cm)",
                "default": None
            }
        },
        "required": ["direction", "distance"]
    }
    
    # Threshold for automatic obstacle checking
    AUTO_CHECK_DISTANCE = 50  # Check obstacles for moves > 50cm
    
    def __init__(self, drone_controller, grok_client=None):
        super().__init__()
        self.drone = drone_controller
        self.grok = grok_client
        self.log = get_logger('tools.move')
    
    def execute(self, direction: str, distance: int, check_obstacles: bool = None, **kwargs) -> ToolResult:
        try:
            # Clamp distance to safe range
            distance = max(20, min(100, distance))
            
            # Determine if we should check obstacles
            should_check = check_obstacles
            if should_check is None:
                # Auto-check for larger movements
                should_check = distance >= self.AUTO_CHECK_DISTANCE
            
            # === OBSTACLE CHECK (for forward/lateral movements) ===
            if should_check and direction in ['forward', 'left', 'right']:
                if self.grok and self.drone.video and self.drone.video.is_running:
                    frame = self.drone.video.capture_snapshot()
                    
                    if frame is not None:
                        maneuver_type = "forward" if direction == "forward" else "lateral"
                        clearance = self.grok.check_clearance(
                            frame,
                            maneuver_type=maneuver_type,
                            required_clearance_cm=distance + 30  # Need clearance > movement distance
                        )
                        
                        # Check if direction is safe
                        is_direction_safe = True
                        if direction == "forward" and not clearance.safe_for_forward_movement:
                            is_direction_safe = False
                        elif direction in ["left", "right"] and not clearance.safe_for_lateral_movement:
                            is_direction_safe = False
                        
                        if not is_direction_safe:
                            self.log.warning(f"⚠️ Obstacle detected in {direction} direction!")
                            
                            # Get estimated clearance
                            clearance_cm = {
                                "forward": clearance.front_clearance_cm,
                                "left": clearance.left_clearance_cm,
                                "right": clearance.right_clearance_cm
                            }.get(direction, -1)
                            
                            if clearance_cm > 0 and clearance_cm < distance:
                                # Reduce movement to safe distance
                                safe_distance = max(20, clearance_cm - 30)  # 30cm safety buffer
                                self.log.warning(f"Reducing movement from {distance}cm to {safe_distance}cm for safety")
                                distance = safe_distance
                            elif clearance_cm > 0 and clearance_cm < 50:
                                return ToolResult(
                                    success=False,
                                    message=f"❌ Movement blocked: Only {clearance_cm}cm clearance in {direction} direction. "
                                            f"Recommendation: {clearance.recommended_action}",
                                    data={
                                        "blocked_by": "obstacle",
                                        "direction": direction,
                                        "clearance_cm": clearance_cm,
                                        "obstacles": [obs.model_dump() for obs in clearance.obstacles]
                                    }
                                )
                        else:
                            self.log.info(f"✅ Path clear in {direction} direction")
            
            # === EXECUTE MOVEMENT ===
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
    """Perform a flip maneuver with comprehensive safety checks."""
    
    name = "flip"
    description = "Perform a flip in the specified direction (forward/back/left/right). Includes automatic safety checks using camera vision."
    parameters = {
        "type": "object",
        "properties": {
            "direction": {
                "type": "string",
                "enum": ["forward", "back", "left", "right"],
                "description": "Direction to flip"
            },
            "skip_safety_check": {
                "type": "boolean",
                "description": "Skip vision safety check (NOT RECOMMENDED)",
                "default": False
            }
        },
        "required": ["direction"]
    }
    
    def __init__(self, drone_controller, grok_client=None):
        super().__init__()
        self.drone = drone_controller
        self.grok = grok_client
        self.log = get_logger('tools.flip')
    
    def execute(self, direction: str, skip_safety_check: bool = False, **kwargs) -> ToolResult:
        try:
            # === PRE-FLIP SAFETY CHECKS ===
            self.log.info(f"🛡️ Running pre-flip safety checks for {direction} flip...")
            
            # 1. Battery check (Tello requires ~50% for flips)
            battery = self.drone.get_battery()
            if battery < FLIP_MIN_BATTERY:
                return ToolResult(
                    success=False,
                    message=f"❌ Flip blocked: Battery too low ({battery}%). Tello needs {FLIP_MIN_BATTERY}%+ for flips.",
                    data={"blocked_by": "battery", "battery": battery, "required": FLIP_MIN_BATTERY}
                )
            self.log.info(f"✅ Battery OK: {battery}%")
            
            # 2. Height check (need altitude for flip)
            try:
                height = self.drone.drone.get_height()
                if height < FLIP_MIN_HEIGHT_CM:
                    return ToolResult(
                        success=False,
                        message=f"❌ Flip blocked: Altitude too low ({height}cm). Need {FLIP_MIN_HEIGHT_CM}cm+ for flip. Try 'move up 50' first!",
                        data={"blocked_by": "altitude", "height": height, "required": FLIP_MIN_HEIGHT_CM}
                    )
                self.log.info(f"✅ Altitude OK: {height}cm")
            except Exception as e:
                self.log.warning(f"Could not check height: {e}")
            
            # 3. Vision-based clearance check (CRITICAL!)
            if not skip_safety_check and self.grok and self.drone.video and self.drone.video.is_running:
                self.log.info("🔍 Running vision-based clearance check...")
                frame = self.drone.video.capture_snapshot()
                
                if frame is not None:
                    clearance = self.grok.check_clearance(
                        frame,
                        maneuver_type="flip",
                        required_clearance_cm=FLIP_MIN_CLEARANCE_CM
                    )
                    
                    if not clearance.safe_for_flip:
                        obstacles_desc = ", ".join([obs.name for obs in clearance.obstacles[:3]])
                        return ToolResult(
                            success=False,
                            message=f"❌ Flip blocked by vision check! Safety score: {clearance.overall_safety_score}/100. "
                                    f"Obstacles detected: {obstacles_desc or 'insufficient clearance'}. "
                                    f"Recommendation: {clearance.recommended_action}",
                            data={
                                "blocked_by": "vision",
                                "safety_score": clearance.overall_safety_score,
                                "obstacles": [obs.model_dump() for obs in clearance.obstacles],
                                "recommended_action": clearance.recommended_action
                            }
                        )
                    self.log.success(f"✅ Clearance OK: Safety score {clearance.overall_safety_score}/100")
                else:
                    self.log.warning("⚠️ Could not capture frame for safety check - proceeding with caution")
            elif skip_safety_check:
                self.log.warning("⚠️ Safety check skipped by user request!")
            
            # === EXECUTE FLIP ===
            self.log.info(f"🚀 All safety checks passed! Executing {direction} flip...")
            self.drone.flip(direction)
            
            return ToolResult(
                success=True,
                message=f"✅ Successfully executed {direction} flip! (Battery: {battery}%)",
                data={"direction": direction, "battery_after": self.drone.get_battery()}
            )
            
        except SafetyViolationError as e:
            return ToolResult(success=False, message=f"Flip blocked by controller: {str(e)}")
        except Exception as e:
            self.log.error(f"Flip failed: {e}")
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


def register_drone_tools(registry, drone_controller, grok_client=None):
    """
    Register all drone control tools.
    
    Args:
        registry: ToolRegistry instance
        drone_controller: DroneController instance
        grok_client: Optional GrokClient for vision-based safety checks
    """
    registry.register(TakeoffTool(drone_controller))
    registry.register(LandTool(drone_controller))
    registry.register(MoveTool(drone_controller, grok_client))  # With vision safety
    registry.register(RotateTool(drone_controller))
    registry.register(FlipTool(drone_controller, grok_client))  # With vision safety
    registry.register(HoverTool(drone_controller))
