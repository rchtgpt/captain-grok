"""
Tool registry for managing all available tools.
"""

from typing import Dict, List, Optional, Any
from core.logger import get_logger
from core.exceptions import ToolExecutionError
from .base import BaseTool, ToolResult


class ToolRegistry:
    """
    Central registry for all tools.
    Manages tool registration, lookup, and execution.
    """
    
    def __init__(self):
        """Initialize the tool registry."""
        self._tools: Dict[str, BaseTool] = {}
        self.log = get_logger('tools')
    
    def register(self, tool: BaseTool) -> None:
        """
        Register a tool.
        
        Args:
            tool: Tool instance to register
        """
        if tool.name in self._tools:
            self.log.warning(f"Tool '{tool.name}' already registered, overwriting")
        
        self._tools[tool.name] = tool
        self.log.debug(f"Registered tool: {tool.name}")
    
    def get(self, name: str) -> Optional[BaseTool]:
        """
        Get a tool by name.
        
        Args:
            name: Tool name
            
        Returns:
            Tool instance or None if not found
        """
        return self._tools.get(name)
    
    def list_all(self) -> List[BaseTool]:
        """
        Get all registered tools.
        
        Returns:
            List of tool instances
        """
        return list(self._tools.values())
    
    def get_schemas(self) -> List[Dict[str, Any]]:
        """
        Get OpenAI-compatible schemas for all tools.
        
        Returns:
            List of tool schemas
        """
        return [tool.to_openai_schema() for tool in self._tools.values()]
    
    def execute(self, name: str, **kwargs) -> ToolResult:
        """
        Execute a tool by name.
        
        Args:
            name: Tool name
            **kwargs: Tool parameters
            
        Returns:
            ToolResult
            
        Raises:
            ToolExecutionError: If tool not found or execution fails
        """
        tool = self.get(name)
        
        if tool is None:
            error_msg = f"Tool '{name}' not found"
            self.log.error(error_msg)
            return ToolResult(
                success=False,
                message=error_msg
            )
        
        try:
            self.log.info(f"Executing tool: {name}")
            result = tool.execute(**kwargs)
            
            if result.success:
                self.log.success(f"Tool '{name}' executed successfully")
            else:
                self.log.warning(f"Tool '{name}' failed: {result.message}")
            
            return result
        
        except Exception as e:
            error_msg = f"Tool '{name}' raised exception: {e}"
            self.log.error(error_msg)
            return ToolResult(
                success=False,
                message=error_msg
            )
    
    def __len__(self) -> int:
        """Get number of registered tools."""
        return len(self._tools)
    
    def __contains__(self, name: str) -> bool:
        """Check if tool is registered."""
        return name in self._tools
    
    def __repr__(self) -> str:
        """String representation."""
        tool_names = ', '.join(self._tools.keys())
        return f"ToolRegistry({len(self._tools)} tools: [{tool_names}])"
