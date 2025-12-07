"""
Status and control routes for Grok-Pilot.
"""

from flask import Blueprint, jsonify, current_app
from core.logger import get_logger
from drone.safety import ABORT_FLAG, clear_abort

status_bp = Blueprint('status', __name__)
log = get_logger('routes.status')


@status_bp.route('/', methods=['GET'])
def get_status():
    """
    Get full system status.
    
    Response JSON:
        {
            "drone": {...},
            "system": {...}
        }
    """
    try:
        drone_status = current_app.drone.get_status()
        
        return jsonify({
            'drone': {
                'connected': drone_status.connected,
                'flying': drone_status.flying,
                'battery': drone_status.battery,
                'height': drone_status.height,
                'temperature': drone_status.temperature,
                'state': drone_status.state.name
            },
            'system': {
                'abort_flag': ABORT_FLAG.is_set(),
                'video_running': current_app.drone.video and current_app.drone.video.is_running,
                'tools_count': len(current_app.tools)
            }
        })
    
    except Exception as e:
        log.error(f"Failed to get status: {e}")
        return jsonify({'error': str(e)}), 500


@status_bp.route('/abort', methods=['POST'])
def trigger_abort():
    """
    Trigger emergency abort.
    
    Response JSON:
        {
            "status": "aborted",
            "message": "..."
        }
    """
    try:
        log.warning("ABORT triggered via API")
        current_app.events.publish('abort', {'source': 'http'})
        current_app.drone.emergency_stop()
        
        return jsonify({
            'status': 'aborted',
            'message': 'Emergency stop activated - drone hovering'
        })
    
    except Exception as e:
        log.error(f"Abort failed: {e}")
        return jsonify({'error': str(e)}), 500


@status_bp.route('/clear', methods=['POST'])
def clear_abort_flag():
    """
    Clear the abort flag to resume operations.
    
    Response JSON:
        {
            "status": "cleared"
        }
    """
    try:
        clear_abort()
        log.info("Abort flag cleared")
        
        return jsonify({
            'status': 'cleared',
            'message': 'Ready for new commands'
        })
    
    except Exception as e:
        log.error(f"Failed to clear abort: {e}")
        return jsonify({'error': str(e)}), 500


@status_bp.route('/emergency/land', methods=['POST'])
def emergency_land():
    """
    🚨 EMERGENCY LAND - Land immediately wherever the drone is!
    
    This is your panic button! Lands the drone RIGHT NOW.
    Bypasses all checks and forces immediate landing.
    
    Response JSON:
        {
            "status": "emergency_landed",
            "message": "...",
            "position": {...}
        }
    """
    try:
        log.warning("🚨🚨🚨 EMERGENCY LAND triggered via API 🚨🚨🚨")
        
        # Get position before landing
        position = current_app.drone.get_position()
        
        # LAND NOW!
        current_app.drone.emergency_land()
        
        return jsonify({
            'status': 'emergency_landed',
            'message': '🚨 Drone landed immediately!',
            'position': position
        })
    
    except Exception as e:
        log.error(f"Emergency land failed: {e}")
        return jsonify({'error': str(e)}), 500


@status_bp.route('/takeoff', methods=['POST'])
def takeoff():
    """
    🚀 TAKEOFF - Launch the drone and rise to eye level.
    
    Response JSON:
        {
            "status": "airborne",
            "message": "...",
            "battery": 85
        }
    """
    try:
        log.info("🚀 TAKEOFF triggered via API")
        
        # Get battery level first
        battery = current_app.drone.get_battery()
        
        # Take off!
        current_app.drone.takeoff()
        
        return jsonify({
            'status': 'airborne',
            'message': '🚀 Drone is airborne!',
            'battery': battery
        })
    
    except Exception as e:
        log.error(f"Takeoff failed: {e}")
        return jsonify({'error': str(e)}), 500


@status_bp.route('/land', methods=['POST'])
def land():
    """
    ✈️ LAND - Land the drone safely (internal land command).
    
    Response JSON:
        {
            "status": "landed",
            "message": "..."
        }
    """
    try:
        log.info("✈️ LAND triggered via API")
        
        # Use the normal land method (not emergency)
        current_app.drone.land()
        
        return jsonify({
            'status': 'landed',
            'message': '✅ Drone landed safely!'
        })
    
    except Exception as e:
        log.error(f"Land failed: {e}")
        return jsonify({'error': str(e)}), 500


@status_bp.route('/return-home', methods=['POST'])
def return_home():
    """
    🏠 RETURN HOME - Fly back to takeoff position and land safely.
    
    Uses position tracking to navigate back to starting point.
    
    Response JSON:
        {
            "status": "returned_home",
            "distance_traveled": 123.45,
            "position": {...}
        }
    """
    try:
        log.info("🏠 RETURN HOME triggered via API")
        
        # Get current position and distance
        position = current_app.drone.get_position()
        distance = current_app.drone.get_distance_from_home()
        
        log.info(f"Current position: {position}, distance: {distance:.1f}cm")
        
        # Return home and land
        current_app.drone.return_home_and_land()
        
        return jsonify({
            'status': 'returned_home',
            'message': f'🏠 Returned home from {distance:.0f}cm away and landed!',
            'distance_traveled': distance,
            'start_position': position
        })
    
    except Exception as e:
        log.error(f"Return home failed: {e}")
        return jsonify({'error': str(e)}), 500
