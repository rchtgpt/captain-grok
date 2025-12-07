#!/usr/bin/env python3
"""
Grok-Pilot: Voice-Controlled Drone System
==========================================

A hackathon-winning project combining xAI Grok, DJI Tello drone, and voice control.

Usage:
    python main.py                # Normal mode with real drone
    python main.py --mock         # Mock mode for testing
    python main.py --debug        # Enable debug logging
    python main.py --no-window    # Disable video window

Author: Built for hackathon
License: MIT
"""

import sys
import argparse

from config.settings import get_settings
from core.logger import setup_logging, get_logger
from core.events import EventBus
from core.keyboard_listener import create_keyboard_listener
from drone.controller import DroneController
from ai.grok_client import GrokClient
from tools.registry import ToolRegistry
from tools.drone_tools import register_drone_tools
from tools.vision_tools import register_vision_tools
from tools.system_tools import register_system_tools
from tools.safety_tools import register_safety_tools
from server.app import create_app


def parse_arguments():
    """
    Parse command line arguments.
    
    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description='Grok-Pilot: Voice-Controlled Drone System',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                  # Run with real drone
  python main.py --mock           # Test without drone hardware
  python main.py --debug          # Enable debug logging
  python main.py --mock --debug   # Test mode with debug output
        """
    )
    
    parser.add_argument(
        '--mock',
        action='store_true',
        help='Use mock drone instead of real hardware'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )
    
    parser.add_argument(
        '--no-window',
        action='store_true',
        help='Disable OpenCV video window'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Use real drone camera but simulate all flight commands (MOTORS OFF)'
    )
    
    parser.add_argument(
        '--host',
        type=str,
        default=None,
        help='Flask server host (default: from .env or 0.0.0.0)'
    )
    
    parser.add_argument(
        '--port',
        type=int,
        default=None,
        help='Flask server port (default: from .env or 5000)'
    )
    
    return parser.parse_args()


def print_banner(settings, args):
    """
    Print startup banner with system information.
    
    Args:
        settings: Settings object
        args: Parsed arguments
    """
    print("\n" + "="*70)
    print("  🚁 GROK-PILOT: Voice-Controlled Drone System")
    print("="*70)
    mode_text = 'DRY-RUN (Real camera, simulated flight)' if args.dry_run else ('MOCK (Testing)' if args.mock else 'REAL DRONE')
    print(f"  Mode:         {mode_text}")
    print(f"  Server:       http://{settings.FLASK_HOST}:{settings.FLASK_PORT}")
    print(f"  Video:        {'Disabled' if not settings.VIDEO_ENABLED else 'Web Stream (/video/stream)'}")
    print(f"  Log Level:    {'DEBUG' if args.debug else settings.LOG_LEVEL}")
    print("="*70)
    print("\n  🎯 Endpoints:")
    print(f"     POST /command        - Execute text command")
    print(f"     GET  /status         - Get system status")
    print(f"     POST /status/abort   - Emergency stop")
    print(f"     POST /voice/webhook  - Twilio webhook")
    print(f"     GET  /video/stream   - MJPEG video stream")
    print("="*70 + "\n")


