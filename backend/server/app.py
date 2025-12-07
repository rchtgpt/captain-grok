"""
Flask application factory for Grok-Pilot server.
"""

from flask import Flask, jsonify
from flask_cors import CORS
from core.logger import get_logger

log = get_logger('server')


def create_app(drone_controller, grok_client, tool_registry, event_bus):
    """
    Create and configure Flask application.
    
    Args:
        drone_controller: DroneController instance
        grok_client: GrokClient instance
        tool_registry: ToolRegistry instance
        event_bus: EventBus instance
        
    Returns:
        Configured Flask app
    """
    app = Flask(__name__)
    
    # Enable CORS for all routes
    CORS(app)
    
    # Store component references for route access
    app.drone = drone_controller
    app.grok = grok_client
    app.tools = tool_registry
    app.events = event_bus
    
    # Import and register blueprints
    from .routes import commands_bp, status_bp, voice_bp, video_bp
    
    app.register_blueprint(commands_bp, url_prefix='/command')
    app.register_blueprint(status_bp, url_prefix='/status')
    app.register_blueprint(voice_bp, url_prefix='/voice')
    app.register_blueprint(video_bp, url_prefix='/video')
    
    # Root endpoint
    @app.route('/')
    def index():
        return {
            'name': 'Grok-Pilot',
            'version': '1.0.0',
            'status': 'operational',
            'endpoints': {
                'command': '/command - POST - Execute text command',
                'status': '/status - GET - Get system status',
                'abort': '/status/abort - POST - Emergency stop',
                'voice': '/voice/webhook - POST - Twilio webhook',
                'video': '/video/stream - GET - MJPEG video stream'
            }
        }
    
    # Error handlers
    @app.errorhandler(400)
    def bad_request(error):
        """Handle 400 Bad Request errors."""
        log.warning(f"Bad request: {error}")
        return jsonify({
            'error': str(error),
            'status': 'error'
        }), 400
    
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Endpoint not found'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        log.error(f"Internal server error: {error}")
        return jsonify({'error': 'Internal server error'}), 500
    
    log.info("Flask app created successfully")
    
    return app
