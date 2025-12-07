"""
Simplified Drone Memory System.

Stripped down to essentials:
- Drone heading and position tracking
- Conversation history
- Session directory management

All entity/person tracking removed - now handled by targets system.
"""

import threading
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

from core.logger import get_logger

log = get_logger('memory')


@dataclass
class ConversationTurn:
    """A single turn in the conversation."""
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime
    
    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat()
        }


class DroneMemory:
    """
    Simplified drone memory.
    
    Features:
    - Heading and position tracking
    - Conversation history for context
    - Session directory management
    
    Entity/person tracking removed - use TargetManager for that.
    """
    
    def __init__(self, session_dir: Optional[Path] = None):
        # Session storage
        if session_dir is None:
            session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            session_dir = Path("data/sessions") / session_id
        
        self.session_dir = Path(session_dir)
        self.session_dir.mkdir(parents=True, exist_ok=True)
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Drone state
        self._heading: int = 0  # 0 = original heading at takeoff
        self._position: Dict[str, int] = {'x': 0, 'y': 0, 'z': 0}
        
        # Conversation history
        self._conversation: List[ConversationTurn] = []
        
        log.info(f"DroneMemory initialized (simplified). Session: {self.session_dir}")
    
    # ==================== PROPERTIES ====================
    
    @property
    def heading(self) -> int:
        with self._lock:
            return self._heading
    
    @property
    def position(self) -> Dict[str, int]:
        with self._lock:
            return self._position.copy()
    
    # ==================== HEADING & POSITION ====================
    
    def update_heading(self, rotation_degrees: int) -> None:
        """Update heading after rotation."""
        with self._lock:
            old_heading = self._heading
            self._heading = (self._heading + rotation_degrees) % 360
            log.debug(f"Heading updated: {old_heading}° -> {self._heading}°")
    
    def update_position(self, direction: str, distance: int) -> None:
        """Update position after movement."""
        with self._lock:
            import math
            heading_rad = math.radians(self._heading)
            
            if direction == 'forward':
                self._position['x'] += int(distance * math.cos(heading_rad))
                self._position['y'] += int(distance * math.sin(heading_rad))
            elif direction == 'back':
                self._position['x'] -= int(distance * math.cos(heading_rad))
                self._position['y'] -= int(distance * math.sin(heading_rad))
            elif direction == 'left':
                self._position['x'] += int(distance * math.cos(heading_rad - math.pi/2))
                self._position['y'] += int(distance * math.sin(heading_rad - math.pi/2))
            elif direction == 'right':
                self._position['x'] += int(distance * math.cos(heading_rad + math.pi/2))
                self._position['y'] += int(distance * math.sin(heading_rad + math.pi/2))
            elif direction == 'up':
                self._position['z'] += distance
            elif direction == 'down':
                self._position['z'] -= distance
            
            log.debug(f"Position updated: {self._position}")
    
    def reset_position(self) -> None:
        """Reset position and heading (e.g., on takeoff)."""
        with self._lock:
            self._heading = 0
            self._position = {'x': 0, 'y': 0, 'z': 0}
            log.info("Position reset (takeoff)")
    
    # ==================== CONVERSATION ====================
    
    def add_conversation_turn(self, role: str, content: str) -> None:
        """Add a conversation turn."""
        with self._lock:
            self._conversation.append(ConversationTurn(
                role=role,
                content=content,
                timestamp=datetime.now()
            ))
            
            # Keep last 30 turns
            if len(self._conversation) > 30:
                self._conversation = self._conversation[-30:]
    
    def get_conversation_for_ai(self, last_n: int = 10) -> List[dict]:
        """Get recent conversation formatted for AI."""
        with self._lock:
            messages = []
            for turn in self._conversation[-last_n:]:
                messages.append({
                    "role": turn.role,
                    "content": turn.content
                })
            return messages
    
    def get_conversation_history(self) -> List[dict]:
        """Get full conversation history."""
        with self._lock:
            return [turn.to_dict() for turn in self._conversation]
    
    # ==================== CONTEXT FOR AI ====================
    
    def get_context_for_ai(self) -> str:
        """Generate minimal context string for AI system prompt."""
        with self._lock:
            return f"""## DRONE STATE
Heading: {self._heading}° from start
Position: x={self._position['x']}cm, y={self._position['y']}cm, z={self._position['z']}cm
"""
    
    # ==================== PERSISTENCE ====================
    
    def to_dict(self) -> dict:
        """Serialize memory to dict."""
        with self._lock:
            return {
                "heading": self._heading,
                "position": self._position,
                "conversation": [t.to_dict() for t in self._conversation]
            }
    
    def save(self) -> None:
        """Save memory to disk."""
        with self._lock:
            memory_path = self.session_dir / "memory.json"
            with open(memory_path, 'w') as f:
                json.dump(self.to_dict(), f, indent=2, default=str)
            log.info(f"Memory saved to {memory_path}")


# Singleton instance
_memory_instance: Optional[DroneMemory] = None
_memory_lock = threading.Lock()


def get_memory() -> DroneMemory:
    """Get the singleton DroneMemory instance."""
    global _memory_instance
    with _memory_lock:
        if _memory_instance is None:
            _memory_instance = DroneMemory()
        return _memory_instance


def reset_memory() -> DroneMemory:
    """Reset memory (new session)."""
    global _memory_instance
    with _memory_lock:
        _memory_instance = DroneMemory()
        return _memory_instance
