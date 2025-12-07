"""
State machine for drone operation modes.
"""

from enum import Enum, auto
from typing import Optional
import threading


class DroneState(Enum):
    """Possible states for the drone."""
    
    IDLE = auto()           # On ground, not connected
    CONNECTED = auto()      # Connected but not flying
    HOVERING = auto()       # In air, hovering
    EXECUTING = auto()      # Executing a command/code
    SEARCHING = auto()      # In persistent search mode
    LANDING = auto()        # Landing in progress
    EMERGENCY = auto()      # Emergency stop activated


class StateMachine:
    """
    Thread-safe state machine for drone operations.
    
    Valid transitions:
        IDLE -> CONNECTED
        CONNECTED -> HOVERING (takeoff)
        HOVERING -> EXECUTING | SEARCHING | LANDING
        EXECUTING -> HOVERING | EMERGENCY
        SEARCHING -> HOVERING | EMERGENCY
        LANDING -> CONNECTED
        EMERGENCY -> HOVERING (recovery)
        * -> EMERGENCY (always allowed)
    """
    
    # Valid state transitions
    VALID_TRANSITIONS = {
        DroneState.IDLE: {DroneState.CONNECTED},
        DroneState.CONNECTED: {DroneState.HOVERING, DroneState.IDLE},
        DroneState.HOVERING: {
            DroneState.EXECUTING,
            DroneState.SEARCHING,
            DroneState.LANDING,
            DroneState.EMERGENCY,
            DroneState.CONNECTED
        },
        DroneState.EXECUTING: {
            DroneState.HOVERING,
            DroneState.EMERGENCY
        },
        DroneState.SEARCHING: {
            DroneState.HOVERING,
            DroneState.EMERGENCY
        },
        DroneState.LANDING: {
            DroneState.CONNECTED,
            DroneState.EMERGENCY
        },
        DroneState.EMERGENCY: {
            DroneState.HOVERING,
            DroneState.LANDING,
            DroneState.CONNECTED
        }
    }
    
    def __init__(self, initial_state: DroneState = DroneState.IDLE):
        """
        Initialize the state machine.
        
        Args:
            initial_state: Starting state
        """
        self._state = initial_state
        self._lock = threading.Lock()
        self._callbacks = []
    
    @property
    def state(self) -> DroneState:
        """Get the current state (thread-safe)."""
        with self._lock:
            return self._state
    
    def transition_to(self, new_state: DroneState, force: bool = False) -> bool:
        """
        Transition to a new state.
        
        Args:
            new_state: The target state
            force: If True, bypass validation (use for emergency)
            
        Returns:
            True if transition successful, False otherwise
        """
        with self._lock:
            current = self._state
            
            # Allow same-state "transitions"
            if current == new_state:
                return True
            
            # Emergency always allowed
            if new_state == DroneState.EMERGENCY:
                self._state = new_state
                self._notify_callbacks(current, new_state)
                return True
            
            # Check if transition is valid
            if force or new_state in self.VALID_TRANSITIONS.get(current, set()):
                self._state = new_state
                self._notify_callbacks(current, new_state)
                return True
            
            return False
    
    def is_flying(self) -> bool:
        """Check if drone is in a flying state."""
        return self.state in {
            DroneState.HOVERING,
            DroneState.EXECUTING,
            DroneState.SEARCHING
        }
    
    def can_execute(self) -> bool:
        """Check if drone can execute commands."""
        return self.state in {
            DroneState.HOVERING,
            DroneState.EXECUTING,
            DroneState.SEARCHING
        }
    
    def on_state_change(self, callback: callable) -> None:
        """
        Register a callback for state changes.
        
        Args:
            callback: Function(old_state, new_state) to call on transition
        """
        with self._lock:
            self._callbacks.append(callback)
    
    def _notify_callbacks(self, old_state: DroneState, new_state: DroneState) -> None:
        """Notify all registered callbacks of state change."""
        for callback in self._callbacks:
            try:
                callback(old_state, new_state)
            except Exception as e:
                print(f"Error in state change callback: {e}")
    
    def __str__(self) -> str:
        """String representation of current state."""
        return f"StateMachine(state={self.state.name})"
