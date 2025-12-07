"""
Mock drone for testing without actual hardware.
Simulates Tello drone behavior.
"""

import time
import numpy as np
from typing import Optional
from core.logger import get_logger


class MockFrameRead:
    """Mock frame reader for simulated video."""
    
    def __init__(self):
        """Initialize with a test pattern."""
        # Create a simple test pattern image
        self.frame = np.zeros((720, 960, 3), dtype=np.uint8)
        self.frame[:, :] = [100, 100, 150]  # Gray-blue background
        
        # Add some text
        import cv2
        cv2.putText(
            self.frame,
            "MOCK DRONE CAMERA",
            (300, 360),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (255, 255, 255),
            2
        )


class MockDrone:
    """
    Mock implementation of Tello drone for testing.
    Simulates all drone operations without actual hardware.
    """
    
    def __init__(self):
        """Initialize mock drone."""
        self.log = get_logger('mock_drone')
        
        # State
        self.connected = False
        self.is_flying = False
        self.stream_on = False
        
        # Position tracking
        self.x = 0
        self.y = 0
        self.z = 0  # height in cm
        self.rotation = 0  # degrees
        
        # Status
        self.battery = 100
        self.temperature = 50
        
        # Video
        self._frame_read = MockFrameRead()
    
    def connect(self):
        """Simulate connection to drone."""
        self.log.info("📡 [MOCK] Connecting to drone...")
        time.sleep(0.5)
        self.connected = True
        self.log.success("✅ [MOCK] Connected!")
    
    def get_battery(self) -> int:
        """Get battery level."""
        # Simulate battery drain
        if self.is_flying:
            self.battery = max(0, self.battery - 0.1)
        return int(self.battery)
    
    def get_temperature(self) -> int:
        """Get temperature."""
        return self.temperature
    
    def get_height(self) -> int:
        """Get current height in cm."""
        return int(self.z)
    
    def takeoff(self):
        """Simulate takeoff."""
        self.log.info("🛫 [MOCK] Taking off...")
        time.sleep(1)
        self.is_flying = True
        self.z = 50  # Hover at 50cm
        self.log.success("✅ [MOCK] Airborne!")
    
    def land(self):
        """Simulate landing."""
        self.log.info("🛬 [MOCK] Landing...")
        time.sleep(1)
        self.is_flying = False
        self.z = 0
        self.log.success("✅ [MOCK] Landed!")
    
    def move_forward(self, distance: int):
        """Move forward."""
        self.log.info(f"➡️ [MOCK] Moving forward {distance}cm")
        time.sleep(distance / 50)  # Simulate movement time
        self.x += distance
    
    def move_back(self, distance: int):
        """Move backward."""
        self.log.info(f"⬅️ [MOCK] Moving back {distance}cm")
        time.sleep(distance / 50)
        self.x -= distance
    
    def move_left(self, distance: int):
        """Move left."""
        self.log.info(f"⬅️ [MOCK] Moving left {distance}cm")
        time.sleep(distance / 50)
        self.y -= distance
    
    def move_right(self, distance: int):
        """Move right."""
        self.log.info(f"➡️ [MOCK] Moving right {distance}cm")
        time.sleep(distance / 50)
        self.y += distance
    
    def move_up(self, distance: int):
        """Move up."""
        self.log.info(f"⬆️ [MOCK] Moving up {distance}cm")
        time.sleep(distance / 50)
        self.z += distance
    
    def move_down(self, distance: int):
        """Move down."""
        self.log.info(f"⬇️ [MOCK] Moving down {distance}cm")
        time.sleep(distance / 50)
        self.z = max(0, self.z - distance)
    
    def rotate_clockwise(self, degrees: int):
        """Rotate clockwise."""
        self.log.info(f"🔄 [MOCK] Rotating clockwise {degrees}°")
        time.sleep(abs(degrees) / 90)
        self.rotation = (self.rotation + degrees) % 360
    
    def rotate_counter_clockwise(self, degrees: int):
        """Rotate counter-clockwise."""
        self.log.info(f"🔄 [MOCK] Rotating counter-clockwise {degrees}°")
        time.sleep(abs(degrees) / 90)
        self.rotation = (self.rotation - degrees) % 360
    
    def flip_forward(self):
        """Flip forward."""
        self.log.info("🤸 [MOCK] Flipping forward!")
        time.sleep(1)
    
    def flip_back(self):
        """Flip backward."""
        self.log.info("🤸 [MOCK] Flipping backward!")
        time.sleep(1)
    
    def flip_left(self):
        """Flip left."""
        self.log.info("🤸 [MOCK] Flipping left!")
        time.sleep(1)
    
    def flip_right(self):
        """Flip right."""
        self.log.info("🤸 [MOCK] Flipping right!")
        time.sleep(1)
    
    def send_rc_control(self, left_right: int, forward_backward: int, up_down: int, yaw: int):
        """
        Send RC control command.
        
        Args:
            left_right: -100 to 100
            forward_backward: -100 to 100
            up_down: -100 to 100
            yaw: -100 to 100
        """
        if left_right == 0 and forward_backward == 0 and up_down == 0 and yaw == 0:
            self.log.info("⏸️ [MOCK] Hovering in place")
        else:
            self.log.debug(f"🎮 [MOCK] RC: lr={left_right}, fb={forward_backward}, ud={up_down}, yaw={yaw}")
    
    def streamon(self):
        """Start video stream."""
        self.log.info("📹 [MOCK] Starting video stream...")
        time.sleep(0.5)
        self.stream_on = True
        self.log.success("✅ [MOCK] Video stream started!")
    
    def streamoff(self):
        """Stop video stream."""
        self.log.info("📹 [MOCK] Stopping video stream...")
        self.stream_on = False
    
    def get_frame_read(self) -> MockFrameRead:
        """Get frame reader."""
        return self._frame_read
    
    def end(self):
        """Disconnect from drone."""
        self.log.info("👋 [MOCK] Disconnecting...")
        self.connected = False
        self.stream_on = False
        self.is_flying = False
    
    def emergency(self):
        """Emergency stop."""
        self.log.warning("🚨 [MOCK] EMERGENCY STOP!")
        self.is_flying = False
    
    def __repr__(self) -> str:
        """String representation."""
        return (
            f"MockDrone(connected={self.connected}, flying={self.is_flying}, "
            f"position=({self.x}, {self.y}, {self.z}), rotation={self.rotation}°, "
            f"battery={self.battery}%)"
        )
