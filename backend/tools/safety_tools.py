"""
Safety tools for Grok-Pilot.
Provides vision-based obstacle detection and clearance checking.
"""

from typing import Optional
from .base import BaseTool, ToolResult
from core.logger import get_logger


class CheckClearanceTool(BaseTool):
    """Check if the area is clear for a maneuver using vision."""
    
    name = "check_clearance"
    description = "Use the camera to check if the area is clear for a maneuver. ALWAYS call this before flips, fast movements, or when unsure about surroundings."
    parameters = {
        "type": "object",
        "properties": {
            "maneuver_type": {
                "type": "string",
                "enum": ["flip", "forward", "backward", "lateral", "vertical", "general"],
                "description": "Type of maneuver to check clearance for",
                "default": "general"
            },
            "required_clearance_cm": {
                "type": "integer",
                "description": "Required clearance in centimeters (default: 100, flip needs 200)",
                "minimum": 50,
                "maximum": 500,
                "default": 100
            }
        },
        "required": []
    }
    
    def __init__(self, drone_controller, grok_client):
        super().__init__()
        self.drone = drone_controller
        self.grok = grok_client
        self.log = get_logger('tools.check_clearance')
    
    def execute(
        self,
        maneuver_type: str = "general",
        required_clearance_cm: int = 100,
        **kwargs
    ) -> ToolResult:
        try:
            if not self.drone.video or not self.drone.video.is_running:
                return ToolResult(
                    success=False,
                    message="Video stream not available for safety check"
                )
            
            # Capture current frame
            frame = self.drone.video.capture_snapshot()
            if frame is None:
                return ToolResult(
                    success=False,
                    message="Could not capture frame for safety check"
                )
            
            # Adjust required clearance based on maneuver
            if maneuver_type == "flip" and required_clearance_cm < 200:
                required_clearance_cm = 200  # Flips need more space
                self.log.info("Increased clearance requirement to 200cm for flip")
            
            # Run clearance check
            result = self.grok.check_clearance(
                frame,
                maneuver_type=maneuver_type,
                required_clearance_cm=required_clearance_cm
            )
            
            # Build response message
            if result.is_clear:
                message = f"✅ CLEAR for {maneuver_type}! Safety score: {result.overall_safety_score}/100"
            else:
                message = f"⚠️ NOT SAFE for {maneuver_type}! Safety score: {result.overall_safety_score}/100\n"
                message += f"Recommended action: {result.recommended_action}"
                if result.warnings:
                    message += f"\nWarnings: {'; '.join(result.warnings[:3])}"
            
            return ToolResult(
                success=True,
                message=message,
                data={
                    "is_clear": result.is_clear,
                    "safety_score": result.overall_safety_score,
                    "safe_for_flip": result.safe_for_flip,
                    "safe_for_forward": result.safe_for_forward_movement,
                    "safe_for_lateral": result.safe_for_lateral_movement,
                    "safe_for_vertical": result.safe_for_vertical_movement,
                    "front_clearance_cm": result.front_clearance_cm,
                    "left_clearance_cm": result.left_clearance_cm,
                    "right_clearance_cm": result.right_clearance_cm,
                    "above_clearance_cm": result.above_clearance_cm,
                    "below_clearance_cm": result.below_clearance_cm,
                    "obstacles": [obs.model_dump() for obs in result.obstacles],
                    "hazards": result.hazards,
                    "warnings": result.warnings,
                    "recommended_action": result.recommended_action
                }
            )
        except Exception as e:
            self.log.error(f"Clearance check failed: {e}")
            return ToolResult(success=False, message=f"Clearance check failed: {str(e)}")


class QuickSafetyCheckTool(BaseTool):
    """Quick safety scan - faster than full clearance check."""
    
    name = "quick_safety_check"
    description = "Quick scan for immediate obstacles. Use for routine movement, not for risky maneuvers like flips."
    parameters = {
        "type": "object",
        "properties": {},
        "required": []
    }
    
    def __init__(self, drone_controller, grok_client):
        super().__init__()
        self.drone = drone_controller
        self.grok = grok_client
        self.log = get_logger('tools.quick_safety')
    
    def execute(self, **kwargs) -> ToolResult:
        try:
            if not self.drone.video or not self.drone.video.is_running:
                return ToolResult(
                    success=False,
                    message="Video stream not available"
                )
            
            frame = self.drone.video.capture_snapshot()
            if frame is None:
                return ToolResult(success=False, message="Could not capture frame")
            
            result = self.grok.quick_obstacle_check(frame)
            
            if result['safe']:
                return ToolResult(
                    success=True,
                    message="✅ Quick check: Area appears safe",
                    data={"safe": True, "details": result['response']}
                )
            else:
                return ToolResult(
                    success=True,
                    message=f"⚠️ Warning: {result['warning']}",
                    data={"safe": False, "warning": result['warning']}
                )
        except Exception as e:
            return ToolResult(success=False, message=f"Safety check failed: {str(e)}")


