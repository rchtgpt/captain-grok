"""
Safety system for Grok-Pilot.
Provides abort mechanism and code sandboxing.
"""

import time
import threading
from typing import Any, Dict
from dataclasses import dataclass

from core.exceptions import AbortException, SafetyViolationError
from core.logger import get_logger

log = get_logger('safety')

# Global abort flag (thread-safe)
ABORT_FLAG = threading.Event()


def smart_sleep(seconds: float) -> None:
    """
    Interruptible sleep function that checks abort flag every 100ms.
    
    Args:
        seconds: Time to sleep in seconds
        
    Raises:
        AbortException: If ABORT_FLAG is set during sleep
    """
    end_time = time.time() + seconds
    
    while time.time() < end_time:
        if ABORT_FLAG.is_set():
            log.warning("Abort detected during sleep!")
            raise AbortException("Mission aborted during wait")
        
        # Sleep in small increments
        remaining = end_time - time.time()
        if remaining > 0:
            time.sleep(min(0.1, remaining))


def clear_abort() -> None:
    """Clear the abort flag to allow new missions."""
    ABORT_FLAG.clear()
    log.info("Abort flag cleared")


@dataclass
class ExecutionResult:
    """Result of code execution."""
    success: bool
    message: str
    output: Any = None
    error: Exception = None


class SafetyExecutor:
    """
    Executes Grok-generated code in a sandboxed environment.
    Only exposes safe functions and checks abort flag.
    """
    
    def __init__(self, drone_controller, tool_registry=None):
        """
        Initialize the safety executor.
        
        Args:
            drone_controller: The drone controller instance
            tool_registry: Optional tool registry for additional functions
        """
        self.drone = drone_controller
        self.tools = tool_registry
        self.log = get_logger('sandbox')
    
    def execute(self, code: str) -> ExecutionResult:
        """
        Execute Python code in a restricted namespace.
        
        Args:
            code: Python code string to execute
            
        Returns:
            ExecutionResult with success status and output
        """
        self.log.debug(f"Executing code:\n{code}")
        
        # Check if abort is already set
        if ABORT_FLAG.is_set():
            return ExecutionResult(
                success=False,
                message="Execution aborted before start",
                error=AbortException("Abort flag already set")
            )
        
        # Validate code before execution
        try:
            self._validate_code(code)
        except SafetyViolationError as e:
            self.log.error(f"Code validation failed: {e}")
            return ExecutionResult(
                success=False,
                message=f"Safety violation: {str(e)}",
                error=e
            )
        
        # Build sandbox globals
        sandbox_globals = self._build_sandbox_globals()
        sandbox_locals = {}
        
        # Execute code
        try:
            exec(code, sandbox_globals, sandbox_locals)
            self.log.success("Code executed successfully")
            return ExecutionResult(
                success=True,
                message="Execution completed",
                output=sandbox_locals
            )
        
        except AbortException as e:
            self.log.warning(f"Execution aborted: {e}")
            self.drone.emergency_stop()
            return ExecutionResult(
                success=False,
                message="Execution aborted by user",
                error=e
            )
        
        except Exception as e:
            self.log.error(f"Execution error: {e}")
            # Try to stop drone safely
            try:
                self.drone.hover()
            except:
                pass
            
            return ExecutionResult(
                success=False,
                message=f"Execution error: {str(e)}",
                error=e
            )
    
    def _build_sandbox_globals(self) -> Dict[str, Any]:
        """
        Build the restricted global namespace for code execution.
        
        Returns:
            Dictionary of allowed functions and objects
        """
        sandbox = {
            # Drone control
            'drone': self.drone,
            
            # Safe sleep
            'wait': smart_sleep,
            
            # Basic Python builtins (safe subset)
            'print': print,
            'len': len,
            'range': range,
            'str': str,
            'int': int,
            'float': float,
            'bool': bool,
            'list': list,
            'dict': dict,
            'abs': abs,
            'min': min,
            'max': max,
            'round': round,
            
            # Explicitly block dangerous functions
            '__builtins__': {
                '__import__': None,
                'eval': None,
                'exec': None,
                'compile': None,
                'open': None,
            }
        }
        
        # Add tool functions if registry provided
        if self.tools:
            for tool in self.tools.list_all():
                # Create a wrapped function that executes the tool
                def make_tool_func(t):
                    def tool_func(**kwargs):
                        result = t.execute(**kwargs)
                        if not result.success:
                            raise Exception(result.message)
                        return result.data
                    return tool_func
                
                sandbox[tool.name] = make_tool_func(tool)
        
        return sandbox
    
    def _validate_code(self, code: str) -> None:
        """
        Perform basic validation on code before execution.
        
        Args:
            code: The code to validate
            
        Raises:
            SafetyViolationError: If code contains unsafe patterns
        """
        # Check for dangerous keywords
        dangerous_keywords = [
            'import ',
            'from ',
            '__import__',
            'eval(',
            'exec(',
            'compile(',
            'open(',
            'file(',
            'input(',
            'raw_input(',
            'os.',
            'sys.',
            'subprocess',
            'socket',
        ]
        
        code_lower = code.lower()
        for keyword in dangerous_keywords:
            if keyword.lower() in code_lower:
                raise SafetyViolationError(f"Dangerous keyword detected: {keyword}")
        
        # Check for overly long code (prevent resource exhaustion)
        if len(code) > 10000:
            raise SafetyViolationError("Code too long (max 10000 characters)")
        
        # Try to compile (checks syntax)
        try:
            compile(code, '<sandbox>', 'exec')
        except SyntaxError as e:
            raise SafetyViolationError(f"Syntax error: {e}")
