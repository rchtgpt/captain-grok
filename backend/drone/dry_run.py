"""
Dry-run drone wrapper for testing with real camera but simulated flight.

This wrapper connects to a real Tello drone and uses its camera, but intercepts
all motor/flight commands and logs them instead of executing them. This allows
you to:
- Use the real drone camera
- Manually move the drone and see the real feed
- Test commands without activating motors
- See exactly what the drone would do

Perfect for safe testing and development!
"""

import time
from djitellopy import Tello
from core.logger import get_logger


class DryRunDrone:
    """
    Wrapper for Tello drone that uses real camera but simulates all flight commands.
    
    PASS-THROUGH (Real execution):
    - Camera operations (streamon, get_frame_read, etc.)
    - Status queries (get_battery, get_height, etc.)
    - Connection methods (connect, end)
    
    INTERCEPTED (Logged, not executed):
    - All motor/flight commands (takeoff, land, move, rotate, flip, etc.)
    """
    
    def __init__(self):
        """Initialize dry-run drone with real Tello connection."""
        self.drone = Tello()  # Real Tello instance
        self.log = get_logger('dry_run')
        
        # Simulation state (for display purposes)
        self.is_flying_simulated = False
        self.simulated_height = 0
        
        self.log.info("🔧 DryRunDrone initialized - Real camera, simulated flight")
    
    # ========================================================================
    # PASS-THROUGH METHODS - Execute normally (camera, status, connection)
    # ========================================================================
    
    def connect(self):
        """Connect to real drone (PASS-THROUGH)."""
        self.log.info("📡 Connecting to real Tello drone...")
        return self.drone.connect()
    
    def end(self):
        """Disconnect from drone (PASS-THROUGH)."""
        self.log.info("📡 Disconnecting from real Tello drone...")
        try:
            return self.drone.end()
        except:
            pass
    
    def streamon(self):
        """Start video stream (PASS-THROUGH - Real camera)."""
        self.log.info("📹 Starting real camera stream...")
        return self.drone.streamon()
    
    def streamoff(self):
        """Stop video stream (PASS-THROUGH - Real camera)."""
        self.log.info("📹 Stopping real camera stream...")
        try:
            return self.drone.streamoff()
        except:
            pass
    
    def get_frame_read(self):
        """Get frame reader (PASS-THROUGH - Real camera)."""
        return self.drone.get_frame_read()
    
    def get_battery(self) -> int:
        """Get battery level (PASS-THROUGH - Real status)."""
        return self.drone.get_battery()
    
    def get_height(self) -> int:
        """Get current height (PASS-THROUGH - Real sensor)."""
        return self.drone.get_height()
    
    def get_temperature(self) -> int:
        """Get temperature (PASS-THROUGH - Real sensor)."""
        try:
            return int(self.drone.get_temperature())
        except Exception as e:
            self.log.debug(f"[DRY-RUN] Could not get real temperature ({e}), using default value")
            return 50  # Default temperature if sensor fails
    
    def get_barometer(self) -> int:
        """Get barometer reading (PASS-THROUGH - Real sensor)."""
        return int(self.drone.get_barometer())
    
    def get_distance_tof(self) -> int:
        """Get TOF distance (PASS-THROUGH - Real sensor)."""
        return self.drone.get_distance_tof()
    
    def get_speed_x(self) -> int:
        """Get speed X (PASS-THROUGH - Real sensor)."""
        return self.drone.get_speed_x()
    
    def get_speed_y(self) -> int:
        """Get speed Y (PASS-THROUGH - Real sensor)."""
        return self.drone.get_speed_y()
    
    def get_speed_z(self) -> int:
        """Get speed Z (PASS-THROUGH - Real sensor)."""
        return self.drone.get_speed_z()
    
    def get_acceleration_x(self) -> float:
        """Get acceleration X (PASS-THROUGH - Real sensor)."""
        return self.drone.get_acceleration_x()
    
    def get_acceleration_y(self) -> float:
        """Get acceleration Y (PASS-THROUGH - Real sensor)."""
        return self.drone.get_acceleration_y()
    
    def get_acceleration_z(self) -> float:
        """Get acceleration Z (PASS-THROUGH - Real sensor)."""
        return self.drone.get_acceleration_z()
    
    def query_battery(self) -> int:
        """Query battery (PASS-THROUGH - Real status)."""
        return self.drone.query_battery()
    
    def query_height(self) -> int:
        """Query height (PASS-THROUGH - Real sensor)."""
        return self.drone.query_height()
    
    def query_temperature(self) -> int:
        """Query temperature (PASS-THROUGH - Real sensor)."""
        return self.drone.query_temperature()
    
    # ========================================================================
    # INTERCEPTED METHODS - Log instead of executing (motor commands)
    # ========================================================================
    
    def takeoff(self):
        """Simulate takeoff (INTERCEPTED - Motors stay off)."""
        self.log.info("🚁 [DRY-RUN] Would execute: TAKEOFF")
        self.log.info("   → Drone would rise to hover height (~50cm)")
        self.log.info("   → Motors: OFF (simulated)")
        self.is_flying_simulated = True
        self.simulated_height = 50
        time.sleep(0.1)  # Small delay to simulate command processing
    
    def land(self):
        """Simulate landing (INTERCEPTED - Motors stay off)."""
        self.log.info("🛬 [DRY-RUN] Would execute: LAND")
        self.log.info("   → Drone would descend and land")
        self.log.info("   → Motors: OFF (simulated)")
        self.is_flying_simulated = False
        self.simulated_height = 0
        time.sleep(0.1)
    
    def move_up(self, distance: int):
        """Simulate move up (INTERCEPTED - Motors stay off)."""
        self.log.info(f"⬆️  [DRY-RUN] Would execute: MOVE UP {distance}cm")
        self.log.info(f"   → Drone would ascend {distance}cm")
        self.log.info("   → Motors: OFF (simulated)")
        self.simulated_height += distance
        time.sleep(0.1)
    
    def move_down(self, distance: int):
        """Simulate move down (INTERCEPTED - Motors stay off)."""
        self.log.info(f"⬇️  [DRY-RUN] Would execute: MOVE DOWN {distance}cm")
        self.log.info(f"   → Drone would descend {distance}cm")
        self.log.info("   → Motors: OFF (simulated)")
        self.simulated_height = max(0, self.simulated_height - distance)
        time.sleep(0.1)
    
    def move_forward(self, distance: int):
        """Simulate move forward (INTERCEPTED - Motors stay off)."""
        self.log.info(f"⬆️  [DRY-RUN] Would execute: MOVE FORWARD {distance}cm")
        self.log.info(f"   → Drone would move forward {distance}cm")
        self.log.info("   → Motors: OFF (simulated)")
        time.sleep(0.1)
    
    def move_back(self, distance: int):
        """Simulate move back (INTERCEPTED - Motors stay off)."""
        self.log.info(f"⬇️  [DRY-RUN] Would execute: MOVE BACK {distance}cm")
        self.log.info(f"   → Drone would move backward {distance}cm")
        self.log.info("   → Motors: OFF (simulated)")
        time.sleep(0.1)
    
    def move_left(self, distance: int):
        """Simulate move left (INTERCEPTED - Motors stay off)."""
        self.log.info(f"⬅️  [DRY-RUN] Would execute: MOVE LEFT {distance}cm")
        self.log.info(f"   → Drone would strafe left {distance}cm")
        self.log.info("   → Motors: OFF (simulated)")
        time.sleep(0.1)
    
    def move_right(self, distance: int):
        """Simulate move right (INTERCEPTED - Motors stay off)."""
        self.log.info(f"➡️  [DRY-RUN] Would execute: MOVE RIGHT {distance}cm")
        self.log.info(f"   → Drone would strafe right {distance}cm")
        self.log.info("   → Motors: OFF (simulated)")
        time.sleep(0.1)
    
    def rotate_clockwise(self, degrees: int):
        """Simulate clockwise rotation (INTERCEPTED - Motors stay off)."""
        self.log.info(f"🔄 [DRY-RUN] Would execute: ROTATE CLOCKWISE {degrees}°")
        self.log.info(f"   → Drone would rotate {degrees}° clockwise")
        self.log.info("   → Motors: OFF (simulated)")
        time.sleep(0.1)
    
    def rotate_counter_clockwise(self, degrees: int):
        """Simulate counter-clockwise rotation (INTERCEPTED - Motors stay off)."""
        self.log.info(f"🔄 [DRY-RUN] Would execute: ROTATE COUNTER-CLOCKWISE {degrees}°")
        self.log.info(f"   → Drone would rotate {degrees}° counter-clockwise")
        self.log.info("   → Motors: OFF (simulated)")
        time.sleep(0.1)
    
    def flip_forward(self):
        """Simulate forward flip (INTERCEPTED - Motors stay off)."""
        self.log.info("🤸 [DRY-RUN] Would execute: FLIP FORWARD")
        self.log.info("   → Drone would perform forward flip")
        self.log.info("   → Motors: OFF (simulated)")
        time.sleep(0.1)
    
    def flip_back(self):
        """Simulate backward flip (INTERCEPTED - Motors stay off)."""
        self.log.info("🤸 [DRY-RUN] Would execute: FLIP BACK")
        self.log.info("   → Drone would perform backward flip")
        self.log.info("   → Motors: OFF (simulated)")
        time.sleep(0.1)
    
    def flip_left(self):
        """Simulate left flip (INTERCEPTED - Motors stay off)."""
        self.log.info("🤸 [DRY-RUN] Would execute: FLIP LEFT")
        self.log.info("   → Drone would perform left flip")
        self.log.info("   → Motors: OFF (simulated)")
        time.sleep(0.1)
    
    def flip_right(self):
        """Simulate right flip (INTERCEPTED - Motors stay off)."""
        self.log.info("🤸 [DRY-RUN] Would execute: FLIP RIGHT")
        self.log.info("   → Drone would perform right flip")
        self.log.info("   → Motors: OFF (simulated)")
        time.sleep(0.1)
    
    def send_rc_control(self, left_right: int, forward_backward: int, 
                       up_down: int, yaw: int):
        """Simulate RC control (INTERCEPTED - Motors stay off)."""
        self.log.info("🎮 [DRY-RUN] Would execute: RC CONTROL")
        self.log.info(f"   → Left/Right: {left_right}")
        self.log.info(f"   → Forward/Back: {forward_backward}")
        self.log.info(f"   → Up/Down: {up_down}")
        self.log.info(f"   → Yaw: {yaw}")
        self.log.info("   → Motors: OFF (simulated)")
        # Note: No sleep here as RC control is continuous
    
    def emergency(self):
        """Simulate emergency stop (INTERCEPTED - Motors stay off)."""
        self.log.warning("🚨 [DRY-RUN] Would execute: EMERGENCY STOP")
        self.log.warning("   → Drone would cut motors immediately")
        self.log.warning("   → Motors: OFF (already off in dry-run)")
        self.is_flying_simulated = False
        time.sleep(0.1)
    
    def go_xyz_speed(self, x: int, y: int, z: int, speed: int):
        """Simulate go to XYZ (INTERCEPTED - Motors stay off)."""
        self.log.info(f"📍 [DRY-RUN] Would execute: GO TO XYZ")
        self.log.info(f"   → Target: X={x}cm, Y={y}cm, Z={z}cm")
        self.log.info(f"   → Speed: {speed}cm/s")
        self.log.info("   → Motors: OFF (simulated)")
        time.sleep(0.1)
    
    def curve_xyz_speed(self, x1: int, y1: int, z1: int, 
                       x2: int, y2: int, z2: int, speed: int):
        """Simulate curve flight (INTERCEPTED - Motors stay off)."""
        self.log.info("🌀 [DRY-RUN] Would execute: CURVE FLIGHT")
        self.log.info(f"   → Waypoint 1: X={x1}cm, Y={y1}cm, Z={z1}cm")
        self.log.info(f"   → Waypoint 2: X={x2}cm, Y={y2}cm, Z={z2}cm")
        self.log.info(f"   → Speed: {speed}cm/s")
        self.log.info("   → Motors: OFF (simulated)")
        time.sleep(0.1)
    
    def set_speed(self, speed: int):
        """Set speed (PASS-THROUGH but logged)."""
        self.log.info(f"⚙️  [DRY-RUN] Would set speed: {speed}cm/s")
        self.log.info("   → Speed setting would be applied")
        # Don't actually set speed in dry-run to avoid any motor config changes
    
    def enable_mission_pads(self):
        """Enable mission pads (PASS-THROUGH but logged)."""
        self.log.info("🎯 [DRY-RUN] Would enable mission pads")
        self.log.info("   → Mission pad detection would be enabled")
    
    def disable_mission_pads(self):
        """Disable mission pads (PASS-THROUGH but logged)."""
        self.log.info("🎯 [DRY-RUN] Would disable mission pads")
        self.log.info("   → Mission pad detection would be disabled")
