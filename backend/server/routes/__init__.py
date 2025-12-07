"""Route blueprints for Grok-Pilot server."""

from .commands import commands_bp
from .status import status_bp
from .voice import voice_bp
from .video import video_bp
from .images import images_bp

__all__ = ['commands_bp', 'status_bp', 'voice_bp', 'video_bp', 'images_bp']