def main():
    """Main entry point for Grok-Pilot."""
    # Parse arguments
    args = parse_arguments()
    
    # Validate flags
    if args.mock and args.dry_run:
        print("❌ Error: Cannot use --mock and --dry-run together")
        print("  --mock: Full simulation (fake camera, fake drone)")
        print("  --dry-run: Real camera, simulated flight (motors off)")
        sys.exit(1)
    
    # Load settings
    settings = get_settings()
    
    # Override settings from args
    if args.host:
        settings.FLASK_HOST = args.host
    if args.port:
        settings.FLASK_PORT = args.port
    if args.no_window:
        settings.VIDEO_ENABLED = False
    
    # Validate settings
    valid, error = settings.validate()
    if not valid:
        print(f"❌ Configuration Error: {error}")
        print("\nPlease:")
        print("  1. Copy .env.example to .env")
        print("  2. Add your XAI_API_KEY to .env")
        sys.exit(1)
    
    # Setup logging
    log_level = 'DEBUG' if args.debug else settings.LOG_LEVEL
    setup_logging(level=log_level, use_colors=settings.LOG_COLORS)
    log = get_logger('main')
    
    log.info("🚀 Grok-Pilot initializing...")
    
    try:
        # Initialize event bus
        log.debug("Creating event bus")
        event_bus = EventBus()
        
        # Initialize Grok AI client
        log.info("🤖 Connecting to xAI Grok...")
        grok_client = GrokClient(settings)
        log.success(f"✅ Grok client ready (model: {settings.XAI_MODEL})")
        
        # Initialize drone controller
        mode_log = 'mock' if args.mock else ('dry-run' if args.dry_run else 'real')
        log.info(f"🛸 Initializing drone ({mode_log})...")
        drone = DroneController(
            event_bus=event_bus,
            settings=settings,
            use_mock=args.mock,
            dry_run=args.dry_run
        )
        
        # Connect to drone
        try:
            drone.connect()
            battery = drone.get_battery()
            log.success(f"✅ Drone connected! Battery: {battery}%")
            
            if battery < settings.LOW_BATTERY_THRESHOLD:
                log.warning(f"⚠️  Low battery: {battery}%")
        
        except Exception as e:
            log.error(f"Failed to connect to drone: {e}")
            if not args.mock:
                log.info("Tip: Use --mock flag to test without drone hardware")
                sys.exit(1)
        
        # Start video stream if enabled (for MJPEG web streaming)
        # Note: OpenCV window display is disabled in server mode 
        # Access video via GET /video/stream endpoint
        if settings.VIDEO_ENABLED and drone.video:
            log.info("📹 Starting video stream...")
            try:
                drone.video.start()
                log.success("✅ Video stream started")
                log.info("📺 Video available at GET /video/stream")
            except Exception as e:
                log.warning(f"Video stream failed: {e}")
        
        # Register all tools
        log.info("🔧 Registering tools...")
        tool_registry = ToolRegistry()
        
        # Pass grok_client to drone tools for vision-based safety checks
        register_drone_tools(tool_registry, drone, grok_client)
        register_vision_tools(tool_registry, drone, grok_client)
        register_system_tools(tool_registry, drone, event_bus)
        register_safety_tools(tool_registry, drone, grok_client)
        
        tool_count = len(tool_registry)
        log.success(f"✅ Registered {tool_count} tools (including safety tools)")
        
        if args.debug:
            log.debug("Available tools:")
            for tool in tool_registry.list_all():
                log.debug(f"  - {tool.name}: {tool.description}")
        
        # Create Flask app
        log.info("🌐 Creating Flask server...")
        app = create_app(drone, grok_client, tool_registry, event_bus)
        log.success("✅ Flask app ready")
        
        # Start keyboard listener for emergency controls
        log.info("⌨️  Starting keyboard listener...")
        keyboard_listener = create_keyboard_listener(drone, event_bus)
        keyboard_listener.start()
        log.success("✅ Keyboard listener active")
        
        # Print banner
        print_banner(settings, args)
        
        # Print quick start guide
        print("  💡 Quick Start:")
        print(f"     curl -X POST http://localhost:{settings.FLASK_PORT}/command \\")
        print("       -H 'Content-Type: application/json' \\")
        print("       -d '{{\"text\": \"take off and look around\"}}'")
        print()
        print("  🎮 Emergency Hotkeys:")
        print("     [L] - 🚨 Emergency Land NOW")
        print("     [H] - 🏠 Return Home & Land")
        print("     [S] - 🛑 Emergency Stop (Hover)")
        print("     [Q] - ❌ Quit Server")
        print("\n  Press Ctrl+C to stop\n")
        
        # Run server
        log.info(f"Starting server on {settings.FLASK_HOST}:{settings.FLASK_PORT}")
        app.run(
            host=settings.FLASK_HOST,
            port=settings.FLASK_PORT,
            threaded=True,
            debug=False  # We handle logging ourselves
        )
    
    except KeyboardInterrupt:
        log.info("\n👋 Shutting down gracefully...")
    
    except Exception as e:
        log.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
    
    finally:
        # Cleanup
        try:
            if 'keyboard_listener' in locals():
                keyboard_listener.stop()
        except:
            pass
        
        try:
            if 'drone' in locals():
                log.info("Disconnecting drone...")
                drone.disconnect()
        except:
            pass
        
        log.info("✅ Grok-Pilot stopped. Goodbye!")


if __name__ == '__main__':
    main()
