"""
Memory API routes - Simplified version.

Most entity endpoints removed. Use /targets API instead.
Only conversation and state endpoints remain.
"""

from flask import Blueprint, request, jsonify
from core.logger import get_logger
from core.memory import get_memory, reset_memory

memory_bp = Blueprint('memory', __name__)
log = get_logger('routes.memory')


@memory_bp.route('/', methods=['GET'])
def get_memory_summary():
    """
    Get summary of drone's memory (simplified).
    
    Returns:
        {
            "people": [],  // Always empty - use /targets instead
            "objects": [],  // Always empty
            "stats": {
                "people_count": 0,
                "objects_count": 0,
                "heading": int,
                "position": {...}
            }
        }
    """
    try:
        memory = get_memory()
        
        return jsonify({
            'people': [],  # Removed - use targets API
            'objects': [],  # Removed
            'stats': {
                'people_count': 0,
                'objects_count': 0,
                'entity_count': 0,
                'heading': memory.heading,
                'position': memory.position
            }
        })
    
    except Exception as e:
        log.error(f"Failed to get memory: {e}")
        return jsonify({'error': str(e)}), 500


@memory_bp.route('/people', methods=['GET'])
def get_people():
    """Get all people - DEPRECATED, use /targets instead."""
    return jsonify({
        'people': [],
        'count': 0,
        'message': 'Use /targets API instead'
    })


@memory_bp.route('/objects', methods=['GET'])
def get_objects():
    """Get all objects - REMOVED."""
    return jsonify({
        'objects': [],
        'count': 0,
        'message': 'Object tracking removed'
    })


@memory_bp.route('/context', methods=['GET'])
def get_ai_context():
    """Get the AI context string (for debugging)."""
    try:
        memory = get_memory()
        context = memory.get_context_for_ai()
        
        return jsonify({
            'context': context,
            'length': len(context)
        })
    
    except Exception as e:
        log.error(f"Failed to get context: {e}")
        return jsonify({'error': str(e)}), 500


@memory_bp.route('/conversation', methods=['GET'])
def get_conversation():
    """Get conversation history."""
    try:
        memory = get_memory()
        history = memory.get_conversation_history()
        
        return jsonify({
            'conversation': history,
            'count': len(history)
        })
    
    except Exception as e:
        log.error(f"Failed to get conversation: {e}")
        return jsonify({'error': str(e)}), 500


@memory_bp.route('/reset', methods=['POST'])
def reset_memory_endpoint():
    """Reset memory (new session)."""
    try:
        new_memory = reset_memory()
        
        return jsonify({
            'status': 'success',
            'message': 'Memory reset',
            'session_dir': str(new_memory.session_dir)
        })
    
    except Exception as e:
        log.error(f"Failed to reset memory: {e}")
        return jsonify({'error': str(e)}), 500


@memory_bp.route('/save', methods=['POST'])
def save_memory():
    """Save memory to disk."""
    try:
        memory = get_memory()
        memory.save()
        
        return jsonify({
            'status': 'success',
            'message': 'Memory saved',
            'path': str(memory.session_dir / 'memory.json')
        })
    
    except Exception as e:
        log.error(f"Failed to save memory: {e}")
        return jsonify({'error': str(e)}), 500
