"""
Session management routes for video recording.

Endpoints:
- POST /session/start - Start recording
- POST /session/stop - Stop recording
- GET /session/status - Current session status
- GET /sessions - List all sessions
- GET /session/<id> - Get session metadata
- GET /session/<id>/video - Download session video
- DELETE /session/<id> - Delete a session
- DELETE /sessions - Delete all sessions
"""

from flask import Blueprint, jsonify, request, send_file, current_app
from pathlib import Path

from core.logger import get_logger
from drone.recorder import get_recorder

log = get_logger('routes.session')
bp = Blueprint('session', __name__, url_prefix='/session')


@bp.route('/start', methods=['POST'])
def start_session():
    """
    Start a new recording session.
    
    Body (optional):
        manual: bool - If true, won't auto-stop on land (default: false)
    
    Returns:
        {
            "success": true,
            "session_id": "20251207_143022",
            "message": "Recording started"
        }
    """
    try:
        data = request.get_json() or {}
        manual = data.get('manual', False)
        
        recorder = get_recorder()
        session_id = recorder.start(manual=manual)
        
        # Connect recorder to video stream if available
        if hasattr(current_app, 'video') and current_app.video:
            current_app.video.set_recorder(recorder)
        
        return jsonify({
            "success": True,
            "session_id": session_id,
            "message": "Recording started"
        })
    
    except Exception as e:
        log.error(f"Failed to start session: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@bp.route('/stop', methods=['POST'])
def stop_session():
    """
    Stop the current recording session.
    
    Returns:
        Session metadata including duration, frame count, etc.
    """
    try:
        recorder = get_recorder()
        metadata = recorder.stop()
        
        if metadata is None:
            return jsonify({
                "success": False,
                "error": "No active recording session"
            }), 400
        
        return jsonify({
            "success": True,
            "session": metadata,
            "message": "Recording stopped"
        })
    
    except Exception as e:
        log.error(f"Failed to stop session: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@bp.route('/status', methods=['GET'])
def get_session_status():
    """
    Get current recording status.
    
    Returns:
        {
            "recording": true/false,
            "session_id": "...",
            "duration_seconds": 123.4,
            "frame_count": 3702
        }
    """
    try:
        recorder = get_recorder()
        status = recorder.get_status()
        
        return jsonify({
            "success": True,
            **status
        })
    
    except Exception as e:
        log.error(f"Failed to get session status: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# Sessions list endpoint (note: different URL pattern)
sessions_bp = Blueprint('sessions', __name__, url_prefix='/sessions')


@sessions_bp.route('', methods=['GET'])
def list_sessions():
    """
    List all recorded sessions.
    
    Returns:
        {
            "success": true,
            "sessions": [
                {
                    "session_id": "20251207_143022",
                    "duration_seconds": 120.5,
                    "frame_count": 3615,
                    ...
                }
            ],
            "count": 5
        }
    """
    try:
        recorder = get_recorder()
        sessions = recorder.list_sessions()
        
        return jsonify({
            "success": True,
            "sessions": sessions,
            "count": len(sessions)
        })
    
    except Exception as e:
        log.error(f"Failed to list sessions: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@sessions_bp.route('', methods=['DELETE'])
def delete_all_sessions():
    """
    Delete all recorded sessions.
    
    Returns:
        {
            "success": true,
            "deleted_count": 5,
            "message": "Deleted 5 sessions"
        }
    """
    try:
        recorder = get_recorder()
        deleted = recorder.delete_all_sessions()
        
        return jsonify({
            "success": True,
            "deleted_count": deleted,
            "message": f"Deleted {deleted} sessions"
        })
    
    except Exception as e:
        log.error(f"Failed to delete all sessions: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@bp.route('/<session_id>', methods=['GET'])
def get_session(session_id: str):
    """
    Get metadata for a specific session.
    
    Returns:
        Session metadata JSON
    """
    try:
        recorder = get_recorder()
        metadata = recorder.get_session(session_id)
        
        if metadata is None:
            return jsonify({
                "success": False,
                "error": f"Session not found: {session_id}"
            }), 404
        
        return jsonify({
            "success": True,
            "session": metadata
        })
    
    except Exception as e:
        log.error(f"Failed to get session {session_id}: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@bp.route('/<session_id>/video', methods=['GET'])
def get_session_video(session_id: str):
    """
    Download the video file for a session.
    
    Returns:
        MP4 video file
    """
    try:
        recorder = get_recorder()
        video_path = recorder.get_session_video_path(session_id)
        
        if video_path is None:
            return jsonify({
                "success": False,
                "error": f"Video not found for session: {session_id}"
            }), 404
        
        return send_file(
            video_path,
            mimetype='video/mp4',
            as_attachment=True,
            download_name=f"session_{session_id}.mp4"
        )
    
    except Exception as e:
        log.error(f"Failed to get video for session {session_id}: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@bp.route('/<session_id>', methods=['DELETE'])
def delete_session(session_id: str):
    """
    Delete a specific session.
    
    Returns:
        {
            "success": true,
            "message": "Session deleted"
        }
    """
    try:
        recorder = get_recorder()
        success = recorder.delete_session(session_id)
        
        if not success:
            return jsonify({
                "success": False,
                "error": f"Session not found: {session_id}"
            }), 404
        
        return jsonify({
            "success": True,
            "message": f"Session {session_id} deleted"
        })
    
    except Exception as e:
        log.error(f"Failed to delete session {session_id}: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
