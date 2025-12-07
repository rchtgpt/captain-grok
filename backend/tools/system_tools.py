"""
System control tools for Grok-Pilot.
Provides status, abort, and utility functions.
"""

from .base import BaseTool, ToolResult
from core.logger import get_logger
from drone.safety import smart_sleep, ABORT_FLAG, clear_abort


class GetStatusTool(BaseTool):
    """Get current drone and system status."""
    
    name = "get_status"
    description = "Get current drone status including battery, height, and flying state"
    parameters = {
        "type": "object",
        "properties": {},
        "required": []
    }
    
    def __init__(self, drone_controller):
        super().__init__()
        self.drone = drone_controller
        self.log = get_logger('tools.status')
    
    def execute(self, **kwargs) -> ToolResult:
        try:
            status = self.drone.get_status()
            
            message = (
                f"Battery: {status.battery}%, "
                f"Height: {status.height}cm, "
                f"State: {status.state.name}, "
                f"Flying: {'Yes' if status.flying else 'No'}"
            )
            
            return ToolResult(
                success=True,
                message=message,
                data={
                    "battery": status.battery,
                    "height": status.height,
                    "temperature": status.temperature,
                    "flying": status.flying,
                    "state": status.state.name,
                    "connected": status.connected
                }
            )
        except Exception as e:
            return ToolResult(success=False, message=f"Failed to get status: {str(e)}")


class EmergencyStopTool(BaseTool):
    """Trigger emergency stop."""
    
    name = "emergency_stop"
    description = "Immediately stop all drone movement and hover in place (USE FOR EMERGENCIES ONLY)"
    parameters = {
        "type": "object",
        "properties": {},
        "required": []
    }
    
    def __init__(self, drone_controller, event_bus):
        super().__init__()
        self.drone = drone_controller
        self.event_bus = event_bus
        self.log = get_logger('tools.emergency')
    
    def execute(self, **kwargs) -> ToolResult:
        try:
            self.log.warning("EMERGENCY STOP TRIGGERED")
            self.drone.emergency_stop()
            self.event_bus.publish('emergency_stop', {'source': 'tool'})
            
            return ToolResult(
                success=True,
                message="EMERGENCY STOP ACTIVATED - Drone hovering",
                data={"abort_flag_set": True}
            )
        except Exception as e:
            return ToolResult(success=False, message=f"Emergency stop failed: {str(e)}")


class WaitTool(BaseTool):
    """Wait for a specified duration."""
    
    name = "wait"
    description = "Wait for a specified number of seconds (interruptible)"
    parameters = {
        "type": "object",
        "properties": {
            "seconds": {
                "type": "number",
                "description": "Number of seconds to wait",
                "minimum": 0.1,
                "maximum": 10
            }
        },
        "required": ["seconds"]
    }
    
    def __init__(self):
        super().__init__()
        self.log = get_logger('tools.wait')
    
    def execute(self, seconds: float, **kwargs) -> ToolResult:
        try:
            # Clamp to safe range
            seconds = max(0.1, min(10.0, seconds))
            
            self.log.debug(f"Waiting {seconds} seconds")
            smart_sleep(seconds)
            
            return ToolResult(
                success=True,
                message=f"Waited {seconds} seconds",
                data={"duration": seconds}
            )
        except Exception as e:
            return ToolResult(success=False, message=f"Wait interrupted: {str(e)}")


class SayTool(BaseTool):
    """Return a message to speak to the user."""
    
    name = "say"
    description = "Say a message to the user (returns text for TTS)"
    parameters = {
        "type": "object",
        "properties": {
            "message": {
                "type": "string",
                "description": "Message to say to the user"
            }
        },
        "required": ["message"]
    }
    
    def __init__(self, event_bus):
        super().__init__()
        self.event_bus = event_bus
        self.log = get_logger('tools.say')
    
    def execute(self, message: str, **kwargs) -> ToolResult:
        try:
            self.log.info(f"Saying: {message}")
            self.event_bus.publish('say', {'message': message})
            
            return ToolResult(
                success=True,
                message=message,
                data={"text": message}
            )
        except Exception as e:
            return ToolResult(success=False, message=f"Say failed: {str(e)}")


