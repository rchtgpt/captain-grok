"""
Tailing routes for real-time person following.

Endpoints:
- POST /tail/start - Start following a target
- POST /tail/stop - Stop following
- GET /tail/status - Get current tailing status
"""

from flask import Blueprint, jsonify, request

from core.logger import get_logger
from core.tailing import get_tailing_controller

log = get_logger('routes.tailing')
bp = Blueprint('tailing', __name__, url_prefix='/tail')


@bp.route('/start', methods=['POST'])
def start_tailing():
    """
    Start following a target.
    
    Body:
        target_id: str - ID of target to follow
        
    Returns:
        {
            "success": true,
            "target_id": "...",
            "target_name": "John",
            "message": "Now following John"
        }
    """
    try:
        data = request.get_json()
        if not data or 'target_id' not in data:
            return jsonify({
                "success": False,
                "error": "Missing target_id"
            }), 400
        
        target_id = data['target_id']
        
        controller = get_tailing_controller()
        if not controller:
            return jsonify({
                "success": False,
                "error": "Tailing controller not initialized"
            }), 500
        
        success = controller.start(target_id)
        
        if success:
            return jsonify({
                "success": True,
                "target_id": target_id,
                "target_name": controller.target_name,
                "message": f"Now following {controller.target_name}"
            })
        else:
            return jsonify({
                "success": False,
                "error": "Could not start tailing - check target exists and has face data"
            }), 400
    
    except Exception as e:
        log.error(f"Failed to start tailing: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@bp.route('/stop', methods=['POST'])
def stop_tailing():
    """
    Stop following the current target.
    
    Returns:
        {
            "success": true,
            "message": "Stopped following"
        }
    """
    try:
        controller = get_tailing_controller()
        if not controller:
            return jsonify({
                "success": False,
                "error": "Tailing controller not initialized"
            }), 500
        
        was_active = controller.active
        controller.stop()
        
        return jsonify({
            "success": True,
            "was_active": was_active,
            "message": "Stopped following" if was_active else "Was not following anyone"
        })
    
    except Exception as e:
        log.error(f"Failed to stop tailing: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@bp.route('/status', methods=['GET'])
def get_tailing_status():
    """
    Get current tailing status.
    
    Returns:
        {
            "success": true,
            "active": true/false,
            "target_id": "...",
            "target_name": "John",
            "bbox": {"x": 0.3, "y": 0.2, "width": 0.2, "height": 0.3},
            "confidence": 0.95,
            "frames_tracked": 150,
            "frames_lost": 3
        }
    """
    try:
        controller = get_tailing_controller()
        
        if not controller:
            return jsonify({
                "success": True,
                "active": False,
                "error": "Tailing not available"
            })
        
        status = controller.get_status()
        
        return jsonify({
            "success": True,
            "active": status.active,
            "target_id": status.target_id,
            "target_name": status.target_name,
            "bbox": status.bbox,
            "confidence": status.confidence,
            "last_seen": status.last_seen,
            "frames_tracked": status.frames_tracked,
            "frames_lost": status.frames_lost
        })
    
    except Exception as e:
        log.error(f"Failed to get tailing status: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