class PreFlightCheckTool(BaseTool):
    """Comprehensive pre-flight safety check."""
    
    name = "preflight_check"
    description = "Run a comprehensive pre-flight safety check including battery, altitude, and obstacle detection. Call this before takeoff or risky operations."
    parameters = {
        "type": "object",
        "properties": {},
        "required": []
    }
    
    def __init__(self, drone_controller, grok_client):
        super().__init__()
        self.drone = drone_controller
        self.grok = grok_client
        self.log = get_logger('tools.preflight')
    
    def execute(self, **kwargs) -> ToolResult:
        checks = []
        warnings = []
        all_passed = True
        
        try:
            # 1. Battery check
            battery = self.drone.get_battery()
            if battery >= 50:
                checks.append(f"✅ Battery: {battery}% (good)")
            elif battery >= 30:
                checks.append(f"⚠️ Battery: {battery}% (moderate)")
                warnings.append("Battery is below 50% - avoid flips")
            else:
                checks.append(f"❌ Battery: {battery}% (low!)")
                warnings.append("Battery too low for safe flight - land soon!")
                all_passed = False
            
            # 2. Height check (if flying)
            if self.drone.state_machine.is_flying():
                try:
                    height = self.drone.drone.get_height()
                    if height >= 100:
                        checks.append(f"✅ Altitude: {height}cm (good for maneuvers)")
                    elif height >= 50:
                        checks.append(f"⚠️ Altitude: {height}cm (gain altitude before flips)")
                        warnings.append("Altitude too low for flip maneuvers")
                    else:
                        checks.append(f"❌ Altitude: {height}cm (too low!)")
                        warnings.append("Altitude critically low!")
                        all_passed = False
                except:
                    checks.append("⚠️ Altitude: Unable to read")
            else:
                checks.append("ℹ️ Altitude: N/A (not flying)")
            
            # 3. Vision-based obstacle check (if video available)
            if self.drone.video and self.drone.video.is_running:
                frame = self.drone.video.capture_snapshot()
                if frame is not None:
                    clearance = self.grok.check_clearance(frame, "general", 100)
                    if clearance.is_clear and clearance.overall_safety_score >= 70:
                        checks.append(f"✅ Obstacles: Clear (score: {clearance.overall_safety_score}/100)")
                    elif clearance.overall_safety_score >= 50:
                        checks.append(f"⚠️ Obstacles: Caution needed (score: {clearance.overall_safety_score}/100)")
                        for hazard in clearance.hazards[:2]:
                            warnings.append(f"Hazard: {hazard}")
                    else:
                        checks.append(f"❌ Obstacles: Dangerous! (score: {clearance.overall_safety_score}/100)")
                        warnings.append(f"Obstacle danger: {clearance.recommended_action}")
                        all_passed = False
                else:
                    checks.append("⚠️ Obstacles: Couldn't capture image")
            else:
                checks.append("⚠️ Obstacles: Video not available")
                warnings.append("Cannot check obstacles - fly carefully!")
            
            # Build result message
            status = "✅ PRE-FLIGHT CHECK PASSED" if all_passed else "⚠️ PRE-FLIGHT CHECK - ISSUES FOUND"
            message = f"{status}\n\n" + "\n".join(checks)
            if warnings:
                message += "\n\n⚠️ WARNINGS:\n• " + "\n• ".join(warnings)
            
            return ToolResult(
                success=True,
                message=message,
                data={
                    "all_passed": all_passed,
                    "checks": checks,
                    "warnings": warnings,
                    "battery": battery
                }
            )
        except Exception as e:
            return ToolResult(success=False, message=f"Pre-flight check failed: {str(e)}")


def register_safety_tools(registry, drone_controller, grok_client):
    """
    Register all safety tools.
    
    Args:
        registry: ToolRegistry instance
        drone_controller: DroneController instance
        grok_client: GrokClient instance
    """
    registry.register(CheckClearanceTool(drone_controller, grok_client))
    registry.register(QuickSafetyCheckTool(drone_controller, grok_client))
    registry.register(PreFlightCheckTool(drone_controller, grok_client))

