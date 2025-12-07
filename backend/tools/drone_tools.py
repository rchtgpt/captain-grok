"""
Drone control tools for Grok-Pilot.
Provides movement commands as callable tools.
All risky maneuvers include MANDATORY vision-based safety checks.
Movements update spatial memory for tracking.

SAFETY PHILOSOPHY:
- If we can't verify it's safe, we DON'T do it
- No silent failures - always explain why something was blocked
- Conservative estimates - better to block a safe maneuver than crash
"""

from typing import Optional
from .base import BaseTool, ToolResult
from core.logger import get_logger
from core.exceptions import SafetyViolationError
from core.memory import get_memory


# =============================================================================
# SAFETY CONSTANTS - DO NOT MODIFY WITHOUT TESTING
# =============================================================================
FLIP_MIN_BATTERY = 50       # Tello hardware requirement for flips
FLIP_MIN_HEIGHT_CM = 100    # Need at least 1m altitude for flip
FLIP_MIN_CLEARANCE_CM = 200 # Need 2m clearance all directions for flip
FLIP_MIN_SAFETY_SCORE = 60  # Minimum vision safety score to allow flip

MOVE_MIN_CLEARANCE_CM = 50  # Minimum clearance before blocking movement
MOVE_SAFETY_BUFFER_CM = 30  # Extra buffer when reducing movement distance
MOVE_AUTO_CHECK_THRESHOLD = 40  # Auto-check obstacles for moves > this distance

