"""
Chat message generator for natural conversational responses.
Generates real-time chat messages as the drone operates.
"""

import threading
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from core.logger import get_logger

log = get_logger('chat_generator')


class MessageType(Enum):
    """Types of chat messages for UI styling."""
    USER = "user"           # User's command
    THINKING = "thinking"   # Drone is processing
    ACTION = "action"       # Drone is doing something
    OBSERVATION = "observation"  # Drone sees something
    SUCCESS = "success"     # Task completed
    ERROR = "error"         # Something went wrong
    MEMORY = "memory"       # Recalling from memory
    CLARIFICATION = "clarification"  # Asking for clarification
    SYSTEM = "system"       # System message


@dataclass
class ChatMessage:
    """A chat message with metadata."""
    id: str
    content: str
    message_type: MessageType
    timestamp: datetime
    image_url: Optional[str] = None
    entity_id: Optional[str] = None
    tool_name: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "content": self.content,
            "message": self.content,  # Alias for frontend compatibility
            "message_type": self.message_type.value,
            "type": self.message_type.value,  # Alias for frontend compatibility
            "timestamp": self.timestamp.isoformat(),
            "image_url": self.image_url,
            "entity_id": self.entity_id,
            "tool_name": self.tool_name
        }


class ChatGenerator:
    """
    Generates natural, conversational chat messages.
    
    Creates messages that feel human and engaging rather than robotic.
    Tracks context to vary responses and maintain personality.
    """
    
    def __init__(self):
        self._lock = threading.Lock()
        self._message_counter = 0
        self._last_action: Optional[str] = None
        
        # S&R themed phrases
        self._scanning_phrases = [
            "Scanning ahead...",
            "Checking this direction...",
            "Searching...",
            "Looking around...",
            "Surveying the area..."
        ]
        
        self._found_phrases = [
            "Survivor found!",
            "I see someone!",
            "Found a person!",
            "Contact! I've spotted someone!"
        ]
        
        self._moving_phrases = [
            "Moving in...",
            "On my way...",
            "Heading there now...",
            "Flying over..."
        ]
        
        self._phrase_counters = {
            "scanning": 0,
            "found": 0,
            "moving": 0
        }
    
    def _next_id(self) -> str:
        """Generate next message ID."""
        with self._lock:
            self._message_counter += 1
            return f"msg_{self._message_counter}_{int(datetime.now().timestamp()*1000)}"
    
    def _get_phrase(self, category: str, phrases: List[str]) -> str:
        """Get next phrase from a category, cycling through options."""
        with self._lock:
            idx = self._phrase_counters.get(category, 0)
            phrase = phrases[idx % len(phrases)]
            self._phrase_counters[category] = idx + 1
            return phrase
    
    # ==================== MESSAGE GENERATORS ====================
    
    def user_message(self, content: str) -> ChatMessage:
        """Create a user message."""
        return ChatMessage(
            id=self._next_id(),
            content=content,
            message_type=MessageType.USER,
            timestamp=datetime.now()
        )
    
    def thinking(self, context: Optional[str] = None) -> ChatMessage:
        """Create a thinking/processing message."""
        if context:
            content = f"Processing: {context}..."
        else:
            content = "Let me think about that..."
        
        return ChatMessage(
            id=self._next_id(),
            content=content,
            message_type=MessageType.THINKING,
            timestamp=datetime.now()
        )
    
    def scanning(self, direction: Optional[str] = None) -> ChatMessage:
        """Create a scanning message."""
        base = self._get_phrase("scanning", self._scanning_phrases)
        
        if direction:
            content = f"{base} ({direction})"
        else:
            content = base
        
        return ChatMessage(
            id=self._next_id(),
            content=content,
            message_type=MessageType.ACTION,
            timestamp=datetime.now(),
            tool_name="look"
        )
    
    def rotating(self, degrees: int) -> ChatMessage:
        """Create a rotation message."""
        if degrees > 0:
            direction = "right"
        else:
            direction = "left"
        
        return ChatMessage(
            id=self._next_id(),
            content=f"Turning {direction}...",
            message_type=MessageType.ACTION,
            timestamp=datetime.now(),
            tool_name="rotate"
        )
    
    def moving(self, direction: str, distance: int) -> ChatMessage:
        """Create a movement message."""
        base = self._get_phrase("moving", self._moving_phrases)
        
        return ChatMessage(
            id=self._next_id(),
            content=f"{base} ({direction} {distance}cm)",
            message_type=MessageType.ACTION,
            timestamp=datetime.now(),
            tool_name="move"
        )
    
    def takeoff(self) -> ChatMessage:
        """Create a takeoff message."""
        return ChatMessage(
            id=self._next_id(),
            content="Taking off! Deploying into the area...",
            message_type=MessageType.ACTION,
            timestamp=datetime.now(),
            tool_name="takeoff"
        )
    
    def landing(self) -> ChatMessage:
        """Create a landing message."""
        return ChatMessage(
            id=self._next_id(),
            content="Landing now...",
            message_type=MessageType.ACTION,
            timestamp=datetime.now(),
            tool_name="land"
        )
    
    def survivor_found(
        self,
        description: str,
        direction: str,
        distance_cm: int,
        image_url: Optional[str] = None,
        entity_id: Optional[str] = None
    ) -> ChatMessage:
        """Create a survivor found message."""
        base = self._get_phrase("found", self._found_phrases)
        
        content = (
            f"{base} {description}, "
            f"{direction}, about {distance_cm}cm away."
        )
        
        return ChatMessage(
            id=self._next_id(),
            content=content,
            message_type=MessageType.OBSERVATION,
            timestamp=datetime.now(),
            image_url=image_url,
            entity_id=entity_id,
            tool_name="search"
        )
    
    def object_found(
        self,
        description: str,
        direction: str,
        image_url: Optional[str] = None,
        entity_id: Optional[str] = None
    ) -> ChatMessage:
        """Create an object found message."""
        content = f"I see {description} {direction}."
        
        return ChatMessage(
            id=self._next_id(),
            content=content,
            message_type=MessageType.OBSERVATION,
            timestamp=datetime.now(),
            image_url=image_url,
            entity_id=entity_id
        )
    
    def scene_observation(
        self,
        description: str,
        people_count: int = 0,
        objects: Optional[List[str]] = None
    ) -> ChatMessage:
        """Create a scene observation message."""
        parts = [description]
        
        if people_count > 0:
            if people_count == 1:
                parts.append("I see one person.")
            else:
                parts.append(f"I see {people_count} people.")
        
        if objects:
            parts.append(f"Also visible: {', '.join(objects[:3])}")
        
        return ChatMessage(
            id=self._next_id(),
            content=" ".join(parts),
            message_type=MessageType.OBSERVATION,
            timestamp=datetime.now()
        )
    
    def memory_recall(
        self,
        content: str,
        entity_id: Optional[str] = None
    ) -> ChatMessage:
        """Create a memory recall message."""
        return ChatMessage(
            id=self._next_id(),
            content=content,
            message_type=MessageType.MEMORY,
            timestamp=datetime.now(),
            entity_id=entity_id
        )
    
    def success(
        self,
        content: str,
        entity_id: Optional[str] = None
    ) -> ChatMessage:
        """Create a success message."""
        return ChatMessage(
            id=self._next_id(),
            content=content,
            message_type=MessageType.SUCCESS,
            timestamp=datetime.now(),
            entity_id=entity_id
        )
    
    def error(self, content: str) -> ChatMessage:
        """Create an error message."""
        return ChatMessage(
            id=self._next_id(),
            content=content,
            message_type=MessageType.ERROR,
            timestamp=datetime.now()
        )
    
    def clarification(
        self,
        question: str,
        options: Optional[List[str]] = None
    ) -> ChatMessage:
        """Create a clarification request."""
        if options:
            content = f"{question} ({' or '.join(options)})"
        else:
            content = question
        
        return ChatMessage(
            id=self._next_id(),
            content=content,
            message_type=MessageType.CLARIFICATION,
            timestamp=datetime.now()
        )
    
    def navigation_start(
        self,
        target: str,
        direction: str
    ) -> ChatMessage:
        """Create a navigation starting message."""
        return ChatMessage(
            id=self._next_id(),
            content=f"Heading to {target}. They're {direction}.",
            message_type=MessageType.ACTION,
            timestamp=datetime.now(),
            tool_name="navigate_to"
        )
    
    def navigation_complete(self, target: str) -> ChatMessage:
        """Create a navigation complete message."""
        return ChatMessage(
            id=self._next_id(),
            content=f"I've reached {target}.",
            message_type=MessageType.SUCCESS,
            timestamp=datetime.now()
        )
    
    def named_entity(self, name: str, description: str) -> ChatMessage:
        """Create a named entity message."""
        return ChatMessage(
            id=self._next_id(),
            content=f"Got it! I'll remember them as '{name}'.",
            message_type=MessageType.SUCCESS,
            timestamp=datetime.now()
        )
    
    def search_complete(
        self,
        survivors_found: int,
        objects_found: int
    ) -> ChatMessage:
        """Create a search complete summary."""
        parts = []
        
        if survivors_found > 0:
            if survivors_found == 1:
                parts.append("1 survivor found")
            else:
                parts.append(f"{survivors_found} survivors found")
        
        if objects_found > 0:
            parts.append(f"{objects_found} objects noted")
        
        if parts:
            content = f"Search complete! {', '.join(parts)} and marked."
        else:
            content = "Search complete. Area appears clear."
        
        return ChatMessage(
            id=self._next_id(),
            content=content,
            message_type=MessageType.SUCCESS,
            timestamp=datetime.now()
        )
    
    def return_home_start(self) -> ChatMessage:
        """Create a return home starting message."""
        return ChatMessage(
            id=self._next_id(),
            content="Returning to start position...",
            message_type=MessageType.ACTION,
            timestamp=datetime.now()
        )
    
    def return_home_complete(self) -> ChatMessage:
        """Create a return home complete message."""
        return ChatMessage(
            id=self._next_id(),
            content="Back at starting position!",
            message_type=MessageType.SUCCESS,
            timestamp=datetime.now()
        )
    
    def whats_that_response(
        self,
        description: str,
        entity_id: Optional[str] = None,
        image_url: Optional[str] = None
    ) -> ChatMessage:
        """Create a 'what's that' response."""
        return ChatMessage(
            id=self._next_id(),
            content=f"That's {description}.",
            message_type=MessageType.OBSERVATION,
            timestamp=datetime.now(),
            entity_id=entity_id,
            image_url=image_url
        )
    
    def location_query_response(
        self,
        target: str,
        direction: str,
        distance_cm: int
    ) -> ChatMessage:
        """Create a location query response."""
        return ChatMessage(
            id=self._next_id(),
            content=f"{target} is {direction}, about {distance_cm}cm away.",
            message_type=MessageType.MEMORY,
            timestamp=datetime.now()
        )
    
    def system_message(self, content: str) -> ChatMessage:
        """Create a system message."""
        return ChatMessage(
            id=self._next_id(),
            content=content,
            message_type=MessageType.SYSTEM,
            timestamp=datetime.now()
        )


# Singleton instance
_chat_instance: Optional[ChatGenerator] = None
_chat_lock = threading.Lock()


def get_chat_generator() -> ChatGenerator:
    """Get singleton ChatGenerator instance."""
    global _chat_instance
    with _chat_lock:
        if _chat_instance is None:
            _chat_instance = ChatGenerator()
        return _chat_instance
