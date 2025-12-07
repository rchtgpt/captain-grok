"""Custom exceptions for Grok-Pilot."""


class GrokPilotError(Exception):
    """Base exception for all Grok-Pilot errors."""
    pass


class AbortException(GrokPilotError):
    """Raised when a mission is aborted by user or system."""
    pass


class DroneConnectionError(GrokPilotError):
    """Raised when drone connection fails or is lost."""
    pass


class SafetyViolationError(GrokPilotError):
    """Raised when a safety limit is violated."""
    pass


class GrokAPIError(GrokPilotError):
    """Raised when xAI Grok API call fails."""
    pass


class VideoStreamError(GrokPilotError):
    """Raised when video stream fails."""
    pass


class ToolExecutionError(GrokPilotError):
    """Raised when a tool execution fails."""
    pass
