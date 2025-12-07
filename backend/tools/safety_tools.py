"""
Safety tools for Grok-Pilot.
Provides vision-based obstacle detection and clearance checking.

SAFETY PHILOSOPHY:
- These tools help the drone understand its environment
- They should ALWAYS be called before risky maneuvers
- Results inform whether to proceed, modify, or abort actions
"""

from typing import Optional
from .base import BaseTool, ToolResult
from core.logger import get_logger


class CheckClearanceTool(BaseTool):
    """
    Check if the area is clear for a maneuver using vision.
    This is the primary safety tool - use it before any risky movement.
    """
    
    name = "check_clearance"
    description = "Scan surroundings using camera to check if safe for a maneuver. Returns detailed clearance data."
    parameters = {
        "type": "object",
        "properties": {
            "maneuver_type": {
                "type": "string",
                "enum": ["flip", "forward", "backward", "lateral", "vertical", "general"],
                "description": "Type of maneuver to check clearance for"
            }
        },
        "required": []
    }
    
    # Clearance requirements by maneuver type
    CLEARANCE_REQUIREMENTS = {
        "flip": 200,      # Flips need 2m clearance
        "forward": 100,   # Forward movement needs 1m
        "backward": 100,  # Backward movement (can't verify visually)
        "lateral": 80,    # Side movements need 80cm
        "vertical": 100,  # Up/down needs 1m
        "general": 100    # Default
    }
    
    def __init__(self, drone_controller, grok_client):
        super().__init__()
        self.drone = drone_controller
        self.grok = grok_client
        self.log = get_logger('tools.check_clearance')
    
    def execute(
        self,
        maneuver_type: str = "general",
        **kwargs
    ) -> ToolResult:
        self.log.info(f"{'='*50}")
        self.log.info(f"🛡️ CLEARANCE CHECK: {maneuver_type.upper()}")
        self.log.info(f"{'='*50}")
        
        # Get required clearance
        required_clearance_cm = self.CLEARANCE_REQUIREMENTS.get(maneuver_type, 100)
        self.log.info(f"Required clearance: {required_clearance_cm}cm")
        
        # Check video system
        if not self.grok:
            self.log.error("Vision AI not available")
            return ToolResult(
                success=False,
                message="❌ Vision AI not available - cannot perform safety check",
                data={"error": "no_grok_client"}
            )
        
        if not self.drone.video:
            self.log.error("Video stream not initialized")
            return ToolResult(
                success=False,
                message="❌ Video stream not initialized - cannot perform safety check",
                data={"error": "no_video_stream"}
            )
        
        if not self.drone.video.is_running:
            self.log.error("Video stream not running")
            return ToolResult(
                success=False,
                message="❌ Video stream not running - cannot perform safety check. Try restarting video.",
                data={"error": "video_not_running"}
            )
        
        # Capture frame
        try:
            frame = self.drone.video.capture_snapshot()
        except Exception as e:
            self.log.error(f"Frame capture failed: {e}")
            return ToolResult(
                success=False,
                message=f"❌ Camera capture failed: {e}",
                data={"error": "capture_failed", "exception": str(e)}
            )
        
        if frame is None:
            self.log.error("Frame is None")
            return ToolResult(
                success=False,
                message="❌ Camera returned empty frame - cannot perform safety check",
                data={"error": "empty_frame"}
            )
        
        # Run vision analysis
        try:
            result = self.grok.check_clearance(
                frame,
                maneuver_type=maneuver_type,
                required_clearance_cm=required_clearance_cm
            )
        except Exception as e:
            self.log.error(f"Vision analysis failed: {e}")
            return ToolResult(
                success=False,
                message=f"❌ Vision analysis failed: {e}",
                data={"error": "analysis_failed", "exception": str(e)}
            )
        
        # Build comprehensive data
        data = {
            "maneuver_type": maneuver_type,
            "required_clearance_cm": required_clearance_cm,
            "is_clear": result.is_clear,
            "safety_score": result.overall_safety_score,
            "clearance": {
                "front": result.front_clearance_cm,
                "left": result.left_clearance_cm,
                "right": result.right_clearance_cm,
                "above": result.above_clearance_cm,
                "below": result.below_clearance_cm
            },
            "safe_for": {
                "flip": result.safe_for_flip,
                "forward": result.safe_for_forward_movement,
                "lateral": result.safe_for_lateral_movement,
                "vertical": result.safe_for_vertical_movement
            },
            "obstacles": [obs.model_dump() for obs in result.obstacles],
            "hazards": result.hazards,
            "warnings": result.warnings,
            "recommended_action": result.recommended_action
        }
        
        # Build human-readable message
        if result.is_clear:
            message = f"✅ CLEAR for {maneuver_type}!\n\n"
            message += f"Safety Score: {result.overall_safety_score}/100\n"
            message += f"Clearance: Front {result.front_clearance_cm}cm, "
            message += f"Left {result.left_clearance_cm}cm, "
            message += f"Right {result.right_clearance_cm}cm\n"
            if maneuver_type == "flip":
                message += f"\n✅ Safe for flip: YES"
            self.log.success(f"✅ CLEAR - Safety score: {result.overall_safety_score}/100")
        else:
            obstacle_list = ", ".join([f"{obs.name} ({obs.position})" for obs in result.obstacles[:3]])
            message = f"⚠️ NOT SAFE for {maneuver_type}!\n\n"
            message += f"Safety Score: {result.overall_safety_score}/100\n"
            message += f"Obstacles: {obstacle_list or 'insufficient clearance'}\n"
            message += f"\nRecommendation: {result.recommended_action}"
            if result.warnings:
                message += f"\n\nWarnings:\n• " + "\n• ".join(result.warnings[:3])
            self.log.warning(f"⚠️ NOT SAFE - Score: {result.overall_safety_score}/100")
        
        self.log.info(f"{'='*50}")
        
        return ToolResult(
            success=True,  # The check succeeded (even if result is "not safe")
            message=message,
            data=data
        )


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
    """
    Comprehensive pre-flight/pre-maneuver safety check.
    
    Checks:
    1. Battery level and health
    2. Altitude (if flying)
    3. Vision-based obstacle scan
    4. Overall flight readiness
    
    Returns detailed report with pass/fail for each check.
    """
    
    name = "preflight_check"
    description = "Run comprehensive safety check: battery, altitude, obstacles. Call before risky operations."
    parameters = {
        "type": "object",
        "properties": {},
        "required": []
    }
    
    # Thresholds
    BATTERY_GOOD = 50
    BATTERY_WARNING = 30
    ALTITUDE_GOOD = 100
    ALTITUDE_WARNING = 50
    SAFETY_SCORE_GOOD = 70
    SAFETY_SCORE_WARNING = 50
    
    def __init__(self, drone_controller, grok_client):
        super().__init__()
        self.drone = drone_controller
        self.grok = grok_client
        self.log = get_logger('tools.preflight')
    
    def execute(self, **kwargs) -> ToolResult:
        self.log.info(f"{'='*60}")
        self.log.info(f"🛡️ PRE-FLIGHT SAFETY CHECK")
        self.log.info(f"{'='*60}")
        
        checks = []
        warnings = []
        critical_failures = []
        data = {}
        
        # === CHECK 1: BATTERY ===
        self.log.info("Check 1/3: Battery...")
        try:
            battery = self.drone.get_battery()
            data["battery"] = battery
            
            if battery >= self.BATTERY_GOOD:
                checks.append(f"✅ Battery: {battery}% (excellent)")
                self.log.success(f"  ✅ Battery: {battery}%")
            elif battery >= self.BATTERY_WARNING:
                checks.append(f"⚠️ Battery: {battery}% (moderate - avoid flips)")
                warnings.append(f"Battery at {battery}% - flip maneuvers disabled")
                self.log.warning(f"  ⚠️ Battery: {battery}%")
            else:
                checks.append(f"❌ Battery: {battery}% (CRITICAL - land soon!)")
                critical_failures.append("Battery critically low")
                self.log.error(f"  ❌ Battery: {battery}%")
        except Exception as e:
            checks.append(f"❌ Battery: Read failed ({e})")
            critical_failures.append(f"Cannot read battery: {e}")
            data["battery"] = -1
            self.log.error(f"  ❌ Battery read failed: {e}")
        
        # === CHECK 2: ALTITUDE ===
        self.log.info("Check 2/3: Altitude...")
        is_flying = self.drone.state_machine.is_flying()
        data["is_flying"] = is_flying
        
        if is_flying:
            try:
                height = self.drone.drone.get_height()
                data["altitude"] = height
                
                if height >= self.ALTITUDE_GOOD:
                    checks.append(f"✅ Altitude: {height}cm (good for all maneuvers)")
                    self.log.success(f"  ✅ Altitude: {height}cm")
                elif height >= self.ALTITUDE_WARNING:
                    checks.append(f"⚠️ Altitude: {height}cm (gain altitude for flips)")
                    warnings.append(f"Altitude {height}cm - need 100cm+ for flips")
                    self.log.warning(f"  ⚠️ Altitude: {height}cm")
                else:
                    checks.append(f"❌ Altitude: {height}cm (too low!)")
                    critical_failures.append(f"Altitude critically low ({height}cm)")
                    self.log.error(f"  ❌ Altitude: {height}cm")
            except Exception as e:
                checks.append(f"⚠️ Altitude: Read failed ({e})")
                warnings.append("Cannot read altitude sensor")
                data["altitude"] = -1
                self.log.warning(f"  ⚠️ Altitude read failed: {e}")
        else:
            checks.append("ℹ️ Altitude: N/A (grounded)")
            data["altitude"] = 0
            self.log.info("  ℹ️ Altitude: N/A (grounded)")
        
        # === CHECK 3: VISION/OBSTACLES ===
        self.log.info("Check 3/3: Obstacle scan...")
        
        vision_available = (
            self.grok is not None and 
            self.drone.video is not None and 
            self.drone.video.is_running
        )
        data["vision_available"] = vision_available
        
        if vision_available:
            try:
                frame = self.drone.video.capture_snapshot()
                if frame is not None:
                    clearance = self.grok.check_clearance(frame, "general", 100)
                    data["safety_score"] = clearance.overall_safety_score
                    data["obstacles"] = [obs.model_dump() for obs in clearance.obstacles]
                    
                    if clearance.is_clear and clearance.overall_safety_score >= self.SAFETY_SCORE_GOOD:
                        checks.append(f"✅ Obstacles: Clear (score: {clearance.overall_safety_score}/100)")
                        self.log.success(f"  ✅ Obstacles: Clear ({clearance.overall_safety_score}/100)")
                    elif clearance.overall_safety_score >= self.SAFETY_SCORE_WARNING:
                        obstacle_names = ", ".join([obs.name for obs in clearance.obstacles[:2]]) or "obstacles nearby"
                        checks.append(f"⚠️ Obstacles: Caution ({clearance.overall_safety_score}/100) - {obstacle_names}")
                        warnings.append(f"Obstacles detected: {obstacle_names}")
                        if clearance.hazards:
                            for hazard in clearance.hazards[:2]:
                                warnings.append(f"Hazard: {hazard}")
                        self.log.warning(f"  ⚠️ Obstacles detected ({clearance.overall_safety_score}/100)")
                    else:
                        obstacle_names = ", ".join([obs.name for obs in clearance.obstacles[:2]]) or "obstacles"
                        checks.append(f"❌ Obstacles: DANGER ({clearance.overall_safety_score}/100) - {obstacle_names}")
                        critical_failures.append(f"Dangerous obstacles: {obstacle_names}")
                        warnings.append(f"Recommendation: {clearance.recommended_action}")
                        self.log.error(f"  ❌ Obstacles: DANGER ({clearance.overall_safety_score}/100)")
                else:
                    checks.append("⚠️ Obstacles: Camera returned empty frame")
                    warnings.append("Could not capture frame for obstacle check")
                    data["safety_score"] = -1
                    self.log.warning("  ⚠️ Camera returned empty frame")
            except Exception as e:
                checks.append(f"⚠️ Obstacles: Check failed ({e})")
                warnings.append(f"Vision check failed: {e}")
                data["safety_score"] = -1
                self.log.warning(f"  ⚠️ Vision check failed: {e}")
        else:
            checks.append("⚠️ Obstacles: Vision system unavailable")
            warnings.append("Cannot check obstacles - fly with extra caution!")
            data["safety_score"] = -1
            self.log.warning("  ⚠️ Vision system unavailable")
        
        # === BUILD RESULT ===
        all_passed = len(critical_failures) == 0
        data["all_passed"] = all_passed
        data["checks"] = checks
        data["warnings"] = warnings
        data["critical_failures"] = critical_failures
        
        # Build message
        if all_passed and len(warnings) == 0:
            status = "✅ PRE-FLIGHT CHECK: ALL CLEAR"
            self.log.success("✅ ALL CHECKS PASSED")
        elif all_passed:
            status = "⚠️ PRE-FLIGHT CHECK: PASSED WITH WARNINGS"
            self.log.warning("⚠️ PASSED WITH WARNINGS")
        else:
            status = "❌ PRE-FLIGHT CHECK: FAILED"
            self.log.error("❌ CHECK FAILED - CRITICAL ISSUES")
        
        message = f"{status}\n{'='*40}\n\n"
        message += "\n".join(checks)
        
        if warnings:
            message += f"\n\n⚠️ WARNINGS:\n• " + "\n• ".join(warnings)
        
        if critical_failures:
            message += f"\n\n❌ CRITICAL ISSUES:\n• " + "\n• ".join(critical_failures)
            message += "\n\n🛑 Resolve critical issues before proceeding!"
        
        # Add recommendations
        if all_passed:
            if data.get("battery", 100) >= 50 and data.get("altitude", 0) >= 100:
                message += "\n\n✅ Ready for all maneuvers including flips!"
            elif data.get("battery", 100) >= 50:
                message += "\n\n✅ Ready for normal flight. Gain altitude for flips."
            else:
                message += "\n\n✅ Ready for careful flight. Avoid aggressive maneuvers."
        
        self.log.info(f"{'='*60}")
        
        return ToolResult(
            success=True,  # The check itself succeeded
            message=message,
            data=data
        )


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

