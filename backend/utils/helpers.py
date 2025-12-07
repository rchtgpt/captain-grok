"""
Helper utility functions for Grok-Pilot.
"""

from typing import List, Dict, Any


def is_abort_keyword(text: str) -> bool:
    """
    Check if text contains abort keywords.
    
    Args:
        text: Text to check
        
    Returns:
        True if abort keyword found
    """
    abort_keywords = [
        'stop',
        'halt',
        'wait',
        'abort',
        'emergency',
        'cancel',
        'freeze'
    ]
    
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in abort_keywords)


def format_tool_results(tool_results: List[Dict[str, Any]]) -> str:
    """
    Format tool execution results into a readable string.
    
    Args:
        tool_results: List of tool result dicts
        
    Returns:
        Formatted string
    """
    if not tool_results:
        return "No tools executed"
    
    lines = []
    for result in tool_results:
        tool_name = result.get('tool', 'unknown')
        success = result.get('success', False)
        message = result.get('message', '')
        
        status = "✅" if success else "❌"
        lines.append(f"{status} {tool_name}: {message}")
    
    return "\n".join(lines)