class ClearAbortTool(BaseTool):
    """Clear the abort flag to resume operations."""
    
    name = "clear_abort"
    description = "Clear the abort flag to allow new commands (use after emergency stop)"
    parameters = {
        "type": "object",
        "properties": {},
        "required": []
    }
    
    def __init__(self):
        super().__init__()
        self.log = get_logger('tools.clear_abort')
    
    def execute(self, **kwargs) -> ToolResult:
        try:
            clear_abort()
            return ToolResult(
                success=True,
                message="Abort flag cleared - ready for new commands",
                data={"abort_cleared": True}
            )
        except Exception as e:
            return ToolResult(success=False, message=f"Failed to clear abort: {str(e)}")


class EmergencyLandTool(BaseTool):
    """Emergency land - lands immediately wherever the drone is."""
    
    name = "emergency_land"
    description = "🚨 EMERGENCY LAND - Land immediately wherever the drone is RIGHT NOW! Use when you need instant landing."
    parameters = {
        "type": "object",
        "properties": {},
        "required": []
    }
    
    def __init__(self, drone_controller, event_bus):
        super().__init__()
        self.drone = drone_controller
        self.event_bus = event_bus
        self.log = get_logger('tools.emergency_land')
    
    def execute(self, **kwargs) -> ToolResult:
        try:
            self.log.warning("🚨🚨🚨 EMERGENCY LAND TRIGGERED FROM TOOL 🚨🚨🚨")
            self.drone.emergency_land()
            
            return ToolResult(
                success=True,
                message="🚨 EMERGENCY LAND COMPLETE - Drone landed immediately!",
                data={"emergency_land": True, "position": self.drone.get_position()}
            )
        except Exception as e:
            self.log.error(f"Emergency land failed: {e}")
            return ToolResult(success=False, message=f"Emergency land failed: {str(e)}")


class ReturnHomeTool(BaseTool):
    """Return home and land - flies back to takeoff position."""
    
    name = "return_home"
    description = "🏠 RETURN HOME - Fly back to takeoff position and land safely. Uses position tracking."
    parameters = {
        "type": "object",
        "properties": {},
        "required": []
    }
    
    def __init__(self, drone_controller, event_bus):
        super().__init__()
        self.drone = drone_controller
        self.event_bus = event_bus
        self.log = get_logger('tools.return_home')
    
    def execute(self, **kwargs) -> ToolResult:
        try:
            self.log.info("🏠 RETURN HOME TRIGGERED FROM TOOL")
            
            # Get current distance from home
            distance = self.drone.get_distance_from_home()
            position = self.drone.get_position()
            
            self.log.info(f"Current position: {position}, distance from home: {distance:.1f}cm")
            
            # Execute return home
            self.drone.return_home_and_land()
            
            return ToolResult(
                success=True,
                message=f"🏠 Returned home from {distance:.0f}cm away and landed safely!",
                data={
                    "return_home": True,
                    "distance_traveled": distance,
                    "start_position": position
                }
            )
        except Exception as e:
            self.log.error(f"Return home failed: {e}")
            return ToolResult(success=False, message=f"Return home failed: {str(e)}")


def register_system_tools(registry, drone_controller, event_bus):
    """
    Register all system tools.
    
    Args:
        registry: ToolRegistry instance
        drone_controller: DroneController instance
        event_bus: EventBus instance
    """
    registry.register(GetStatusTool(drone_controller))
    registry.register(EmergencyStopTool(drone_controller, event_bus))
    registry.register(EmergencyLandTool(drone_controller, event_bus))
    registry.register(ReturnHomeTool(drone_controller, event_bus))
    registry.register(WaitTool())
    registry.register(SayTool(event_bus))
    registry.register(ClearAbortTool())
