"""
Keyboard listener for emergency controls.
Allows instant drone control via keyboard hotkeys while server is running.
"""

import threading
import sys
import select
from typing import Optional, Callable
from core.logger import get_logger

log = get_logger('keyboard')


class KeyboardListener:
    """
    Listen for keyboard input in a background thread.
    Provides emergency hotkeys for drone control.
    """
    
    def __init__(self, drone_controller, event_bus):
        """
        Initialize keyboard listener.
        
        Args:
            drone_controller: DroneController instance
            event_bus: EventBus instance
        """
        self.drone = drone_controller
        self.event_bus = event_bus
        self.log = log
        
        self._running = False
        self._thread: Optional[threading.Thread] = None
        
        # Hotkey mappings
        self.hotkeys = {
            'L': ('emergency_land', '🚨 Emergency Land'),
            'H': ('return_home', '🏠 Return Home'),
            'S': ('emergency_stop', '🛑 Emergency Stop (Hover)'),
            'Q': ('quit', '❌ Quit Server'),
        }
    
    def start(self) -> None:
        """Start the keyboard listener in a background thread."""
        if self._running:
            self.log.warning("Keyboard listener already running")
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()
        
        self.log.info("⌨️  Keyboard listener started!")
        self.log.info("━" * 60)
        self.log.info("🎮 EMERGENCY HOTKEYS:")
        for key, (action, description) in self.hotkeys.items():
            self.log.info(f"   [{key}] - {description}")
        self.log.info("━" * 60)
    
    def stop(self) -> None:
        """Stop the keyboard listener."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)
        self.log.info("Keyboard listener stopped")
    
    def _listen_loop(self) -> None:
        """Main listening loop (runs in background thread)."""
        self.log.debug("Keyboard listener loop started")
        
        try:
            import tty
            import termios
            
            # Save terminal settings
            old_settings = termios.tcgetattr(sys.stdin)
            
            try:
                # Set terminal to raw mode for single-key input
                tty.setcbreak(sys.stdin.fileno())
                
                while self._running:
                    # Check if input is available (non-blocking with 0.1s timeout)
                    if select.select([sys.stdin], [], [], 0.1)[0]:
                        key = sys.stdin.read(1).upper()
                        
                        if key in self.hotkeys:
                            action, description = self.hotkeys[key]
                            self.log.warning(f"🎮 HOTKEY PRESSED: [{key}] - {description}")
                            self._handle_hotkey(action)
            
            finally:
                # Restore terminal settings
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
        
        except Exception as e:
            # If terminal manipulation fails (e.g., not a TTY), fall back to simple input
            self.log.debug(f"Terminal manipulation not available: {e}")
            self._simple_listen_loop()
    
    def _simple_listen_loop(self) -> None:
        """Fallback listening loop for environments without TTY."""
        self.log.debug("Using simple keyboard listener (press Enter after key)")
        
        while self._running:
            try:
                # This will block until Enter is pressed
                if select.select([sys.stdin], [], [], 0.5)[0]:
                    key = sys.stdin.readline().strip().upper()
                    
                    if key and key[0] in self.hotkeys:
                        action, description = self.hotkeys[key[0]]
                        self.log.warning(f"🎮 HOTKEY PRESSED: [{key[0]}] - {description}")
                        self._handle_hotkey(action)
            except:
                break
    
    def _handle_hotkey(self, action: str) -> None:
        """
        Handle a hotkey press.
        
        Args:
            action: Action to perform
        """
        try:
            if action == 'emergency_land':
                self.log.warning("🚨🚨🚨 EMERGENCY LAND VIA HOTKEY 🚨🚨🚨")
                self.drone.emergency_land()
                self.event_bus.publish('keyboard_emergency_land', {})
            
            elif action == 'return_home':
                self.log.warning("🏠 RETURN HOME VIA HOTKEY")
                self.drone.return_home_and_land()
                self.event_bus.publish('keyboard_return_home', {})
            
            elif action == 'emergency_stop':
                self.log.warning("🛑 EMERGENCY STOP VIA HOTKEY")
                self.drone.emergency_stop()
                self.event_bus.publish('keyboard_emergency_stop', {})
            
            elif action == 'quit':
                self.log.warning("❌ QUIT VIA HOTKEY - Shutting down...")
                # Land if flying
                if self.drone.state_machine.is_flying():
                    self.log.info("Landing before quit...")
                    try:
                        self.drone.emergency_land()
                    except:
                        pass
                
                # Publish shutdown event
                self.event_bus.publish('shutdown', {'source': 'keyboard'})
                
                # Exit
                import os
                os._exit(0)
        
        except Exception as e:
            self.log.error(f"Hotkey handler failed: {e}")
    
    def is_running(self) -> bool:
        """Check if listener is running."""
        return self._running


def create_keyboard_listener(drone_controller, event_bus) -> KeyboardListener:
    """
    Factory function to create a keyboard listener.
    
    Args:
        drone_controller: DroneController instance
        event_bus: EventBus instance
        
    Returns:
        KeyboardListener instance
    """
    return KeyboardListener(drone_controller, event_bus)
