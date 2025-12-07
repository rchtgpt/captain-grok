"""
Main drone controller interface.
Provides high-level API for drone control with safety features.
"""

from typing import Optional, Union
from dataclasses import dataclass

from djitellopy import Tello

from core.logger import get_logger
from core.events import EventBus
from core.state import DroneState, StateMachine
from core.exceptions import DroneConnectionError, SafetyViolationError
from config.settings import Settings

from .mock import MockDrone
from .safety import ABORT_FLAG
from .video import VideoStream


@dataclass
class DroneStatus:
    """Drone status information."""
    connected: bool
    flying: bool
    battery: int
    height: int
    temperature: int
    state: DroneState


class DroneController:
    """
    High-level drone control interface with safety features.
    Works with both real Tello drone and MockDrone.
    """
    
    def __init__(
        self,
        event_bus: EventBus,
        settings: Settings,
        use_mock: bool = False,
        dry_run: bool = False
    ):
        """
        Initialize drone controller.
        
        Args:
            event_bus: Event bus for communication
            settings: Application settings
            use_mock: Use MockDrone instead of real drone
            dry_run: Use real drone camera but simulate flight commands
        """
        self.event_bus = event_bus
        self.settings = settings
        self.log = get_logger('drone')
        
        # Create drone instance
        if use_mock or not settings.DRONE_ENABLED:
            self.log.info("Using MockDrone (simulation mode)")
            self.drone = MockDrone()
            self.is_mock = True
        elif dry_run:
            self.log.info("Using DryRunDrone (real camera, simulated flight)")
            from .dry_run import DryRunDrone
            self.drone = DryRunDrone()
            self.is_mock = False
        else:
            self.log.info("Using real Tello drone")
            self.drone = Tello()
            self.is_mock = False
        
        # State machine
        self.state_machine = StateMachine(DroneState.IDLE)
        
        # Video stream
        self.video: Optional[VideoStream] = None
        
        # Position tracking for return home
        self.takeoff_position = {'x': 0, 'y': 0, 'z': 0}  # Starting position
        self.current_position = {'x': 0, 'y': 0, 'z': 0}  # Current estimated position
        self.position_tracking_enabled = True
        
        # Subscribe to abort events
        self.event_bus.subscribe('abort', self._on_abort)
    
    def connect(self) -> bool:
        """
        Connect to the drone.
        
        Returns:
            True if connection successful
            
        Raises:
            DroneConnectionError: If connection fails
        """
        try:
            self.log.info("Connecting to drone...")
            self.drone.connect()
            
            # Get initial status
            battery = self.drone.get_battery()
            self.log.success(f"Connected! Battery: {battery}%")
            
            # Check battery level
            if battery < self.settings.LOW_BATTERY_THRESHOLD:
                self.log.warning(f"⚠️ Low battery: {battery}%")
            
            # Update state
            self.state_machine.transition_to(DroneState.CONNECTED)
            
            # Initialize video if enabled
            # Note: Window display disabled by default - video accessed via /video/stream endpoint
            # For window display, call video.run_display_loop() on the main thread
            if self.settings.VIDEO_ENABLED:
                self.video = VideoStream(
                    self.drone,
                    self.event_bus,
                    show_window=False  # Disabled - OpenCV windows require main thread on macOS
                )
            
            return True
        
        except Exception as e:
            self.log.error(f"Failed to connect: {e}")
            raise DroneConnectionError(f"Could not connect to drone: {e}")
    
    def disconnect(self) -> None:
        """Disconnect from drone and cleanup."""
        self.log.info("Disconnecting from drone...")
        
        # Stop video
        if self.video and self.video.is_running:
            self.video.stop()
        
        # Land if flying
        if self.state_machine.is_flying():
            try:
                self.land()
            except:
                pass
        
        # Disconnect
        try:
            self.drone.end()
        except:
            pass
        
        self.state_machine.transition_to(DroneState.IDLE)
        self.log.info("Disconnected")
    
    def takeoff(self) -> None:
        """
        Take off and hover.
        
        Raises:
            SafetyViolationError: If conditions unsafe for takeoff
        """
        if self.state_machine.is_flying():
            self.log.warning("Already flying!")
            return
        
        # Safety checks
        battery = self.drone.get_battery()
        if battery < self.settings.LOW_BATTERY_THRESHOLD:
            raise SafetyViolationError(f"Battery too low for takeoff: {battery}%")
        
        self.log.info("Taking off...")
        self.drone.takeoff()
        
        # Reset position tracking at takeoff
        self.takeoff_position = {'x': 0, 'y': 0, 'z': 0}
        self.current_position = {'x': 0, 'y': 0, 'z': 0}
        
        self.state_machine.transition_to(DroneState.HOVERING)
        self.event_bus.publish('drone.takeoff', {})
        self.log.success("Airborne!")
    
    def land(self) -> None:
        """Land the drone."""
        if not self.state_machine.is_flying():
            self.log.warning("Not flying!")
            return
        
        self.log.info("Landing...")
        self.state_machine.transition_to(DroneState.LANDING)
        
        self.drone.land()
        
        self.state_machine.transition_to(DroneState.CONNECTED)
        self.event_bus.publish('drone.land', {})
        self.log.success("Landed!")
    
    def move(self, direction: str, distance: int) -> None:
        """
        Move in a direction.
        
        Args:
            direction: One of 'forward', 'back', 'left', 'right', 'up', 'down'
            distance: Distance in centimeters
            
        Raises:
            SafetyViolationError: If movement violates safety limits
        """
        if not self.state_machine.can_execute():
            current_state = self.state_machine.state
            if current_state == DroneState.CONNECTED:
                raise SafetyViolationError("Cannot move: Drone is on the ground. Call 'takeoff' first to launch the drone.")
            else:
                raise SafetyViolationError(f"Cannot move in current state: {current_state.name}")
        
        # Clamp distance to safe limits
        distance = max(
            self.settings.MIN_MOVE_DISTANCE,
            min(distance, self.settings.MAX_MOVE_DISTANCE)
        )
        
        # Check height limit for upward movement
        if direction == 'up':
            current_height = self.drone.get_height() if hasattr(self.drone, 'get_height') else 0
            if current_height + distance > self.settings.MAX_HEIGHT_CM:
                raise SafetyViolationError(f"Would exceed max height of {self.settings.MAX_HEIGHT_CM}cm")
        
        # Execute movement
        self.state_machine.transition_to(DroneState.EXECUTING)
        
        direction_map = {
            'forward': self.drone.move_forward,
            'back': self.drone.move_back,
            'left': self.drone.move_left,
            'right': self.drone.move_right,
            'up': self.drone.move_up,
            'down': self.drone.move_down
        }
        
        if direction not in direction_map:
            raise ValueError(f"Invalid direction: {direction}")
        
        self.log.info(f"Moving {direction} {distance}cm")
        direction_map[direction](distance)
        
        # Update position tracking
        if self.position_tracking_enabled:
            if direction == 'forward':
                self.current_position['x'] += distance
            elif direction == 'back':
                self.current_position['x'] -= distance
            elif direction == 'left':
                self.current_position['y'] -= distance
            elif direction == 'right':
                self.current_position['y'] += distance
            elif direction == 'up':
                self.current_position['z'] += distance
            elif direction == 'down':
                self.current_position['z'] -= distance
        
        self.state_machine.transition_to(DroneState.HOVERING)
    
    def rotate(self, degrees: int) -> None:
        """
        Rotate the drone.
        
        Args:
            degrees: Degrees to rotate (positive = clockwise)
        """
        if not self.state_machine.can_execute():
            raise SafetyViolationError("Cannot rotate in current state")
        
        self.state_machine.transition_to(DroneState.EXECUTING)
        
        if degrees > 0:
            self.log.info(f"Rotating clockwise {degrees}°")
            self.drone.rotate_clockwise(abs(degrees))
        else:
            self.log.info(f"Rotating counter-clockwise {abs(degrees)}°")
            self.drone.rotate_counter_clockwise(abs(degrees))
        
        self.state_machine.transition_to(DroneState.HOVERING)
    
    def flip(self, direction: str) -> None:
        """
        Perform a flip.
        
        Args:
            direction: One of 'forward', 'back', 'left', 'right'
        """
        if not self.state_machine.can_execute():
            raise SafetyViolationError("Cannot flip in current state")
        
        flip_map = {
            'forward': self.drone.flip_forward,
            'back': self.drone.flip_back,
            'left': self.drone.flip_left,
            'right': self.drone.flip_right
        }
        
        if direction not in flip_map:
            raise ValueError(f"Invalid flip direction: {direction}")
        
        self.log.info(f"Flipping {direction}!")
        self.state_machine.transition_to(DroneState.EXECUTING)
        flip_map[direction]()
        self.state_machine.transition_to(DroneState.HOVERING)
    
    def hover(self) -> None:
        """Stop all movement and hover in place."""
        self.log.info("Hovering...")
        self.drone.send_rc_control(0, 0, 0, 0)
        if self.state_machine.can_execute():
            self.state_machine.transition_to(DroneState.HOVERING)
    
    def emergency_stop(self) -> None:
        """
        Emergency stop - immediately halt all movement.
        Sets ABORT_FLAG and hovers.
        """
        self.log.warning("🚨 EMERGENCY STOP ACTIVATED!")
        
        ABORT_FLAG.set()
        self.state_machine.transition_to(DroneState.EMERGENCY, force=True)
        
        # Stop all movement
        self.drone.send_rc_control(0, 0, 0, 0)
        
        self.event_bus.publish('emergency_stop', {})
    
    def get_status(self) -> DroneStatus:
        """
        Get current drone status.
        
        Returns:
            DroneStatus object
        """
        try:
            battery = self.drone.get_battery()
            temperature = self.drone.get_temperature() if hasattr(self.drone, 'get_temperature') else 0
            height = self.drone.get_height() if hasattr(self.drone, 'get_height') else 0
            
            return DroneStatus(
                connected=hasattr(self.drone, 'connected') and self.drone.connected,
                flying=self.state_machine.is_flying(),
                battery=battery,
                height=height,
                temperature=temperature,
                state=self.state_machine.state
            )
        except Exception as e:
            self.log.error(f"Error getting status: {e}")
            return DroneStatus(
                connected=False,
                flying=False,
                battery=0,
                height=0,
                temperature=0,
                state=self.state_machine.state
            )
    
    def get_battery(self) -> int:
        """Get battery percentage."""
        return self.drone.get_battery()
    
    def emergency_land(self) -> None:
        """
        EMERGENCY LAND - Land immediately wherever the drone is.
        Use this when you need to land RIGHT NOW!
        Bypasses all normal checks and forces an immediate landing.
        """
        self.log.warning("🚨🚨🚨 EMERGENCY LAND INITIATED! 🚨🚨🚨")
        
        # Set abort flag to stop any ongoing operations
        ABORT_FLAG.set()
        
        # Force state to landing (bypasses state machine checks)
        self.state_machine.transition_to(DroneState.LANDING, force=True)
        
        try:
            # LAND NOW!
            self.drone.land()
            self.log.success("✅ Emergency landing completed")
            
            # Update state
            self.state_machine.transition_to(DroneState.CONNECTED)
            self.event_bus.publish('emergency_land', {})
            
        except Exception as e:
            self.log.error(f"Emergency land failed: {e}")
            # Try emergency motor stop as last resort
            try:
                self.drone.emergency()
            except:
                pass
    
    def return_home_and_land(self) -> None:
        """
        RETURN HOME & LAND - Fly back to takeoff position, then land safely.
        Uses position tracking to navigate back to the starting point.
        """
        self.log.warning("🏠 RETURN HOME ACTIVATED - Flying back to takeoff position")
        
        if not self.state_machine.is_flying():
            self.log.warning("Not flying! Cannot return home.")
            return
        
        try:
            # Calculate distance from home
            dx = self.current_position['x']
            dy = self.current_position['y']
            dz = self.current_position['z']
            
            self.log.info(f"Current position: x={dx}cm, y={dy}cm, z={dz}cm")
            self.log.info("Flying back to takeoff position...")
            
            # Return to home height first (safe)
            if dz > 0:
                self.log.info(f"Descending {dz}cm to takeoff height")
                self.move('down', min(abs(dz), 100))
            elif dz < 0:
                self.log.info(f"Ascending {abs(dz)}cm to takeoff height")
                self.move('up', min(abs(dz), 100))
            
            # Return to home position (x, y)
            # Move back in reverse of how we got here
            if dx > 0:
                self.log.info(f"Moving back {dx}cm")
                while dx > 0:
                    dist = min(dx, 100)
                    self.move('back', dist)
                    dx -= dist
            elif dx < 0:
                self.log.info(f"Moving forward {abs(dx)}cm")
                while dx < 0:
                    dist = min(abs(dx), 100)
                    self.move('forward', dist)
                    dx += dist
            
            if dy > 0:
                self.log.info(f"Moving left {dy}cm")
                while dy > 0:
                    dist = min(dy, 100)
                    self.move('left', dist)
                    dy -= dist
            elif dy < 0:
                self.log.info(f"Moving right {abs(dy)}cm")
                while dy < 0:
                    dist = min(abs(dy), 100)
                    self.move('right', dist)
                    dy += dist
            
            self.log.success("✅ Returned to takeoff position!")
            self.log.info("Landing...")
            
            # Land safely
            self.land()
            
            self.log.success("🏠 Return home complete!")
            self.event_bus.publish('return_home_complete', {})
            
        except Exception as e:
            self.log.error(f"Return home failed: {e}")
            self.log.warning("Initiating emergency land instead!")
            self.emergency_land()
    
    def get_position(self) -> dict:
        """
        Get estimated current position relative to takeoff.
        
        Returns:
            dict with 'x', 'y', 'z' in centimeters
        """
        return self.current_position.copy()
    
    def get_distance_from_home(self) -> float:
        """
        Calculate straight-line distance from takeoff position.
        
        Returns:
            Distance in centimeters
        """
        import math
        dx = self.current_position['x']
        dy = self.current_position['y']
        dz = self.current_position['z']
        return math.sqrt(dx**2 + dy**2 + dz**2)
    
    def _on_abort(self, data) -> None:
        """Handle abort event."""
        self.log.warning("Abort event received!")
        self.emergency_stop()
    
    def __repr__(self) -> str:
        """String representation."""
        status = self.get_status()
        return (
            f"DroneController(state={status.state.name}, "
            f"battery={status.battery}%, flying={status.flying})"
        )
