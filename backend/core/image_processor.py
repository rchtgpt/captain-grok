"""
Image processing utilities for cropping, enhancement, and face extraction.
Async-capable for parallel processing.
"""

import cv2
import numpy as np
from typing import Optional, Dict, Tuple, List
from concurrent.futures import ThreadPoolExecutor
import threading
from pathlib import Path

from core.logger import get_logger

log = get_logger('image_processor')


class ImageProcessor:
    """
    Process and enhance captured images.
    Supports cropping, face region extraction, and image enhancement.
    Thread-safe with parallel processing support.
    """
    
    def __init__(self, max_workers: int = 2):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self._lock = threading.Lock()
    
    def extract_region(
        self, 
        frame: np.ndarray, 
        bbox: Dict[str, float],
        padding: int = 20,
        enhance: bool = True
    ) -> Optional[np.ndarray]:
        """
        Extract and optionally enhance a region from a frame.
        
        Args:
            frame: Source image (BGR)
            bbox: Bounding box as percentages {x, y, width, height}
            padding: Pixels of padding to add around the box
            enhance: Whether to enhance the cropped image
            
        Returns:
            Cropped (and optionally enhanced) image, or None on error
        """
        try:
            h, w = frame.shape[:2]
            
            # Convert percentage bbox to pixels
            x = int(bbox['x'] * w)
            y = int(bbox['y'] * h)
            bw = int(bbox['width'] * w)
            bh = int(bbox['height'] * h)
            
            # Add padding
            x = max(0, x - padding)
            y = max(0, y - padding)
            bw = min(w - x, bw + 2 * padding)
            bh = min(h - y, bh + 2 * padding)
            
            # Validate dimensions
            if bw <= 0 or bh <= 0:
                log.warning(f"Invalid crop dimensions: {bw}x{bh}")
                return None
            
            # Crop
            crop = frame[y:y+bh, x:x+bw].copy()
            
            if enhance:
                crop = self.enhance_image(crop)
            
            return crop
            
        except Exception as e:
            log.error(f"Error extracting region: {e}")
            return None
    
    def extract_face_region(
        self,
        frame: np.ndarray,
        person_bbox: Dict[str, float],
        enhance: bool = True
    ) -> Optional[np.ndarray]:
        """
        Extract face region from a person bounding box.
        Assumes face is in the upper 35% of the person bounding box.
        
        Args:
            frame: Source image
            person_bbox: Person's bounding box
            enhance: Whether to enhance the result
            
        Returns:
            Face region image or None
        """
        try:
            # Face is typically in the upper portion of person bbox
            face_bbox = {
                'x': person_bbox['x'] + person_bbox['width'] * 0.1,  # Slight inward offset
                'y': person_bbox['y'],
                'width': person_bbox['width'] * 0.8,  # Slightly narrower
                'height': person_bbox['height'] * 0.35  # Upper 35%
            }
            
            return self.extract_region(frame, face_bbox, padding=10, enhance=enhance)
            
        except Exception as e:
            log.error(f"Error extracting face region: {e}")
            return None
    
    def enhance_image(self, image: np.ndarray) -> np.ndarray:
        """
        Enhance image quality with denoising, sharpening, and contrast.
        
        Args:
            image: Input image (BGR)
            
        Returns:
            Enhanced image
        """
        try:
            if image is None or image.size == 0:
                return image
            
            # Denoise (light)
            denoised = cv2.fastNlMeansDenoisingColored(
                image, None, 
                h=5,  # Filter strength
                hColor=5,
                templateWindowSize=7,
                searchWindowSize=21
            )
            
            # Sharpen
            kernel = np.array([
                [0, -0.5, 0],
                [-0.5, 3, -0.5],
                [0, -0.5, 0]
            ])
            sharpened = cv2.filter2D(denoised, -1, kernel)
            
            # Enhance contrast using CLAHE on L channel
            lab = cv2.cvtColor(sharpened, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            l = clahe.apply(l)
            
            enhanced = cv2.merge([l, a, b])
            enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
            
            return enhanced
            
        except Exception as e:
            log.error(f"Error enhancing image: {e}")
            return image
    
    def create_thumbnail(
        self,
        image: np.ndarray,
        max_size: int = 150
    ) -> np.ndarray:
        """
        Create a thumbnail image.
        
        Args:
            image: Input image
            max_size: Maximum dimension (width or height)
            
        Returns:
            Thumbnail image
        """
        try:
            h, w = image.shape[:2]
            
            if max(h, w) <= max_size:
                return image.copy()
            
            if w > h:
                new_w = max_size
                new_h = int(h * max_size / w)
            else:
                new_h = max_size
                new_w = int(w * max_size / h)
            
            return cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
            
        except Exception as e:
            log.error(f"Error creating thumbnail: {e}")
            return image
    
    def annotate_frame(
        self,
        frame: np.ndarray,
        detections: List[Dict],
        show_labels: bool = True
    ) -> np.ndarray:
        """
        Draw bounding boxes and labels on a frame.
        
        Args:
            frame: Input frame
            detections: List of detections with bbox and label
            show_labels: Whether to show text labels
            
        Returns:
            Annotated frame
        """
        try:
            annotated = frame.copy()
            h, w = frame.shape[:2]
            
            colors = {
                'person': (0, 255, 0),    # Green
                'object': (255, 165, 0),  # Orange
                'furniture': (128, 128, 128),  # Gray
                'location': (0, 255, 255)  # Yellow
            }
            
            for det in detections:
                bbox = det.get('bounding_box')
                if not bbox:
                    continue
                
                # Convert to pixels
                x = int(bbox['x'] * w)
                y = int(bbox['y'] * h)
                bw = int(bbox['width'] * w)
                bh = int(bbox['height'] * h)
                
                # Get color
                entity_type = det.get('entity_type', 'object')
                color = colors.get(entity_type, (255, 255, 255))
                
                # Draw rectangle
                cv2.rectangle(annotated, (x, y), (x + bw, y + bh), color, 2)
                
                # Draw label
                if show_labels:
                    label = det.get('label', det.get('description', ''))[:30]
                    
                    # Background for text
                    (text_w, text_h), _ = cv2.getTextSize(
                        label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1
                    )
                    cv2.rectangle(
                        annotated,
                        (x, y - text_h - 5),
                        (x + text_w + 5, y),
                        color,
                        -1
                    )
                    
                    # Text
                    cv2.putText(
                        annotated,
                        label,
                        (x + 2, y - 3),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (0, 0, 0),
                        1
                    )
            
            return annotated
            
        except Exception as e:
            log.error(f"Error annotating frame: {e}")
            return frame
    
    def estimate_bbox_from_position(
        self,
        frame_position: str,
        estimated_distance: str
    ) -> Dict[str, float]:
        """
        Estimate a rough bounding box from position and distance descriptions.
        Used when Grok doesn't provide exact coordinates.
        
        Args:
            frame_position: "far_left", "left", "center", "right", "far_right"
            estimated_distance: "very_close", "close", "medium", "far", "very_far"
            
        Returns:
            Estimated bounding box
        """
        # X position based on frame position
        x_positions = {
            'far_left': 0.0,
            'left': 0.15,
            'center': 0.35,
            'right': 0.55,
            'far_right': 0.75
        }
        
        # Size based on distance (closer = larger)
        sizes = {
            'very_close': {'width': 0.4, 'height': 0.7},
            'close': {'width': 0.3, 'height': 0.6},
            'medium': {'width': 0.25, 'height': 0.5},
            'far': {'width': 0.15, 'height': 0.35},
            'very_far': {'width': 0.1, 'height': 0.25}
        }
        
        x = x_positions.get(frame_position.lower(), 0.35)
        size = sizes.get(estimated_distance.lower(), sizes['medium'])
        
        return {
            'x': x,
            'y': 0.1,  # Assume person starts near top of frame
            'width': size['width'],
            'height': size['height']
        }
    
    def save_image(
        self,
        image: np.ndarray,
        path: Path,
        quality: int = 90
    ) -> bool:
        """
        Save image to disk.
        
        Args:
            image: Image to save
            path: Output path
            quality: JPEG quality (0-100)
            
        Returns:
            True if successful
        """
        try:
            path = Path(path)
            path.parent.mkdir(parents=True, exist_ok=True)
            
            encode_params = [cv2.IMWRITE_JPEG_QUALITY, quality]
            cv2.imwrite(str(path), image, encode_params)
            return True
            
        except Exception as e:
            log.error(f"Error saving image to {path}: {e}")
            return False
    
    def process_async(
        self,
        frame: np.ndarray,
        bbox: Optional[Dict[str, float]] = None,
        extract_face: bool = False
    ):
        """
        Process image asynchronously.
        
        Returns:
            Future that resolves to (full_enhanced, crop, face_crop)
        """
        def _process():
            full_enhanced = self.enhance_image(frame)
            
            crop = None
            if bbox:
                crop = self.extract_region(frame, bbox)
            
            face_crop = None
            if extract_face and bbox:
                face_crop = self.extract_face_region(frame, bbox)
            
            return full_enhanced, crop, face_crop
        
        return self.executor.submit(_process)
    
    def shutdown(self):
        """Shutdown the thread pool."""
        self.executor.shutdown(wait=False)


# Singleton instance
_processor_instance: Optional[ImageProcessor] = None
_processor_lock = threading.Lock()


def get_image_processor() -> ImageProcessor:
    """Get singleton ImageProcessor instance."""
    global _processor_instance
    with _processor_lock:
        if _processor_instance is None:
            _processor_instance = ImageProcessor()
        return _processor_instance
