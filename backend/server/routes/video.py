"""
Video streaming routes for Grok-Pilot.
"""

import time
import cv2
from flask import Blueprint, Response, current_app
from core.logger import get_logger

video_bp = Blueprint('video', __name__)
log = get_logger('routes.video')


@video_bp.route('/stream')
def video_stream():
    """
    MJPEG video stream endpoint.
    
    Returns:
        MJPEG stream response
    """
    # Capture reference to video stream BEFORE entering generator
    # (generators lose Flask app context after first yield)
    drone = current_app.drone
    video = drone.video if drone else None
    
    def generate():
        """Generator function for MJPEG frames."""
        log.info("Video stream client connected")
        
        while True:
            try:
                # Check if video is available
                if not video or not video.is_running:
                    # Send placeholder frame
                    placeholder = create_placeholder_frame("Video Not Available")
                    _, jpeg = cv2.imencode('.jpg', placeholder)
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' +
                           jpeg.tobytes() + b'\r\n')
                    time.sleep(0.5)
                    continue
                
                # Get frame from drone
                frame = video.get_frame()
                
                if frame is None:
                    time.sleep(0.033)  # ~30fps
                    continue
                
                # Encode as JPEG
                _, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                
                # Yield as MJPEG
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' +
                       jpeg.tobytes() + b'\r\n')
                
                time.sleep(0.033)  # ~30fps
            
            except GeneratorExit:
                log.info("Video stream client disconnected")
                break
            
            except Exception as e:
                log.error(f"Video stream error: {e}")
                time.sleep(0.5)
    
    return Response(
        generate(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )


def create_placeholder_frame(text):
    """
    Create a placeholder frame with text.
    
    Args:
        text: Text to display
        
    Returns:
        Numpy array frame
    """
    import numpy as np
    
    # Create gray frame
    frame = np.zeros((720, 960, 3), dtype=np.uint8)
    frame[:, :] = [50, 50, 50]
    
    # Add text
    cv2.putText(
        frame,
        text,
        (300, 360),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.5,
        (255, 255, 255),
        3
    )
    
    return frame
