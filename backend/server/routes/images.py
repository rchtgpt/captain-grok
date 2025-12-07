"""
Image serving routes for Grok-Pilot.
Serves captured vision images from logs.
"""

import os
from flask import Blueprint, send_from_directory, abort, current_app
from core.logger import get_logger

images_bp = Blueprint('images', __name__)
log = get_logger('routes.images')


@images_bp.route('/vision/<path:image_path>')
def serve_vision_image(image_path):
    """
    Serve images from vision logs.
    
    URL format: /images/vision/<run_id>/<image_id>/input_image.jpg
    Example: /images/vision/run_20251206_224151/image_0001/input_image.jpg
    
    Args:
        image_path: Path relative to vision_logs directory
        
    Returns:
        Image file
    """
    try:
        # Base directory for vision logs
        base_dir = os.path.join(os.getcwd(), 'logs', 'vision_logs')
        
        # Security: ensure we're not escaping the base directory
        requested_path = os.path.normpath(os.path.join(base_dir, image_path))
        if not requested_path.startswith(os.path.normpath(base_dir)):
            log.warning(f"Attempted path traversal: {image_path}")
            abort(403)
        
        # Check if file exists
        if not os.path.isfile(requested_path):
            log.warning(f"Image not found: {image_path}")
            abort(404)
        
        # Get directory and filename
        directory = os.path.dirname(requested_path)
        filename = os.path.basename(requested_path)
        
        log.debug(f"Serving image: {image_path}")
        return send_from_directory(directory, filename, mimetype='image/jpeg')
    
    except Exception as e:
        log.error(f"Error serving image: {e}")
        abort(500)


@images_bp.route('/vision/latest')
def get_latest_image():
    """
    Get the most recently captured image URL.
    
    Returns:
        JSON with image URL
    """
    try:
        from utils.image_logger import get_image_logger
        
        image_logger = get_image_logger()
        
        if image_logger.image_counter == 0:
            return {'error': 'No images captured yet'}, 404
        
        run_dir = image_logger.run_dir.name
        image_id = f"image_{image_logger.image_counter:04d}"
        image_url = f"/images/vision/{run_dir}/{image_id}/input_image.jpg"
        
        return {
            'url': image_url,
            'run_id': run_dir,
            'image_id': image_id,
            'total_images': image_logger.image_counter
        }
    
    except Exception as e:
        log.error(f"Error getting latest image: {e}")
        return {'error': str(e)}, 500
