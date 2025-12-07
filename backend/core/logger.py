"""
Colored logging system with emoji support for Grok-Pilot.
Provides beautiful, easy-to-read console output.
"""

import logging
import sys
from datetime import datetime
from typing import Optional
from colorama import Fore, Back, Style, init

# Initialize colorama for cross-platform color support
init(autoreset=True)


# Custom log level for success messages
SUCCESS = 25
logging.addLevelName(SUCCESS, 'SUCCESS')


class ColoredFormatter(logging.Formatter):
    """Custom formatter that adds colors and emojis to log messages."""
    
    # Emoji mapping for log levels
    EMOJIS = {
        'DEBUG': '🔵',
        'INFO': '🚀',
        'SUCCESS': '✅',
        'WARNING': '⚠️',
        'ERROR': '❌',
        'CRITICAL': '🛑'
    }
    
    # Color mapping for log levels
    COLORS = {
        'DEBUG': Fore.CYAN,
        'INFO': Fore.WHITE,
        'SUCCESS': Fore.GREEN,
        'WARNING': Fore.YELLOW,
        'ERROR': Fore.RED,
        'CRITICAL': Fore.RED + Back.WHITE
    }
    
    def __init__(self, use_colors: bool = True):
        """
        Initialize the colored formatter.
        
        Args:
            use_colors: Whether to use colors in output
        """
        super().__init__()
        self.use_colors = use_colors
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format the log record with colors and emojis.
        
        Args:
            record: The log record to format
            
        Returns:
            Formatted log string
        """
        # Get timestamp
        timestamp = datetime.fromtimestamp(record.created).strftime('%H:%M:%S')
        
        # Get emoji and color
        level_name = record.levelname
        emoji = self.EMOJIS.get(level_name, '📝')
        color = self.COLORS.get(level_name, Fore.WHITE) if self.use_colors else ''
        reset = Style.RESET_ALL if self.use_colors else ''
        
        # Format module name (truncate if too long)
        module = record.name
        if len(module) > 15:
            module = module[:12] + '...'
        
        # Build the log line
        log_line = (
            f"{Fore.WHITE}[{timestamp}]{reset} "
            f"{emoji} {color}{level_name:8}{reset} "
            f"{Fore.BLUE}{module:15}{reset} "
            f"{color}{record.getMessage()}{reset}"
        )
        
        # Add exception info if present
        if record.exc_info:
            log_line += '\n' + self.formatException(record.exc_info)
        
        return log_line


class GrokPilotLogger(logging.Logger):
    """Custom logger with success level."""
    
    def success(self, message: str, *args, **kwargs):
        """
        Log a success message.
        
        Args:
            message: The message to log
            *args: Additional arguments
            **kwargs: Additional keyword arguments
        """
        if self.isEnabledFor(SUCCESS):
            self._log(SUCCESS, message, args, **kwargs)


# Register custom logger class
logging.setLoggerClass(GrokPilotLogger)


# Global logger registry
_loggers: dict[str, logging.Logger] = {}


def setup_logging(level: str = 'INFO', use_colors: bool = True) -> None:
    """
    Setup the logging system for the entire application.
    
    Args:
        level: The logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        use_colors: Whether to use colored output
    """
    # Convert string level to logging constant
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Remove existing handlers
    root_logger.handlers.clear()
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    
    # Set formatter
    formatter = ColoredFormatter(use_colors=use_colors)
    console_handler.setFormatter(formatter)
    
    # Add handler to root logger
    root_logger.addHandler(console_handler)
    
    # Suppress noisy third-party loggers
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    logging.getLogger('asyncio').setLevel(logging.WARNING)
    
    # Suppress djitellopy spam (especially RC control commands)
    # The library adds its own handler, so we need to clear handlers AND set level
    djitellopy_logger = logging.getLogger('djitellopy')
    djitellopy_logger.handlers.clear()  # Remove their custom StreamHandler
    djitellopy_logger.setLevel(logging.WARNING)
    djitellopy_logger.propagate = False  # Don't let it propagate to root


def get_logger(name: str) -> GrokPilotLogger:
    """
    Get a logger instance for a specific module.
    
    Args:
        name: The name of the module/component
        
    Returns:
        Logger instance
    """
    if name not in _loggers:
        _loggers[name] = logging.getLogger(name)
    
    return _loggers[name]
