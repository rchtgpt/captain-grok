"""
Event bus for decoupled communication between components.
Implements a publish/subscribe pattern.
"""

from typing import Callable, Dict, List, Any
from collections import defaultdict
import threading


class EventBus:
    """
    Thread-safe event bus for pub/sub communication.
    
    Example:
        bus = EventBus()
        bus.subscribe('abort', lambda data: print(f"Abort: {data}"))
        bus.publish('abort', {'reason': 'user_request'})
    """
    
    def __init__(self):
        """Initialize the event bus."""
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self._lock = threading.Lock()
    
    def subscribe(self, event_type: str, callback: Callable[[Any], None]) -> None:
        """
        Subscribe to an event type.
        
        Args:
            event_type: The type of event to listen for
            callback: Function to call when event is published (receives event data)
        """
        with self._lock:
            if callback not in self._subscribers[event_type]:
                self._subscribers[event_type].append(callback)
    
    def unsubscribe(self, event_type: str, callback: Callable[[Any], None]) -> None:
        """
        Unsubscribe from an event type.
        
        Args:
            event_type: The type of event to stop listening for
            callback: The callback function to remove
        """
        with self._lock:
            if callback in self._subscribers[event_type]:
                self._subscribers[event_type].remove(callback)
    
    def publish(self, event_type: str, data: Any = None) -> None:
        """
        Publish an event to all subscribers.
        
        Args:
            event_type: The type of event to publish
            data: Optional data to pass to subscribers
        """
        # Get subscribers outside lock to avoid deadlock
        with self._lock:
            callbacks = self._subscribers[event_type].copy()
        
        # Call subscribers
        for callback in callbacks:
            try:
                callback(data)
            except Exception as e:
                # Don't let subscriber errors break the event bus
                print(f"Error in event subscriber for '{event_type}': {e}")
    
    def clear(self, event_type: str = None) -> None:
        """
        Clear subscribers for an event type, or all subscribers.
        
        Args:
            event_type: Specific event type to clear, or None for all
        """
        with self._lock:
            if event_type:
                self._subscribers[event_type].clear()
            else:
                self._subscribers.clear()
    
    def subscriber_count(self, event_type: str) -> int:
        """
        Get the number of subscribers for an event type.
        
        Args:
            event_type: The event type to check
            
        Returns:
            Number of subscribers
        """
        with self._lock:
            return len(self._subscribers[event_type])
