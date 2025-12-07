"""
Centralized configuration management for Grok-Pilot.
Loads settings from environment variables with sensible defaults.
"""

import os
from typing import Optional
from dotenv import load_dotenv


class Settings:
    """Application settings loaded from environment variables."""
    
    def __init__(self):
        """Initialize settings from environment variables."""
        # Load .env file
        load_dotenv()
        
        # xAI API Configuration
        self.XAI_API_KEY: str = os.getenv('XAI_API_KEY', '')
        self.XAI_MODEL: str = os.getenv('XAI_MODEL', 'grok-3-fast')
        self.XAI_VISION_MODEL: str = os.getenv('XAI_VISION_MODEL', 'grok-2-vision-1212')
        self.XAI_REALTIME_MODEL: str = os.getenv('XAI_REALTIME_MODEL', 'grok-3-fast')
        
        # API Endpoints
        self.XAI_API_BASE: str = 'https://api.x.ai/v1'
        self.XAI_REALTIME_URL: str = 'wss://api.x.ai/v1/realtime'
        
        # Flask Server Configuration
        self.FLASK_HOST: str = os.getenv('FLASK_HOST', '0.0.0.0')
        self.FLASK_PORT: int = int(os.getenv('FLASK_PORT', '8080'))
        self.FLASK_DEBUG: bool = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
        
        # Drone Configuration
        self.DRONE_ENABLED: bool = os.getenv('DRONE_ENABLED', 'true').lower() == 'true'
        self.VIDEO_ENABLED: bool = os.getenv('VIDEO_ENABLED', 'true').lower() == 'true'
        
        # Safety Limits
        self.MAX_HEIGHT_CM: int = 200
        self.MIN_MOVE_DISTANCE: int = 20
        self.MAX_MOVE_DISTANCE: int = 100
        self.LOW_BATTERY_THRESHOLD: int = 20
        
        # Logging Configuration
        self.LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO').upper()
        self.LOG_COLORS: bool = os.getenv('LOG_COLORS', 'true').lower() == 'true'
        
        # Video Configuration
        self.VIDEO_WIDTH: int = 960
        self.VIDEO_HEIGHT: int = 720
        self.VIDEO_FPS: int = 30
        
    def validate(self) -> tuple[bool, Optional[str]]:
        """
        Validate that required settings are present.
        
        Returns:
            tuple: (is_valid, error_message)
        """
        if not self.XAI_API_KEY:
            return False, "XAI_API_KEY is not set. Please set it in .env file."
        
        if self.FLASK_PORT < 1024 or self.FLASK_PORT > 65535:
            return False, f"Invalid FLASK_PORT: {self.FLASK_PORT}. Must be between 1024 and 65535."
        
        return True, None
    
    def __repr__(self) -> str:
        """Return a string representation (hiding sensitive data)."""
        return (
            f"Settings(\n"
            f"  XAI_API_KEY={'*' * 8 if self.XAI_API_KEY else 'NOT SET'},\n"
            f"  XAI_MODEL={self.XAI_MODEL},\n"
            f"  FLASK_HOST={self.FLASK_HOST},\n"
            f"  FLASK_PORT={self.FLASK_PORT},\n"
            f"  DRONE_ENABLED={self.DRONE_ENABLED},\n"
            f"  VIDEO_ENABLED={self.VIDEO_ENABLED}\n"
            f")"
        )


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """
    Get or create the global settings instance.
    
    Returns:
        Settings: The global settings object
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
