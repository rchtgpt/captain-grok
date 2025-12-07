"""
Targets API routes.
Manage search targets with facial recognition.
"""

import os
import tempfile
from flask import Blueprint, request, jsonify, send_file, current_app
from pathlib import Path

from core.targets import get_target_manager
from core.logger import get_logger

log = get_logger('routes.targets')

targets_bp = Blueprint('targets', __name__)


@targets_bp.route('/', methods=['GET'])
def list_targets():
    """Get all targets."""
    try:
        manager = get_target_manager()
        targets = manager.get_all_targets()
        
        return jsonify({
            "targets": [t.to_dict() for t in targets],
            "stats": {
                "total": manager.total_count,
                "found": manager.found_count,
                "searching": manager.searching_count
            }
        })
    except Exception as e:
        log.error(f"Error listing targets: {e}")
        return jsonify({"error": str(e)}), 500


@targets_bp.route('/<target_id>', methods=['GET'])
def get_target(target_id: str):
    """Get a single target by ID."""
    try:
        manager = get_target_manager()
        target = manager.get_target(target_id)
        
        if not target:
            return jsonify({"error": "Target not found"}), 404
        
        return jsonify({"target": target.to_dict()})
    except Exception as e:
        log.error(f"Error getting target: {e}")
        return jsonify({"error": str(e)}), 500


@targets_bp.route('/', methods=['POST'])
def create_target():
    """
    Create a new target.
    
    Accepts multipart form data:
    - name: Target name (required)
    - description: Optional description
    - photos: One or more photo files
    """
    try:
        manager = get_target_manager()
        
        # Get form data
        name = request.form.get('name')
        if not name:
            return jsonify({"error": "Name is required"}), 400
        
        description = request.form.get('description', '')
        
        # Handle file uploads
        photo_paths = []
        temp_files = []
        
        if 'photos' in request.files:
            files = request.files.getlist('photos')
            for f in files:
                if f.filename:
                    # Save to temp file
                    ext = Path(f.filename).suffix or '.jpg'
                    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
                    f.save(temp_file.name)
                    photo_paths.append(temp_file.name)
                    temp_files.append(temp_file.name)
        
        # Create target
        target = manager.add_target(
            name=name,
            description=description,
            photo_paths=photo_paths
        )
        
        # Clean up temp files
        for temp_path in temp_files:
            try:
                os.unlink(temp_path)
            except:
                pass
        
        log.info(f"Created target: {target.name} (id={target.id})")
        
        return jsonify({
            "target": target.to_dict(),
            "message": f"Target '{name}' created successfully"
        }), 201
        
    except Exception as e:
        log.error(f"Error creating target: {e}")
        return jsonify({"error": str(e)}), 500


@targets_bp.route('/<target_id>', methods=['PUT'])
def update_target(target_id: str):
    """Update target details."""
    try:
        manager = get_target_manager()
        
        data = request.get_json() or {}
        
        # Only allow updating certain fields
        allowed_fields = {'name', 'description', 'status'}
        updates = {k: v for k, v in data.items() if k in allowed_fields}
        
        if not updates:
            return jsonify({"error": "No valid fields to update"}), 400
        
        target = manager.update_target(target_id, **updates)
        
        if not target:
            return jsonify({"error": "Target not found"}), 404
        
        return jsonify({
            "target": target.to_dict(),
            "message": "Target updated successfully"
        })
        
    except Exception as e:
        log.error(f"Error updating target: {e}")
        return jsonify({"error": str(e)}), 500


@targets_bp.route('/<target_id>', methods=['DELETE'])
def delete_target(target_id: str):
    """Delete a target."""
    try:
        manager = get_target_manager()
        
        success = manager.delete_target(target_id)
        
        if not success:
            return jsonify({"error": "Target not found"}), 404
        
        return jsonify({
            "success": True,
            "message": "Target deleted successfully"
        })
        
    except Exception as e:
        log.error(f"Error deleting target: {e}")
        return jsonify({"error": str(e)}), 500


@targets_bp.route('/<target_id>/photos', methods=['POST'])
def add_photos(target_id: str):
    """Add more reference photos to a target."""
    try:
        manager = get_target_manager()
        
        target = manager.get_target(target_id)
        if not target:
            return jsonify({"error": "Target not found"}), 404
        
        if 'photos' not in request.files:
            return jsonify({"error": "No photos provided"}), 400
        
        files = request.files.getlist('photos')
        
        for f in files:
            if f.filename:
                # Read file data
                photo_data = f.read()
                manager.add_photo_from_bytes(target_id, photo_data, f.filename)
        
        # Get updated target
        target = manager.get_target(target_id)
        
        return jsonify({
            "target": target.to_dict(),
            "message": f"Added {len(files)} photo(s) to target"
        })
        
    except Exception as e:
        log.error(f"Error adding photos: {e}")
        return jsonify({"error": str(e)}), 500


@targets_bp.route('/<target_id>/reference/<filename>', methods=['GET'])
def get_reference_photo(target_id: str, filename: str):
    """Serve a reference photo."""
    try:
        manager = get_target_manager()
        
        target = manager.get_target(target_id)
        if not target:
            return jsonify({"error": "Target not found"}), 404
        
        # Find the photo
        for photo_path in target.reference_photos:
            if Path(photo_path).name == filename:
                if Path(photo_path).exists():
                    return send_file(photo_path, mimetype='image/jpeg')
        
        return jsonify({"error": "Photo not found"}), 404
        
    except Exception as e:
        log.error(f"Error serving reference photo: {e}")
        return jsonify({"error": str(e)}), 500


@targets_bp.route('/<target_id>/matched/<filename>', methods=['GET'])
def get_matched_photo(target_id: str, filename: str):
    """Serve a matched photo from drone."""
    try:
        manager = get_target_manager()
        
        target = manager.get_target(target_id)
        if not target:
            return jsonify({"error": "Target not found"}), 404
        
        # Find the photo
        for photo_path in target.matched_photos:
            if Path(photo_path).name == filename:
                if Path(photo_path).exists():
                    return send_file(photo_path, mimetype='image/jpeg')
        
        return jsonify({"error": "Photo not found"}), 404
        
    except Exception as e:
        log.error(f"Error serving matched photo: {e}")
        return jsonify({"error": str(e)}), 500


@targets_bp.route('/images/<path:filepath>', methods=['GET'])
def serve_target_image(filepath: str):
    """Serve any target-related image by path."""
    try:
        manager = get_target_manager()
        
        # Try to find the image in photos or matched directories
        photos_path = manager.photos_dir / filepath
        matched_path = manager.matched_dir / filepath
        
        if photos_path.exists():
            return send_file(str(photos_path), mimetype='image/jpeg')
        elif matched_path.exists():
            return send_file(str(matched_path), mimetype='image/jpeg')
        
        # Try as absolute path
        if Path(filepath).exists():
            return send_file(filepath, mimetype='image/jpeg')
        
        return jsonify({"error": "Image not found"}), 404
        
    except Exception as e:
        log.error(f"Error serving image: {e}")
        return jsonify({"error": str(e)}), 500


@targets_bp.route('/by-name/<name>', methods=['GET'])
def get_target_by_name(name: str):
    """Get a target by name."""
    try:
        manager = get_target_manager()
        target = manager.get_target_by_name(name)
        
        if not target:
            return jsonify({"error": "Target not found"}), 404
        
        return jsonify({"target": target.to_dict()})
        
    except Exception as e:
        log.error(f"Error getting target by name: {e}")
        return jsonify({"error": str(e)}), 500
