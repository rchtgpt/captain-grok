"""Route blueprints for Grok-Pilot server."""

from .commands import commands_bp
from .status import status_bp
from .voice import voice_bp
from .video import video_bp
from .images import images_bp
from .memory import memory_bp
from .targets import targets_bp
from .session import bp as session_bp, sessions_bp
from .tailing import bp as tailing_bp

__all__ = [
    'commands_bp', 
    'status_bp', 
    'voice_bp', 
    'video_bp', 
    'images_bp', 
    'memory_bp', 
    'targets_bp',
    'session_bp',
    'sessions_bp',
    'tailing_bp'
]
