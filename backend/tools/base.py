"""
Base tool class for Grok-Pilot tool system.
All tools inherit from BaseTool and follow OpenAI function calling format.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class ToolResult:
    """Result of a tool execution."""
    success: bool
    message: str
    data: Any = None


class BaseTool(ABC):
    """
    Abstract base class for all tools.
    Implements OpenAI-compatible function calling interface.
    """
    
    # Subclasses must define these
    name: str = ""
    description: str = ""
    parameters: Dict[str, Any] = {}
    
    def __init__(self):
        """Initialize the tool."""
        if not self.name:
            raise ValueError(f"{self.__class__.__name__} must define 'name'")
        if not self.description:
            raise ValueError(f"{self.__class__.__name__} must define 'description'")
    
    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        """
        Execute the tool with given parameters.
        
        Args:
            **kwargs: Tool-specific parameters
            
        Returns:
            ToolResult with success status and output
        """
        pass
    
    def to_openai_schema(self) -> Dict[str, Any]:
        """
        Convert tool to OpenAI function calling schema.
        
        Returns:
            Dictionary in OpenAI function format
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters or {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }
    
    def __str__(self) -> str:
        """String representation."""
        return f"{self.__class__.__name__}(name='{self.name}')"
    
    def __repr__(self) -> str:
        """Detailed representation."""
        return (
            f"{self.__class__.__name__}("
            f"name='{self.name}', "
            f"description='{self.description[:50]}...')"
        )