# Directions that REQUIRE obstacle checking (can't see behind us)
CHECKABLE_DIRECTIONS = ['forward', 'left', 'right']


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
            import time
            
            # Check if already flying - don't reset memory or takeoff again!
            if self.drone.state_machine.is_flying():
                self.log.info("Already airborne - skipping takeoff")
                return ToolResult(
                    success=True,
                    message="Already airborne! Ready to proceed.",
                    data={"status": "already_flying", "skipped": True}
                )
            
            self.drone.takeoff()
            self.log.info("Takeoff complete, stabilizing...")
            
            # Longer pause to stabilize - Tello needs time after takeoff
            time.sleep(2.0)
            
            # Rise ABOVE eye level using RC control (more reliable after takeoff)
            # The discrete move_up command often fails with "Not joystick" error
            # after takeoff, but RC control works consistently
            # Target: ~160cm (above eye level for better view)
            self.log.info("Rising above eye level (+110cm) using RC control...")
            
            # Calculate rise time: ~110cm at throttle 40 takes about 3.2 seconds
            # Tello rises ~30-35cm/s at throttle 40
            rise_duration = 3.2
            start_time = time.time()
            
            while time.time() - start_time < rise_duration:
                # Throttle only (0, 0, vertical_speed, 0)
                self.drone.drone.send_rc_control(0, 0, 40, 0)
                time.sleep(0.05)  # 20Hz update rate
            
            # Stop vertical movement
            self.drone.drone.send_rc_control(0, 0, 0, 0)
            time.sleep(0.3)  # Brief settle time
            
            self.log.success("Above eye level (~160cm), stabilizing...")
            
            # Reset memory position on takeoff
            memory = get_memory()
            memory.reset_position()
            
            return ToolResult(
                success=True,
                message="Airborne above eye level (~160cm)! Ready to search.",
                data={"height": 160, "status": "hovering"}
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
    """
    Move the drone with COMPREHENSIVE obstacle avoidance.
    
    EVERY movement is checked for obstacles:
    - Forward: Direct vision check
    - Left/Right: Vision check (camera can see periphery)
    - Back: ROTATE first to check, then rotate back and move
    - Up: Check for ceiling obstacles
    - Down: Check for floor/ground obstacles
    
    The drone will NEVER blindly move into an obstacle.
    """
    
    name = "move"
    description = "Move drone safely. ALL movements are checked for obstacles using camera vision. Will block or reduce distance if obstacles detected."
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
    
    def __init__(self, drone_controller, grok_client=None):
        super().__init__()
        self.drone = drone_controller
        self.grok = grok_client
        self.log = get_logger('tools.move')
    
    def _has_vision(self) -> bool:
        """Check if vision system is available."""
        return (
            self.grok is not None and 
            self.drone.video is not None and 
            self.drone.video.is_running
        )
    
    def _capture_frame(self):
        """Safely capture a frame from the camera."""
        try:
            frame = self.drone.video.capture_snapshot()
            return frame
        except Exception as e:
            self.log.warning(f"Frame capture failed: {e}")
            return None
    
    def _check_forward(self, distance: int) -> tuple[bool, int, str, dict]:
        """Check clearance for forward movement."""
        self.log.info("🔍 Checking FORWARD clearance...")
        
        if not self._has_vision():
            safe_dist = min(25, distance)
            self.log.warning(f"⚠️ SAFETY: No vision system - limiting forward to {safe_dist}cm")
            return True, safe_dist, f"⚠️ No vision - limited to {safe_dist}cm", {"warning": "no_vision"}
        
        frame = self._capture_frame()
        if frame is None:
            self.log.warning("⚠️ SAFETY: Camera error - limiting forward movement")
            return True, min(25, distance), "⚠️ Camera error - limited movement", {"warning": "camera_error"}
        
        try:
            clearance = self.grok.check_clearance(frame, "forward", distance + MOVE_SAFETY_BUFFER_CM)
            
            data = {
                "safety_score": clearance.overall_safety_score,
                "front_clearance": clearance.front_clearance_cm,
                "obstacles": [obs.model_dump() for obs in clearance.obstacles]
            }
            
            # Log all detected obstacles
            if clearance.obstacles:
                self.log.info(f"   Detected obstacles: {[o.name for o in clearance.obstacles]}")
            
            # Check if path is clear
            if clearance.safe_for_forward_movement:
                if clearance.front_clearance_cm >= distance + MOVE_SAFETY_BUFFER_CM or clearance.front_clearance_cm < 0:
                    self.log.success(f"✅ SAFE: Forward path clear (score: {clearance.overall_safety_score}/100)")
                    return True, distance, f"✅ Path clear ahead (score: {clearance.overall_safety_score}/100)", data
            
            # Obstacle detected - can we reduce distance?
            if clearance.front_clearance_cm > MOVE_MIN_CLEARANCE_CM:
                safe_dist = max(20, clearance.front_clearance_cm - MOVE_SAFETY_BUFFER_CM)
                obstacles = ", ".join([o.name for o in clearance.obstacles[:2]]) or "obstacle"
                self.log.warning(f"⚠️ OBSTACLE AHEAD: {obstacles} at ~{clearance.front_clearance_cm}cm")
                self.log.warning(f"⚠️ SAFETY: Reducing forward distance from {distance}cm to {safe_dist}cm")
                return True, safe_dist, f"⚠️ {obstacles} at ~{clearance.front_clearance_cm}cm - reduced to {safe_dist}cm", data
            
            # Too close - block
            obstacles = ", ".join([o.name for o in clearance.obstacles[:2]]) or "obstacle"
            self.log.error(f"🚨 BLOCKED: {obstacles} only {clearance.front_clearance_cm}cm ahead!")
            self.log.error(f"🚨 SAFETY: Forward movement BLOCKED to prevent collision!")
            return False, 0, f"❌ BLOCKED: {obstacles} only {clearance.front_clearance_cm}cm ahead!", data
            
        except Exception as e:
            self.log.error(f"Vision check failed: {e}")
            self.log.warning("⚠️ SAFETY: Vision error - limiting to 25cm")
            return True, min(25, distance), f"⚠️ Vision error - limited to 25cm", {"error": str(e)}
    
    def _check_lateral(self, direction: str, distance: int) -> tuple[bool, int, str, dict]:
        """Check clearance for left/right movement."""
        self.log.info(f"🔍 Checking {direction.upper()} clearance...")
        
        if not self._has_vision():
            safe_dist = min(25, distance)
            self.log.warning(f"⚠️ SAFETY: No vision system - limiting {direction} to {safe_dist}cm")
            return True, safe_dist, f"⚠️ No vision - limited to {safe_dist}cm", {"warning": "no_vision"}
        
        frame = self._capture_frame()
        if frame is None:
            self.log.warning(f"⚠️ SAFETY: Camera error - limiting {direction} movement")
            return True, min(25, distance), "⚠️ Camera error - limited movement", {"warning": "camera_error"}
        
        try:
            clearance = self.grok.check_clearance(frame, "lateral", distance + MOVE_SAFETY_BUFFER_CM)
            
            clearance_cm = clearance.left_clearance_cm if direction == "left" else clearance.right_clearance_cm
            
            data = {
                "safety_score": clearance.overall_safety_score,
                f"{direction}_clearance": clearance_cm,
                "obstacles": [obs.model_dump() for obs in clearance.obstacles]
            }
            
            # Log all detected obstacles
            if clearance.obstacles:
                self.log.info(f"   Detected obstacles: {[o.name for o in clearance.obstacles]}")
            
            # Check if path is clear
            if clearance.safe_for_lateral_movement:
                if clearance_cm >= distance + MOVE_SAFETY_BUFFER_CM or clearance_cm < 0:
                    self.log.success(f"✅ SAFE: {direction.capitalize()} path clear (score: {clearance.overall_safety_score}/100)")
                    return True, distance, f"✅ Path clear {direction} (score: {clearance.overall_safety_score}/100)", data
            
            # Obstacle detected - can we reduce distance?
            if clearance_cm > MOVE_MIN_CLEARANCE_CM:
                safe_dist = max(20, clearance_cm - MOVE_SAFETY_BUFFER_CM)
                obstacles = ", ".join([o.name for o in clearance.obstacles[:2]]) or "obstacle"
                self.log.warning(f"⚠️ OBSTACLE {direction.upper()}: {obstacles} at ~{clearance_cm}cm")
                self.log.warning(f"⚠️ SAFETY: Reducing {direction} distance from {distance}cm to {safe_dist}cm")
                return True, safe_dist, f"⚠️ {obstacles} {direction} at ~{clearance_cm}cm - reduced to {safe_dist}cm", data
            
            # Too close - block
            obstacles = ", ".join([o.name for o in clearance.obstacles[:2]]) or "obstacle"
            self.log.error(f"🚨 BLOCKED: {obstacles} only {clearance_cm}cm to the {direction}!")
            self.log.error(f"🚨 SAFETY: {direction.capitalize()} movement BLOCKED to prevent collision!")
            return False, 0, f"❌ BLOCKED: {obstacles} only {clearance_cm}cm to the {direction}!", data
            
        except Exception as e:
            self.log.error(f"Vision check failed: {e}")
            self.log.warning(f"⚠️ SAFETY: Vision error - limiting {direction} to 25cm")
            return True, min(25, distance), f"⚠️ Vision error - limited to 25cm", {"error": str(e)}
    
    def _execute_backward_smart(self, distance: int) -> tuple[bool, int, str, dict]:
        """
        SMART backward movement: Rotate → Check → Move FORWARD (stay facing new direction).
        
        Why this is smart:
        1. We're LOOKING at where we're going when we move
        2. Moving forward is more reliable than backward on Tello
        3. NO unnecessary rotation back - drone stays facing new direction
        4. If user wants to continue moving that way, no rotation needed!
        
        The drone will be facing the opposite direction after this move.
        That's intentional - it's more efficient for exploration sequences.
        
        Returns: (success, distance_moved, message, data)
        """
        self.log.info("🔍 SMART BACKWARD: Rotate 180° → Check → Move Forward (stay facing new direction)")
        
        if not self._has_vision():
            safe_dist = min(20, distance)
            self.log.warning(f"⚠️ SAFETY: No vision - backward is DANGEROUS without eyes!")
            self.log.warning(f"⚠️ SAFETY: Limiting backward to {safe_dist}cm (can't see behind)")
            return False, safe_dist, f"⚠️ No vision - backward limited to {safe_dist}cm", {"warning": "no_vision_backward", "use_blind_backup": True}
        
        try:
            # Step 1: Rotate 180° to face the direction we want to move
            self.log.info("🔄 Step 1: Rotating 180° to face movement direction...")
            self.drone.rotate(180)
            
            # Step 2: Check clearance (now looking at where we want to go)
            self.log.info("🔍 Step 2: Checking clearance ahead...")
            frame = self._capture_frame()
            if frame is None:
                self.log.warning("⚠️ SAFETY: Camera error - rotating back and aborting")
                self.drone.rotate(180)  # Rotate back since we didn't move
                return False, 0, "⚠️ Camera error during backward check", {"warning": "camera_error", "use_blind_backup": True}
            
            clearance = self.grok.check_clearance(frame, "forward", distance + MOVE_SAFETY_BUFFER_CM)
            
            data = {
                "safety_score": clearance.overall_safety_score,
                "clearance_cm": clearance.front_clearance_cm,
                "obstacles": [obs.model_dump() for obs in clearance.obstacles],
                "smart_backward": True,
                "orientation_changed": True  # Drone is now facing opposite direction
            }
            
            # Log detected obstacles
            if clearance.obstacles:
                self.log.info(f"   Detected in path: {[o.name for o in clearance.obstacles]}")
            
            # Determine safe distance
            actual_distance = distance
            if not clearance.safe_for_forward_movement or (clearance.front_clearance_cm > 0 and clearance.front_clearance_cm < distance + MOVE_SAFETY_BUFFER_CM):
                if clearance.front_clearance_cm > MOVE_MIN_CLEARANCE_CM:
                    actual_distance = max(20, clearance.front_clearance_cm - MOVE_SAFETY_BUFFER_CM)
                    obstacles = ", ".join([o.name for o in clearance.obstacles[:2]]) or "obstacle"
                    self.log.warning(f"⚠️ OBSTACLE: {obstacles} at ~{clearance.front_clearance_cm}cm")
                    self.log.warning(f"⚠️ SAFETY: Reducing distance from {distance}cm to {actual_distance}cm")
                elif clearance.front_clearance_cm > 0:
                    # Too close - abort and rotate back (since we didn't move)
                    obstacles = ", ".join([o.name for o in clearance.obstacles[:2]]) or "obstacle"
                    self.log.error(f"🚨 BLOCKED: {obstacles} only {clearance.front_clearance_cm}cm away!")
                    self.log.error(f"🚨 SAFETY: Movement BLOCKED - rotating back to original orientation")
                    self.drone.rotate(180)  # Only rotate back because we DIDN'T move
                    data["orientation_changed"] = False
                    return False, 0, f"❌ BLOCKED: {obstacles} only {clearance.front_clearance_cm}cm in that direction!", data
            
            # Step 3: Move FORWARD (we're now facing the direction we want to go)
            self.log.info(f"🚀 Step 3: Moving forward {actual_distance}cm...")
            self.drone.move("forward", actual_distance)
            
            # NO Step 4 - we stay facing this direction!
            # This is intentional - more efficient for sequences
            
            self.log.success(f"✅ SMART BACKWARD complete: moved {actual_distance}cm")
            self.log.info(f"ℹ️ Drone is now facing the opposite direction (efficient for continued exploration)")
            
            msg = f"✅ Moved backward {actual_distance}cm (now facing opposite direction)"
            if actual_distance != distance:
                msg = f"⚠️ Moved backward {actual_distance}cm (reduced from {distance}cm) - now facing opposite direction"
            
            data["distance_moved"] = actual_distance
            return True, actual_distance, msg, data
            
        except Exception as e:
            self.log.error(f"Smart backward failed: {e}")
            self.log.warning("⚠️ Movement failed - orientation may have changed")
            return False, 0, f"❌ Backward movement failed: {e}", {"error": str(e), "orientation_unknown": True}
    
    def _check_vertical(self, direction: str, distance: int) -> tuple[bool, int, str, dict]:
        """
        Vertical movement (up/down) - NO VISION CHECK.
        
        Camera faces FORWARD - it cannot see above or below.
        Vision-based vertical checks are unreliable and cause false blocks.
        
        Just allow the movement. Tello has its own altitude limits.
        """
        self.log.info(f"✅ {direction.upper()} movement allowed (no vision check - camera faces forward)")
        return True, distance, f"✅ Moving {direction} {distance}cm", {
            "direction": direction,
            "vision_check_skipped": True,
            "reason": "Camera faces forward, cannot verify vertical clearance"
        }
    
    def execute(self, direction: str, distance: int, **kwargs) -> ToolResult:
        """Execute movement with comprehensive obstacle checking."""
        
        # Clamp distance
        original_distance = distance
        distance = max(20, min(100, distance))
        
        self.log.info(f"{'='*60}")
        self.log.info(f"🚁 MOVE REQUEST: {direction.upper()} {distance}cm")
        self.log.info(f"{'='*60}")
        
        try:
            # === BACKWARD is special - uses smart rotate+forward method ===
            if direction == "back":
                success, actual_distance, message, data = self._execute_backward_smart(distance)
                
                # Check if we need fallback to blind backward (no vision)
                if not success and data.get("use_blind_backup"):
                    fallback_dist = data.get("warning", "").split("limited to ")[1].split("cm")[0] if "limited to" in str(data.get("warning", "")) else 20
                    fallback_dist = min(20, distance)  # Max 20cm blind
                    self.log.warning(f"⚠️ Using limited blind backward: {fallback_dist}cm")
                    self.drone.move("back", fallback_dist)
                    return ToolResult(
                        success=True,
                        message=f"⚠️ Moved back {fallback_dist}cm (limited - no vision available)",
                        data={"direction": "back", "distance": fallback_dist, "blind_move": True}
                    )
                
                if success:
                    self.log.success(f"{'='*60}")
                    self.log.success(f"✅ BACKWARD MOVE COMPLETE: {actual_distance}cm")
                    self.log.success(f"{'='*60}")
                    return ToolResult(success=True, message=message, data=data)
                else:
                    self.log.error(f"{'='*60}")
                    self.log.error(f"🚨 BACKWARD BLOCKED: {message}")
                    self.log.error(f"{'='*60}")
                    return ToolResult(success=False, message=message, data=data)
            
            # === OTHER DIRECTIONS: Check then move ===
            if direction == "forward":
                can_move, safe_distance, message, data = self._check_forward(distance)
            elif direction in ["left", "right"]:
                can_move, safe_distance, message, data = self._check_lateral(direction, distance)
            elif direction in ["up", "down"]:
                can_move, safe_distance, message, data = self._check_vertical(direction, distance)
            else:
                self.log.error(f"❌ Invalid direction: {direction}")
                return ToolResult(success=False, message=f"❌ Invalid direction: {direction}")
            
            # === BLOCKED? ===
            if not can_move:
                self.log.error(f"{'='*60}")
                self.log.error(f"🚨🚨🚨 MOVEMENT BLOCKED - COLLISION PREVENTED! 🚨🚨🚨")
                self.log.error(f"   Direction: {direction}")
                self.log.error(f"   Requested: {distance}cm")
                self.log.error(f"   Reason: {message}")
                self.log.error(f"{'='*60}")
                return ToolResult(
                    success=False,
                    message=message,
                    data={"blocked": True, "direction": direction, "requested_distance": distance, **data}
                )
            
            # === DISTANCE REDUCED? ===
            if safe_distance != distance:
                self.log.warning(f"{'='*60}")
                self.log.warning(f"⚠️ DISTANCE REDUCED FOR SAFETY")
                self.log.warning(f"   Direction: {direction}")
                self.log.warning(f"   Requested: {distance}cm → Allowed: {safe_distance}cm")
                self.log.warning(f"   Reason: {message}")
                self.log.warning(f"{'='*60}")
                distance = safe_distance
            
            # === EXECUTE MOVEMENT ===
            self.log.info(f"🚀 EXECUTING: move {direction} {distance}cm")
            self.drone.move(direction, distance)
            
            self.log.success(f"{'='*60}")
            self.log.success(f"✅ MOVE COMPLETE: {direction} {distance}cm")
            self.log.success(f"{'='*60}")
            
            result_msg = f"✅ Moved {direction} {distance}cm"
            if distance != original_distance:
                result_msg += f" (reduced from {original_distance}cm for safety)"
            
            return ToolResult(
                success=True,
                message=result_msg,
                data={"direction": direction, "distance": distance, "original_distance": original_distance, **data}
            )
            
        except SafetyViolationError as e:
            self.log.error(f"🚨 Movement blocked by controller: {e}")
            return ToolResult(success=False, message=f"❌ Blocked: {str(e)}")
        except Exception as e:
            self.log.error(f"🚨 Movement failed: {e}")
            return ToolResult(success=False, message=f"❌ Failed: {str(e)}")


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
            
            # Update memory heading (recalculates all entity positions)
            memory = get_memory()
            memory.update_heading(degrees)
            
            direction = "clockwise" if degrees > 0 else "counter-clockwise"
            return ToolResult(
                success=True,
                message=f"Rotated {abs(degrees)}° {direction}",
                data={"degrees": degrees, "direction": direction, "new_heading": memory.heading}
            )
        except Exception as e:
            return ToolResult(success=False, message=f"Rotation failed: {str(e)}")


class FlipTool(BaseTool):
    """
    Perform a flip maneuver with safety checks.
    
    A flip will execute if:
    1. Battery >= 50%
    2. Altitude >= 100cm  
    3. Front clearance > 50cm (simple check - if there's space ahead, flip is OK)
    
    We don't use overly conservative safety scores - just check actual clearance.
    """
    
    name = "flip"
    description = "Perform a flip (forward/back/left/right). REQUIRES: battery>50%, altitude>100cm, >50cm clearance ahead."
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
    
    # Minimum clearance for flip (50cm is plenty for a Tello flip)
    FLIP_MIN_CLEARANCE = 50
    
    def __init__(self, drone_controller, grok_client=None):
        super().__init__()
        self.drone = drone_controller
        self.grok = grok_client
        self.log = get_logger('tools.flip')
    
    def _check_battery(self) -> tuple[bool, int, str]:
        """Check battery level. Returns (passed, level, message)."""
        try:
            battery = self.drone.get_battery()
            if battery < FLIP_MIN_BATTERY:
                return False, battery, f"Battery {battery}% is below {FLIP_MIN_BATTERY}% minimum"
            return True, battery, f"Battery {battery}% OK"
        except Exception as e:
            return False, 0, f"Could not read battery: {e}"
    
    def _check_altitude(self) -> tuple[bool, int, str]:
        """Check altitude. Returns (passed, height, message)."""
        try:
            height = self.drone.drone.get_height()
            if height < FLIP_MIN_HEIGHT_CM:
                return False, height, f"Altitude {height}cm is below {FLIP_MIN_HEIGHT_CM}cm minimum. Use 'move up' first!"
            return True, height, f"Altitude {height}cm OK"
        except Exception as e:
            # CAN'T CHECK HEIGHT = CAN'T FLIP (fail safe)
            return False, -1, f"Could not read altitude: {e}. Cannot verify safe flip height."
    
    def _check_vision_clearance(self) -> tuple[bool, dict, str]:
        """
        Check clearance using vision. Returns (passed, data, message).
        
        SIMPLE RULE: If front clearance > 50cm, flip is allowed.
        We don't use overly conservative safety scores.
        """
        # Check if vision system is available - if not, ALLOW flip (don't block on vision)
        if not self.grok or not self.drone.video or not self.drone.video.is_running:
            self.log.warning("⚠️ Vision not available - allowing flip (battery/altitude checks passed)")
            return True, {"vision_skipped": True}, "Vision not available - allowing flip based on battery/altitude"
        
        # Capture frame
        try:
            frame = self.drone.video.capture_snapshot()
        except Exception as e:
            self.log.warning(f"⚠️ Frame capture failed - allowing flip: {e}")
            return True, {"vision_skipped": True, "error": str(e)}, "Frame capture failed - allowing flip"
        
        if frame is None:
            self.log.warning("⚠️ Empty frame - allowing flip")
            return True, {"vision_skipped": True}, "Empty frame - allowing flip"
        
        # Run vision analysis
        try:
            clearance = self.grok.check_clearance(
                frame,
                maneuver_type="flip",
                required_clearance_cm=self.FLIP_MIN_CLEARANCE
            )
        except Exception as e:
            self.log.warning(f"⚠️ Vision analysis failed - allowing flip: {e}")
            return True, {"vision_skipped": True, "error": str(e)}, "Vision analysis failed - allowing flip"
        
        # Build detailed data
        data = {
            "safety_score": clearance.overall_safety_score,
            "front_clearance": clearance.front_clearance_cm,
            "left_clearance": clearance.left_clearance_cm,
            "right_clearance": clearance.right_clearance_cm,
            "obstacles": [obs.model_dump() for obs in clearance.obstacles]
        }
        
        # SIMPLE CHECK: Is there >50cm clearance ahead?
        front_clear = clearance.front_clearance_cm
        
        # If clearance is unknown (-1) or > 50cm, ALLOW the flip
        if front_clear < 0 or front_clear > self.FLIP_MIN_CLEARANCE:
            self.log.info(f"✅ Clearance OK for flip (front: {front_clear}cm)")
            return True, data, f"Clearance OK (front: {front_clear}cm)"
        
        # Only block if there's a confirmed obstacle < 50cm ahead
        obstacle_names = ", ".join([obs.name for obs in clearance.obstacles[:2]]) or "obstacle"
        self.log.warning(f"⚠️ Obstacle too close for flip: {obstacle_names} at {front_clear}cm")
        return False, data, f"Obstacle too close: {obstacle_names} only {front_clear}cm ahead (need >{self.FLIP_MIN_CLEARANCE}cm)"
    
    def execute(self, direction: str, **kwargs) -> ToolResult:
        """
        Execute flip with mandatory safety checks.
        ALL checks must pass or flip is blocked with detailed explanation.
        """
        self.log.info(f"{'='*60}")
        self.log.info(f"🛡️ FLIP SAFETY CHECK: {direction.upper()} FLIP")
        self.log.info(f"{'='*60}")
        
        checks_passed = []
        checks_failed = []
        all_data = {"direction": direction}
        
        try:
            # === CHECK 1: BATTERY ===
            self.log.info("Check 1/3: Battery level...")
            battery_ok, battery_level, battery_msg = self._check_battery()
            all_data["battery"] = battery_level
            if battery_ok:
                self.log.success(f"  ✅ {battery_msg}")
                checks_passed.append(f"✅ Battery: {battery_level}%")
            else:
                self.log.error(f"  ❌ {battery_msg}")
                checks_failed.append(f"❌ Battery: {battery_msg}")
            
            # === CHECK 2: ALTITUDE ===
            self.log.info("Check 2/3: Altitude...")
            altitude_ok, height, altitude_msg = self._check_altitude()
            all_data["altitude"] = height
            if altitude_ok:
                self.log.success(f"  ✅ {altitude_msg}")
                checks_passed.append(f"✅ Altitude: {height}cm")
            else:
                self.log.error(f"  ❌ {altitude_msg}")
                checks_failed.append(f"❌ Altitude: {altitude_msg}")
            
            # === CHECK 3: VISION CLEARANCE ===
            self.log.info("Check 3/3: Vision clearance check...")
            vision_ok, vision_data, vision_msg = self._check_vision_clearance()
            all_data["vision"] = vision_data
            if vision_ok:
                self.log.success(f"  ✅ {vision_msg}")
                checks_passed.append(f"✅ Vision: {vision_msg}")
            else:
                self.log.error(f"  ❌ {vision_msg}")
                checks_failed.append(f"❌ Vision: {vision_msg}")
            
            # === DECISION ===
            self.log.info(f"{'='*60}")
            
            if checks_failed:
                self.log.error(f"❌ FLIP BLOCKED - {len(checks_failed)} check(s) failed")
                all_data["blocked_by"] = [c.split(":")[0].replace("❌ ", "") for c in checks_failed]
                
                # Build helpful message
                message = f"❌ FLIP BLOCKED!\n\n"
                message += "Checks passed:\n" + "\n".join(checks_passed) + "\n\n" if checks_passed else ""
                message += "Checks FAILED:\n" + "\n".join(checks_failed)
                
                # Add specific recommendations
                if not battery_ok:
                    message += "\n\n💡 Tip: Land and charge battery before attempting flips."
                if not altitude_ok and height >= 0:
                    gain_needed = FLIP_MIN_HEIGHT_CM - height
                    message += f"\n\n💡 Tip: Try 'move up {min(gain_needed + 20, 100)}' to gain altitude first."
                if not vision_ok:
                    message += f"\n\n💡 Tip: Move to a more open area with at least 50cm clearance ahead."
                
                return ToolResult(
                    success=False,
                    message=message,
                    data=all_data
                )
            
            # === ALL CHECKS PASSED - EXECUTE FLIP ===
            self.log.success(f"✅ ALL SAFETY CHECKS PASSED!")
            self.log.info(f"🚀 Executing {direction} flip...")
            
            self.drone.flip(direction)
            
            # Get battery after flip
            battery_after = self.drone.get_battery()
            all_data["battery_after"] = battery_after
            
            self.log.success(f"✅ {direction.upper()} FLIP COMPLETE!")
            self.log.info(f"{'='*60}")
            
            return ToolResult(
                success=True,
                message=f"✅ {direction.upper()} FLIP executed successfully!\n\n"
                        f"Pre-flip checks:\n" + "\n".join(checks_passed) +
                        f"\n\nBattery after flip: {battery_after}%",
                data=all_data
            )
            
        except SafetyViolationError as e:
            self.log.error(f"Flip blocked by controller: {e}")
            return ToolResult(
                success=False,
                message=f"❌ Flip blocked by drone controller: {str(e)}",
                data={"blocked_by": "controller", "error": str(e)}
            )
        except Exception as e:
            self.log.error(f"Flip failed with exception: {e}")
            return ToolResult(
                success=False,
                message=f"❌ Flip failed unexpectedly: {str(e)}",
                data={"blocked_by": "exception", "error": str(e)}
            )


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
