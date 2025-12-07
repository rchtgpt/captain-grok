"""
Face Recognition Service for target matching.
Uses the face_recognition library for embedding extraction and comparison.
"""

import threading
import numpy as np
from typing import Optional, List, Dict, Tuple, Any
from dataclasses import dataclass

from core.logger import get_logger

log = get_logger('face_recognition')

# Try to import face_recognition, but gracefully handle if not available
try:
    import face_recognition
    FACE_RECOGNITION_AVAILABLE = True
    log.info("face_recognition library loaded successfully")
except ImportError:
    FACE_RECOGNITION_AVAILABLE = False
    log.warning("face_recognition library not available - facial recognition disabled")


@dataclass
class FaceDetection:
    """A detected face with its embedding and location."""
    embedding: List[float]
    bbox: Dict[str, float]  # {x, y, width, height} as percentages
    confidence: float = 1.0


class FaceRecognitionService:
    """
    Service for face detection and recognition.
    
    Features:
    - Extract face embeddings from images
    - Compare embeddings for matching
    - Find best match among targets
    """
    
    # Matching threshold - LOWER means STRICTER matching (distance-based)
    # 0.6 = lenient (too many false positives)
    # 0.5 = moderate
    # 0.45 = strict (fewer false positives, requires good face match)
    # 0.4 = very strict (may miss some valid matches)
    MATCH_THRESHOLD = 0.45
    
    # Minimum confidence to report a match (0-1 scale)
    # Confidence = 1 - (distance / threshold)
    # At threshold=0.45, distance=0.35 gives ~22% confidence
    # We want at least 50% confidence for a solid match
    MIN_CONFIDENCE = 0.50
    
    def __init__(self):
        self.log = get_logger('face_service')
        self._lock = threading.Lock()
        
        if not FACE_RECOGNITION_AVAILABLE:
            self.log.warning("Face recognition not available - install face_recognition package")
    
    @property
    def is_available(self) -> bool:
        """Check if face recognition is available."""
        return FACE_RECOGNITION_AVAILABLE
    
    def extract_embedding(self, image: np.ndarray) -> Optional[List[float]]:
        """
        Extract face embedding from an image.
        
        Args:
            image: BGR image (OpenCV format)
            
        Returns:
            128-dimensional face embedding as list, or None if no face found
        """
        if not FACE_RECOGNITION_AVAILABLE:
            return None
        
        try:
            # Validate image
            if image is None or image.size == 0:
                self.log.debug("Empty image provided")
                return None
            
            # Ensure image is contiguous in memory (required by dlib)
            if not image.flags['C_CONTIGUOUS']:
                image = np.ascontiguousarray(image)
            
            # Ensure image is uint8
            if image.dtype != np.uint8:
                image = image.astype(np.uint8)
            
            # Convert BGR to RGB (face_recognition uses RGB)
            rgb_image = image[:, :, ::-1].copy()  # .copy() ensures contiguous array
            
            # Ensure minimum image size for face detection
            min_size = 80
            h, w = rgb_image.shape[:2]
            if h < min_size or w < min_size:
                self.log.debug(f"Image too small for face detection: {w}x{h}")
                return None
            
            # Find face locations
            face_locations = face_recognition.face_locations(rgb_image, model="hog")
            
            if not face_locations:
                self.log.debug("No faces found in image")
                return None
            
            # Get embedding for first (largest) face
            # Use num_jitters=1 for faster processing (default)
            try:
                embeddings = face_recognition.face_encodings(rgb_image, face_locations, num_jitters=1)
            except Exception as encoding_error:
                self.log.warning(f"Face encoding failed (possibly invalid face region): {encoding_error}")
                return None
            
            if embeddings and len(embeddings) > 0:
                return embeddings[0].tolist()
            
            return None
            
        except Exception as e:
            self.log.error(f"Error extracting embedding: {e}")
            return None
    
    def extract_all_faces(self, image: np.ndarray, upsample: int = 1) -> List[FaceDetection]:
        """
        Extract all faces from an image with their embeddings and locations.
        
        Args:
            image: BGR image (OpenCV format)
            upsample: Number of times to upsample image for finding smaller faces.
                      1 = default (fast), 2 = better for distant/small faces (slower)
            
        Returns:
            List of FaceDetection objects
        """
        if not FACE_RECOGNITION_AVAILABLE:
            return []
        
        try:
            # Validate image
            if image is None or image.size == 0:
                return []
            
            h, w = image.shape[:2]
            
            # Ensure minimum image size (reduced from 80 to catch more faces)
            min_size = 50
            if h < min_size or w < min_size:
                self.log.debug(f"Image too small for face detection: {w}x{h}")
                return []
            
            # Ensure image is contiguous and uint8
            if not image.flags['C_CONTIGUOUS']:
                image = np.ascontiguousarray(image)
            if image.dtype != np.uint8:
                image = image.astype(np.uint8)
            
            # Convert BGR to RGB (ensure contiguous)
            rgb_image = image[:, :, ::-1].copy()
            
            # Find all face locations with upsampling for better small face detection
            # HOG model is fast; upsample helps find smaller/distant faces
            face_locations = face_recognition.face_locations(
                rgb_image, 
                model="hog",
                number_of_times_to_upsample=upsample
            )
            
            if not face_locations:
                return []
            
            # Get embeddings for all faces
            try:
                embeddings = face_recognition.face_encodings(rgb_image, face_locations, num_jitters=1)
            except Exception as encoding_error:
                self.log.warning(f"Face encoding failed (possibly invalid face region): {encoding_error}")
                return []
            
            detections = []
            for (top, right, bottom, left), embedding in zip(face_locations, embeddings):
                # Convert to percentage-based bbox
                bbox = {
                    'x': left / w,
                    'y': top / h,
                    'width': (right - left) / w,
                    'height': (bottom - top) / h
                }
                
                detections.append(FaceDetection(
                    embedding=embedding.tolist(),
                    bbox=bbox
                ))
            
            self.log.debug(f"Found {len(detections)} faces in image (upsample={upsample})")
            return detections
            
        except Exception as e:
            self.log.error(f"Error extracting faces: {e}")
            return []
    
    def compare_embeddings(self, emb1: List[float], emb2: List[float]) -> float:
        """
        Compare two face embeddings.
        
        Args:
            emb1: First embedding (128-d list)
            emb2: Second embedding (128-d list)
            
        Returns:
            Similarity score (0-1, higher is more similar)
        """
        if not emb1 or not emb2:
            return 0.0
        
        try:
            # face_recognition uses Euclidean distance
            # We convert to similarity score (0-1)
            arr1 = np.array(emb1)
            arr2 = np.array(emb2)
            
            # Euclidean distance
            distance = np.linalg.norm(arr1 - arr2)
            
            # Convert to similarity (inverse of distance)
            # Distance of 0 = similarity of 1
            # Distance of 1 = similarity of ~0.37
            # Distance of 0.6 (threshold) = similarity of ~0.55
            similarity = np.exp(-distance)
            
            # Alternative: linear scaling where 0.6 threshold = 0.6 similarity
            # similarity = max(0, 1 - distance)
            
            return float(similarity)
            
        except Exception as e:
            self.log.error(f"Error comparing embeddings: {e}")
            return 0.0
    
    def is_match(self, emb1: List[float], emb2: List[float], threshold: float = None) -> bool:
        """
        Check if two embeddings match (same person).
        
        Uses Euclidean distance threshold (standard for face_recognition).
        
        Args:
            emb1: First face embedding
            emb2: Second face embedding
            threshold: Optional custom threshold (default: self.MATCH_THRESHOLD = 0.6)
        """
        if not FACE_RECOGNITION_AVAILABLE or not emb1 or not emb2:
            return False
        
        if threshold is None:
            threshold = self.MATCH_THRESHOLD
        
        try:
            arr1 = np.array(emb1)
            arr2 = np.array(emb2)
            
            distance = np.linalg.norm(arr1 - arr2)
            return distance <= threshold
            
        except Exception:
            return False
    
    def find_best_match(
        self, 
        embedding: List[float], 
        target_embeddings: List[Tuple[str, List[List[float]]]]
    ) -> Optional[Tuple[str, float]]:
        """
        Find the best matching target for a face embedding.
        
        Args:
            embedding: Face embedding to match
            target_embeddings: List of (target_id, [embeddings]) tuples
            
        Returns:
            (target_id, confidence) tuple, or None if no match
        """
        if not embedding or not target_embeddings:
            return None
        
        best_match_id = None
        best_distance = float('inf')
        
        try:
            query_arr = np.array(embedding)
            
            for target_id, embeddings_list in target_embeddings:
                for target_emb in embeddings_list:
                    if not target_emb:
                        continue
                    
                    target_arr = np.array(target_emb)
                    distance = np.linalg.norm(query_arr - target_arr)
                    
                    if distance < best_distance:
                        best_distance = distance
                        best_match_id = target_id
            
            # Check if best match is within threshold
            if best_match_id and best_distance <= self.MATCH_THRESHOLD:
                # Convert distance to confidence (0-1)
                confidence = max(0, 1 - (best_distance / self.MATCH_THRESHOLD))
                
                # Only return if confidence meets minimum threshold
                if confidence >= self.MIN_CONFIDENCE:
                    self.log.debug(f"Face match found: distance={best_distance:.3f}, confidence={confidence:.1%}")
                    return (best_match_id, confidence)
                else:
                    self.log.debug(f"Face match rejected (low confidence): distance={best_distance:.3f}, confidence={confidence:.1%} < {self.MIN_CONFIDENCE:.1%}")
                    return None
            
            return None
            
        except Exception as e:
            self.log.error(f"Error finding best match: {e}")
            return None


# Singleton instance
_face_service: Optional[FaceRecognitionService] = None
_face_service_lock = threading.Lock()


def get_face_service() -> FaceRecognitionService:
    """Get the singleton FaceRecognitionService instance."""
    global _face_service
    with _face_service_lock:
        if _face_service is None:
            _face_service = FaceRecognitionService()
        return _face_service
